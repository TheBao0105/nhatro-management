"""
Gọi API giữa các service (service-to-service) để kiểm tra quyền sở hữu dữ liệu.

Nguyên tắc:
- Luôn chuyển tiếp JWT của chính người dùng -> service đích tự áp phạm vi theo role của họ.
- Không có FK chéo service; liên kết bằng ID qua API.
- Fail-closed: service đích không phản hồi / phản hồi bất thường -> 503, KHÔNG mặc định cho phép.

Quan hệ ID (nguồn sự thật: Tenant Service):
    user_id   : ID tài khoản (Identity Service, claim `user_id` trong JWT)
    tenant_id : ID hồ sơ người thuê (TenantProfile.id) — Contract.tenant_id / Invoice.tenant_id
    room_id   : ID phòng (Property Service) — TenantProfile.room_id
"""
import requests
from django.conf import settings
from rest_framework.exceptions import APIException, NotAuthenticated

SERVICE_NAMES = {
    'identity': 'Identity Service',
    'property': 'Property Service',
    'tenant': 'Tenant Service',
    'contract': 'Contract Service',
    'billing': 'Billing Service',
}

# Hồ sơ người thuê ở trạng thái này coi như "đang thuê" phòng room_id.
ACTIVE_TENANT_STATUS = 'ACTIVE'
MOVED_OUT_STATUS = 'MOVED_OUT'
# Hợp đồng ở các trạng thái này coi như còn ràng buộc với phòng (không được xóa phòng).
ACTIVE_CONTRACT_STATUSES = ('DRAFT', 'ACTIVE', 'EXTENDED')


class DependencyUnavailable(APIException):
    status_code = 503
    default_detail = 'Không xác minh được quyền truy cập vì service liên quan không phản hồi.'
    default_code = 'dependency_unavailable'


def auth_header_from_request(request):
    header = request.META.get('HTTP_AUTHORIZATION', '')
    return header if header.startswith('Bearer ') else None


def auth_header_from_user(user):
    """TokenUser (service stateless) giữ token đã xác minh -> dựng lại header Bearer."""
    token = getattr(user, 'token', None)
    return f'Bearer {token}' if token is not None else None


def _get(service, path, auth_header):
    if not auth_header:
        raise NotAuthenticated()
    base = settings.SERVICE_URLS[service].rstrip('/')
    name = SERVICE_NAMES.get(service, service)
    try:
        resp = requests.get(f'{base}{path}', headers={'Authorization': auth_header},
                            timeout=getattr(settings, 'INTER_SERVICE_TIMEOUT', 3))
    except requests.RequestException:
        raise DependencyUnavailable(f'{name} không phản hồi — không xác minh được quyền truy cập dữ liệu.')
    if resp.status_code == 401:
        raise NotAuthenticated()
    return resp, name


def fetch_tenant_links(auth_header):
    """
    GET Tenant Service /api/tenants/links/ bằng JWT của người dùng.
    Trả về danh sách {tenant_id, user_id, room_id, landlord_id, status} trong phạm vi của họ:
    TENANT/STAFF -> hồ sơ gắn với user_id của mình; LANDLORD -> hồ sơ mình quản lý; ADMIN -> tất cả.
    """
    resp, name = _get('tenant', '/api/tenants/links/', auth_header)
    try:
        data = resp.json() if resp.status_code == 200 else None
    except ValueError:
        data = None
    if not isinstance(data, list) or not all(isinstance(i, dict) for i in data):
        raise DependencyUnavailable(f'{name} trả về dữ liệu liên kết không hợp lệ (HTTP {resp.status_code}).')
    return data


def tenant_links_for_user(user):
    """Như fetch_tenant_links nhưng cache trên đối tượng user (tối đa 1 lần gọi / request)."""
    cached = getattr(user, '_tenant_links_cache', None)
    if cached is None:
        cached = fetch_tenant_links(auth_header_from_user(user))
        try:
            user._tenant_links_cache = cached
        except AttributeError:
            pass
    return cached


def own_tenant_ids(user):
    """tenant_id (TenantProfile.id) của chính tài khoản đang đăng nhập — mọi trạng thái (gồm lịch sử)."""
    return sorted({int(link['tenant_id']) for link in tenant_links_for_user(user) if link.get('tenant_id')})


def own_rented_room_ids(user):
    """room_id các phòng tài khoản đang đăng nhập ĐANG thuê (hồ sơ ACTIVE)."""
    return sorted({int(link['room_id']) for link in tenant_links_for_user(user)
                   if link.get('room_id') and link.get('status') == ACTIVE_TENANT_STATUS})


def room_accessible(auth_header, room_id):
    """Property Service có trả phòng này trong phạm vi của người dùng không (200 -> True, 403/404 -> False)."""
    resp, name = _get('property', f'/api/rooms/{int(room_id)}/', auth_header)
    if resp.status_code == 200:
        return True
    if resp.status_code in (403, 404):
        return False
    raise DependencyUnavailable(f'{name} không xác minh được phòng #{room_id} (HTTP {resp.status_code}).')


def tenant_account_eligible(auth_header, user_id):
    """
    Identity Service: tài khoản user_id có được gắn vào hồ sơ người thuê không (role TENANT, đang hoạt động).
    Gọi bằng JWT của người dùng (ADMIN/LANDLORD). 404 -> False; phản hồi bất thường -> 503 (fail-closed).
    """
    resp, name = _get('identity', f'/api/users/{int(user_id)}/tenant-link-eligibility/', auth_header)
    if resp.status_code == 404:
        return False
    if resp.status_code == 200:
        try:
            data = resp.json()
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get('eligible'), bool):
            return data['eligible']
    raise DependencyUnavailable(f'{name} không xác minh được tài khoản #{user_id} (HTTP {resp.status_code}).')


def fetch_room_contracts(auth_header, room_id):
    """
    GET Contract Service /api/contracts/?room_id=<id> bằng JWT của người dùng.
    Trả về danh sách hợp đồng gắn với phòng trong phạm vi người gọi.
    """
    resp, name = _get('contract', f'/api/contracts/?room_id={int(room_id)}', auth_header)
    try:
        data = resp.json() if resp.status_code == 200 else None
    except ValueError:
        data = None
    if isinstance(data, dict) and isinstance(data.get('results'), list):
        data = data['results']
    if not isinstance(data, list) or not all(isinstance(i, dict) for i in data):
        raise DependencyUnavailable(f'{name} trả về dữ liệu hợp đồng không hợp lệ (HTTP {resp.status_code}).')
    return data


def room_external_block_reason(user, room_id):
    """
    Kiểm tra liên kết từ Tenant Service và Contract Service trước khi xóa phòng:
    - Có hồ sơ người thuê đang gắn với phòng (status != MOVED_OUT) -> chặn xóa.
    - Có hợp đồng còn hiệu lực hoặc bản nháp (DRAFT, ACTIVE, EXTENDED) -> chặn xóa.
    Trả về chuỗi lý do nếu phải chặn, hoặc None nếu không còn liên kết đang hoạt động.
    """
    rid = int(room_id)
    for link in tenant_links_for_user(user):
        if link.get('room_id') == rid and link.get('status') != MOVED_OUT_STATUS:
            return 'đang có hồ sơ khách thuê liên kết'
    auth_header = auth_header_from_user(user)
    for contract in fetch_room_contracts(auth_header, rid):
        if contract.get('room_id') in (None, rid) and contract.get('status') in ACTIVE_CONTRACT_STATUSES:
            return 'đang có hợp đồng thuê còn hiệu lực'
    return None
