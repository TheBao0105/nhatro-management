"""[PURE UNIT] Permission & Role Logic Unit Tests for Service 2.

Tests `common.auth` (`get_role`, `get_user_id`, `is_admin`, `is_landlord`, `is_manager`,
`IsManagerOrReadOnly`, `IsManagerRole`), `common.sprint.SprintFeatureLock`,
`services.property_service.serializers._viewer_is_manager`, and `settings.SIMPLE_JWT`
directly without HTTP requests.
Total in module: 12 pure unit tests (S2-PERM-001..011, S2-SEC-018).
"""
from types import SimpleNamespace
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from common import auth
from common.sprint import SprintFeatureLock
from services.property_service.serializers import _viewer_is_manager
from .base import fake_user


class PermissionClassUnitTests(SimpleTestCase):
    """[PURE UNIT] Lớp quyền và hàm role (common.auth, common.sprint, serializers._viewer_is_manager)."""

    def req(self, user, method='GET'):
        return mock.Mock(user=user, method=method)

    def test_get_role_for_anonymous_and_none(self):
        """S2-PERM-001 | [Từ S2-SEC-001] get_role người chưa xác thực | Data: None / is_authenticated=False | Expected: None"""
        self.assertIsNone(auth.get_role(None))
        self.assertIsNone(auth.get_role(fake_user(authenticated=False)))

    def test_get_role_superuser_unknown_and_missing(self):
        """S2-PERM-002 | [Từ S2-SEC-002] get_role: superuser, role lạ, thiếu role | Data: is_superuser, 'HACKER', không role | Expected: ADMIN, TENANT, TENANT"""
        self.assertEqual(auth.get_role(fake_user(role='TENANT', is_superuser=True)), 'ADMIN')
        self.assertEqual(auth.get_role(fake_user(role='HACKER')), 'TENANT')
        self.assertEqual(auth.get_role(mock.Mock(spec=['is_authenticated'], is_authenticated=True)), 'TENANT')

    def test_role_predicates(self):
        """S2-PERM-003 | [Từ S2-SEC-003] is_admin/is_landlord/is_manager | Data: ADMIN, LANDLORD, TENANT, STAFF | Expected: chỉ ADMIN & LANDLORD là manager; STAFF không"""
        self.assertTrue(auth.is_admin(fake_user(role='ADMIN')))
        self.assertTrue(auth.is_landlord(fake_user(role='LANDLORD')))
        self.assertTrue(auth.is_manager(fake_user(role='ADMIN')))
        self.assertTrue(auth.is_manager(fake_user(role='LANDLORD')))
        self.assertFalse(auth.is_manager(fake_user(role='TENANT')))
        self.assertFalse(auth.is_manager(fake_user(role='STAFF')))

    def test_get_user_id_parsing(self):
        """S2-PERM-004 | [Từ S2-SEC-004] get_user_id ép kiểu số nguyên và xử lý giá trị lỗi | Data: 12, '12', None, 'abc' | Expected: 12, 12, None, None"""
        self.assertEqual(auth.get_user_id(fake_user(user_id=12)), 12)
        self.assertEqual(auth.get_user_id(fake_user(user_id='12')), 12)
        self.assertIsNone(auth.get_user_id(fake_user(user_id=None)))
        self.assertIsNone(auth.get_user_id(fake_user(user_id='abc')))

    def test_is_manager_or_read_only_unauthenticated_denied(self):
        """S2-PERM-005 | [Từ S2-SEC-005] IsManagerOrReadOnly từ chối người dùng chưa đăng nhập | Data: user ẩn danh, GET | Expected: False"""
        perm = auth.IsManagerOrReadOnly()
        self.assertFalse(perm.has_permission(self.req(fake_user(authenticated=False)), None))

    def test_is_manager_or_read_only_safe_methods_for_any_authenticated_user(self):
        """S2-PERM-006 | [Từ S2-SEC-006] IsManagerOrReadOnly cho phép GET/HEAD/OPTIONS với mọi user đã đăng nhập | Data: TENANT với GET/HEAD/OPTIONS | Expected: True"""
        perm = auth.IsManagerOrReadOnly()
        for method in ('GET', 'HEAD', 'OPTIONS'):
            self.assertTrue(perm.has_permission(self.req(fake_user(role='TENANT'), method), None))

    def test_is_manager_or_read_only_write_requires_manager(self):
        """S2-PERM-007 | [Từ S2-SEC-007] IsManagerOrReadOnly chỉ cho phép LANDLORD/ADMIN gọi POST/PUT/PATCH/DELETE | Data: 4 write methods × 4 roles | Expected: LANDLORD/ADMIN True; TENANT/STAFF False"""
        perm = auth.IsManagerOrReadOnly()
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            self.assertTrue(perm.has_permission(self.req(fake_user(role='LANDLORD'), method), None))
            self.assertTrue(perm.has_permission(self.req(fake_user(role='ADMIN'), method), None))
            self.assertFalse(perm.has_permission(self.req(fake_user(role='TENANT'), method), None))
            self.assertFalse(perm.has_permission(self.req(fake_user(role='STAFF'), method), None))

    def test_is_manager_role_permission(self):
        """S2-PERM-008 | [Từ S2-SEC-008] IsManagerRole chặn mọi method của TENANT và user ẩn danh | Data: LANDLORD, ADMIN, TENANT, ẩn danh | Expected: True, True, False, False"""
        perm = auth.IsManagerRole()
        self.assertTrue(perm.has_permission(self.req(fake_user(role='LANDLORD')), None))
        self.assertTrue(perm.has_permission(self.req(fake_user(role='ADMIN')), None))
        self.assertFalse(perm.has_permission(self.req(fake_user(role='TENANT')), None))
        self.assertFalse(perm.has_permission(self.req(fake_user(authenticated=False)), None))

    def test_sprint_feature_lock_allows_unlocked_actions_and_blocks_locked_actions(self):
        """S2-PERM-009 | [Bổ sung Unit] SprintFeatureLock khi SPRINT_FEATURE_LOCK=True: cho phép action không khóa (list, retrieve) và chặn action trong sprint_locked_actions (create, history:POST) | Data: view có sprint_locked_actions=('create', 'history:POST') | Expected: list=True, create=False, history:GET=True, history:POST=False"""
        lock = SprintFeatureLock()
        admin = fake_user(role='ADMIN')
        locked_types = ('create', 'history:POST')
        self.assertTrue(lock.has_permission(self.req(admin, 'GET'), SimpleNamespace(sprint_locked_actions=locked_types, action='list')))
        self.assertFalse(lock.has_permission(self.req(admin, 'POST'), SimpleNamespace(sprint_locked_actions=locked_types, action='create')))
        self.assertTrue(lock.has_permission(self.req(admin, 'GET'), SimpleNamespace(sprint_locked_actions=locked_types, action='history')))
        self.assertFalse(lock.has_permission(self.req(admin, 'POST'), SimpleNamespace(sprint_locked_actions=locked_types, action='history')))

    @override_settings(SPRINT_FEATURE_LOCK=False)
    def test_sprint_feature_lock_allows_all_actions_when_disabled(self):
        """S2-PERM-010 | [Bổ sung Unit] SprintFeatureLock khi SPRINT_FEATURE_LOCK=False: cho phép cả action nằm trong sprint_locked_actions | Data: action='create' trong sprint_locked_actions | Expected: True"""
        lock = SprintFeatureLock()
        view = SimpleNamespace(sprint_locked_actions=('create',), action='create')
        self.assertTrue(lock.has_permission(self.req(fake_user(role='LANDLORD'), 'POST'), view))

    def test_viewer_is_manager_helper_with_various_contexts(self):
        """S2-PERM-011 | [Bổ sung Unit] _viewer_is_manager trong serializers.py với context rỗng, request=None, TENANT, LANDLORD, ADMIN | Data: 5 context | Expected: chỉ LANDLORD và ADMIN trả True"""
        self.assertFalse(_viewer_is_manager(SimpleNamespace(context={})))
        self.assertFalse(_viewer_is_manager(SimpleNamespace(context={'request': None})))
        self.assertFalse(_viewer_is_manager(SimpleNamespace(context={'request': SimpleNamespace(user=fake_user(role='TENANT'))})))
        self.assertTrue(_viewer_is_manager(SimpleNamespace(context={'request': SimpleNamespace(user=fake_user(role='LANDLORD'))})))
        self.assertTrue(_viewer_is_manager(SimpleNamespace(context={'request': SimpleNamespace(user=fake_user(role='ADMIN'))})))

    def test_signing_key_is_configured(self):
        """S2-SEC-018 | Khóa ký JWT dùng chung được cấu hình | Data: settings.SIMPLE_JWT | Expected: SIGNING_KEY khác rỗng và dùng claim user_id"""
        self.assertTrue(settings.SIMPLE_JWT['SIGNING_KEY'])
        self.assertEqual(settings.SIMPLE_JWT['USER_ID_CLAIM'], 'user_id')
