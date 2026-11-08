import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from services.identity_service.models import UserRole
from services.property_service.models import Property, Room, RoomStatus

User = get_user_model()

def seed():
    print("=" * 60)
    print("🚀 SEEDING INITIAL DATA FOR SPRINT 1 (SOA ARCHITECTURE)")
    print("=" * 60)

    # -------------------------------------------------------------
    # 1. IDENTITY SERVICE (default database: nhatro_identity_db)
    # -------------------------------------------------------------
    print("\n[1/2] Seeding Identity Service (nhatro_identity_db)...")

    # Admin
    admin_user, created = User.objects.using('default').get_or_create(
        username='admin',
        defaults={
            'email': 'admin@nhatro.vn',
            'first_name': 'Hệ Thống',
            'last_name': 'Admin',
            'role': UserRole.ADMIN,
            'is_staff': True,
            'is_superuser': True,
            'phone_number': '0900000001',
            'identity_card': '079090000001',
            'address': 'Quận 1, TP. Hồ Chí Minh'
        }
    )
    if created:
        admin_user.set_password('adminpassword123')
        admin_user.save(using='default')
        print("  [+] Admin user created: admin / adminpassword123")
    else:
        print("  [ok] Admin user already exists.")

    # Landlord (Chủ trọ)
    landlord, created = User.objects.using('default').get_or_create(
        username='chutro1',
        defaults={
            'email': 'chutro1@nhatro.vn',
            'first_name': 'Nguyễn Văn',
            'last_name': 'An',
            'role': UserRole.LANDLORD,
            'phone_number': '0901234567',
            'identity_card': '079092001122',
            'address': '123 Đường D2, P. 25, Q. Bình Thạnh, TP.HCM'
        }
    )
    if created:
        landlord.set_password('chutropassword123')
        landlord.save(using='default')
        print("  [+] Landlord user created: chutro1 / chutropassword123 (ID: %s)" % landlord.id)
    else:
        print("  [ok] Landlord user already exists (ID: %s)." % landlord.id)

    # Tenant (Khách thuê)
    tenant, created = User.objects.using('default').get_or_create(
        username='khach1',
        defaults={
            'email': 'khach1@gmail.com',
            'first_name': 'Trần Thị',
            'last_name': 'Mai',
            'role': UserRole.TENANT,
            'phone_number': '0912345678',
            'identity_card': '079198003344',
            'address': 'Tiền Giang'
        }
    )
    if created:
        tenant.set_password('khachpassword123')
        tenant.save(using='default')
        print("  [+] Tenant user created: khach1 / khachpassword123")
    else:
        print("  [ok] Tenant user already exists.")

    # -------------------------------------------------------------
    # 2. PROPERTY SERVICE (property_db: nhatro_property_db)
    # -------------------------------------------------------------
    print("\n[2/2] Seeding Property & Room Service (nhatro_property_db)...")
    landlord_id = landlord.id

    prop1, created = Property.objects.using('property_db').get_or_create(
        name='Nhà trọ Hoa Mai - Bình Thạnh',
        owner_id=landlord_id,
        defaults={
            'address': '45/12 Đường Nguyễn Gia Trí, Phường 25',
            'ward': 'Phường 25',
            'district': 'Bình Thạnh',
            'city': 'TP. Hồ Chí Minh',
            'total_floors': 3,
            'electricity_rate': 3800.0,
            'water_rate': 25000.0,
            'internet_rate': 100000.0,
            'description': 'Nhà trọ sinh viên gần ĐH Hutech, Ngoại Thương, an ninh 24/7.',
            'rules': '- Không tụ tập nhậu nhẹt sau 23h\n- Giữ gìn vệ sinh chung khuôn viên',
            'image_url': 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80'
        }
    )
    if created:
        print("  [+] Property 1 created: Nhà trọ Hoa Mai (owner_id=%s)" % landlord_id)
    else:
        print("  [ok] Property 1 already exists.")

    prop2, created = Property.objects.using('property_db').get_or_create(
        name='Căn hộ Mini Happy House - Quận 7',
        owner_id=landlord_id,
        defaults={
            'address': '88 Đường số 7, KDC Tân Quy Đông',
            'ward': 'Tân Phong',
            'district': 'Quận 7',
            'city': 'TP. Hồ Chí Minh',
            'total_floors': 4,
            'electricity_rate': 4000.0,
            'water_rate': 30000.0,
            'internet_rate': 120000.0,
            'description': 'Căn hộ mini cao cấp full nội thất, thang máy, bãi đỗ xe hơi.',
            'rules': '- Cho nuôi thú cưng nhỏ có cam kết\n- Để xe đúng vị trí quy định',
            'image_url': 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80'
        }
    )
    if created:
        print("  [+] Property 2 created: Happy House (owner_id=%s)" % landlord_id)
    else:
        print("  [ok] Property 2 already exists.")

    # Rooms for Property 1
    rooms_data_1 = [
        {
            'room_number': '101', 'floor': 1, 'area': 22.5, 'rent_price': 3500000,
            'deposit_amount': 3500000, 'max_occupants': 2, 'status': RoomStatus.AVAILABLE,
            'amenities': 'Gác lửng, Máy lạnh Inverter, Kệ bếp, WC riêng',
            'description': 'Phòng tầng trệt rộng rãi, thoáng mát.',
            'initial_electric_reading': 120.0, 'initial_water_reading': 45.0,
        },
        {
            'room_number': '102', 'floor': 1, 'area': 20.0, 'rent_price': 3200000,
            'deposit_amount': 3200000, 'max_occupants': 2, 'status': RoomStatus.OCCUPIED,
            'amenities': 'Gác lửng, Quạt trần, WC riêng',
            'description': 'Phòng đang cho sinh viên thuê.',
            'initial_electric_reading': 85.0, 'initial_water_reading': 30.0,
        },
        {
            'room_number': '201', 'floor': 2, 'area': 25.0, 'rent_price': 4200000,
            'deposit_amount': 4200000, 'max_occupants': 3, 'status': RoomStatus.AVAILABLE,
            'amenities': 'Ban công view đường, Máy lạnh, Tủ lạnh, WC riêng',
            'description': 'Phòng góc hai mặt thoáng gió mát mẻ.',
            'initial_electric_reading': 210.0, 'initial_water_reading': 60.0,
        },
        {
            'room_number': '202', 'floor': 2, 'area': 24.0, 'rent_price': 3900000,
            'deposit_amount': 3900000, 'max_occupants': 3, 'status': RoomStatus.RESERVED,
            'amenities': 'Máy lạnh, Gác lửng, Bình nước nóng',
            'description': 'Khách đã cọc giữ phòng đến 15 hàng tháng.',
            'initial_electric_reading': 150.0, 'initial_water_reading': 50.0,
        },
        {
            'room_number': '301', 'floor': 3, 'area': 20.0, 'rent_price': 3000000,
            'deposit_amount': 3000000, 'max_occupants': 2, 'status': RoomStatus.MAINTENANCE,
            'amenities': 'Gác lửng, Quạt trần, Cửa sổ thoáng',
            'description': 'Đang sửa chữa và sơn mới tường.',
            'initial_electric_reading': 40.0, 'initial_water_reading': 15.0,
        },
    ]

    for r_data in rooms_data_1:
        Room.objects.using('property_db').get_or_create(
            property=prop1,
            room_number=r_data['room_number'],
            defaults=r_data
        )

    # Rooms for Property 2
    rooms_data_2 = [
        {
            'room_number': 'P.101', 'floor': 1, 'area': 30.0, 'rent_price': 5500000,
            'deposit_amount': 5500000, 'max_occupants': 2, 'status': RoomStatus.AVAILABLE,
            'amenities': 'Full nội thất, Sofa, Máy giặt riêng, Smart TV',
            'description': 'Căn hộ Studio tiện nghi cao cấp.',
            'initial_electric_reading': 310.0, 'initial_water_reading': 80.0,
        },
        {
            'room_number': 'P.201', 'floor': 2, 'area': 32.0, 'rent_price': 6000000,
            'deposit_amount': 6000000, 'max_occupants': 3, 'status': RoomStatus.OCCUPIED,
            'amenities': 'Full nội thất cao cấp, Ban công riêng rộng',
            'description': 'Khách là chuyên gia thuê lâu dài.',
            'initial_electric_reading': 420.0, 'initial_water_reading': 110.0,
        },
    ]

    for r_data in rooms_data_2:
        Room.objects.using('property_db').get_or_create(
            property=prop2,
            room_number=r_data['room_number'],
            defaults=r_data
        )

    print("\n✅ SEEDING COMPLETED SUCCESSFULLY FOR SPRINT 1!")
    print("=" * 60)

if __name__ == '__main__':
    seed()
