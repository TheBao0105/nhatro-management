"""Factory/helper dùng chung cho test Service 2 (không phải module test: tên không khớp `test*.py`)."""
from types import SimpleNamespace
from unittest import mock

from services.property_service.models import Property, Room

OWNER_ID = 101
OTHER_OWNER_ID = 202
TENANT_USER_ID = 555

# Điểm vá duy nhất để cô lập Tenant Service khi kiểm tra phạm vi dữ liệu của TENANT.
RENTED_ROOMS_TARGET = 'services.property_service.views.own_rented_room_ids'


def make_property(**overrides):
    data = {
        'owner_id': OWNER_ID,
        'name': 'Nhà trọ Test',
        'address': '1 Đường Test',
        'ward': 'Phường 1',
        'district': 'Quận 1',
        'total_floors': 5,
    }
    data.update(overrides)
    return Property.objects.create(**data)


def make_room(prop, **overrides):
    data = {
        'property': prop,
        'room_number': '101',
        'floor': 1,
        'area': 20.0,
        'rent_price': 3000000,
        'max_occupants': 2,
    }
    data.update(overrides)
    return Room.objects.create(**data)


def fake_user(user_id=OWNER_ID, role='LANDLORD', is_superuser=False, authenticated=True, **extra):
    """Đối tượng giống TokenUser (claims JWT) — dùng cho test thuần đơn vị, không cần HTTP."""
    return SimpleNamespace(id=user_id, role=role, is_superuser=is_superuser,
                           is_authenticated=authenticated, **extra)


def serializer_context(user=None):
    """Context giống DRF view truyền vào serializer (`request.user`)."""
    return {'request': SimpleNamespace(user=user or fake_user())}


def patch_rented_rooms(room_ids):
    """Giả lập Tenant Service: tài khoản TENANT đang thuê các phòng `room_ids`."""
    return mock.patch(RENTED_ROOMS_TARGET, return_value=sorted(room_ids))
