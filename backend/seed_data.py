import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from services.identity_service.models import UserRole
from services.property_service.models import Property, Room, RoomStatus, MaintenanceRequest, MaintenancePriority, MaintenanceStatus

User = get_user_model()

def seed():
    print("--- SEEDING INITIAL DATA FOR SPRINT 1 ---")

    # 1. Admin
    admin_user, created = User.objects.get_or_create(
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
        admin_user.save()
        print("Created Admin user: admin / adminpassword123")
    else:
        print("Admin user already exists.")

    # 2. Landlord (Chủ trọ)
    landlord, created = User.objects.get_or_create(
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
        landlord.save()
        print("Created Landlord user: chutro1 / chutropassword123")
    else:
        print("Landlord user already exists.")

    # 3. Tenant (Khách thuê)
    tenant, created = User.objects.get_or_create(
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
        tenant.save()
        print("Created Tenant user: khach1 / khachpassword123")
    else:
        print("Tenant user already exists.")

    # 4. Properties (Nhà trọ)
    prop1, created = Property.objects.get_or_create(
        name='Nhà trọ Hoa Mai - Bình Thạnh',
        landlord=landlord,
        defaults={
            'address': '45/12 Đường Nguyễn Gia Trí, Phường 25',
            'ward': 'Phường 25',
            'district': 'Bình Thạnh',
            'city': 'TP. Hồ Chí Minh',
            'total_floors': 3,
            'electricity_rate': 3800.0,
            'water_rate': 25000.0,
            'internet_rate': 100000.0,
            'description': 'Nhà trọ sinh viên gần ĐH Hutech, Ngoại Thương. Giờ giấc tự do, khóa vân tay, camera 24/7, sân thượng phơi đồ thoáng mát.',
            'rules': '- Không tụ tập nhậu nhẹt sau 23h\n- Giữ gìn vệ sinh chung nơi để xe và hành lang\n- Đóng tiền phòng đúng hạn ngày 05 hàng tháng',
            'image_url': 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80'
        }
    )
    if created:
        print("Created Property 1: Nhà trọ Hoa Mai")

    prop2, created = Property.objects.get_or_create(
        name='Tòa nhà Căn hộ Mini Happy House - Quận 7',
        landlord=landlord,
        defaults={
            'address': '88 Đường số 7, KDC Tân Quy Đông',
            'ward': 'Tân Phong',
            'district': 'Quận 7',
            'city': 'TP. Hồ Chí Minh',
            'total_floors': 4,
            'electricity_rate': 4000.0,
            'water_rate': 30000.0,
            'internet_rate': 120000.0,
            'description': 'Căn hộ mini cao cấp full nội thất: giường nệm cao su, máy giặt riêng, bếp từ âm, ban công thoáng gió view công viên.',
            'rules': '- Cho nuôi thú cưng nhỏ có cam kết\n- Để xe đúng vị trí vạch kẻ tầng trệt',
            'image_url': 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80'
        }
    )
    if created:
        print("Created Property 2: Happy House")

    # 5. Rooms for Property 1
    rooms_data_1 = [
        {
            'room_number': '101', 'floor': 1, 'area': 22.5, 'rent_price': 3500000,
            'deposit_amount': 3500000, 'max_occupants': 2, 'status': RoomStatus.AVAILABLE,
            'amenities': 'Gác lửng, Máy lạnh Inverter, Kệ bếp, WC riêng',
            'description': 'Phòng tầng trệt rộng rãi, xe để trước cửa phòng tiện lợi.'
        },
        {
            'room_number': '102', 'floor': 1, 'area': 20.0, 'rent_price': 3200000,
            'deposit_amount': 3200000, 'max_occupants': 2, 'status': RoomStatus.OCCUPIED,
            'amenities': 'Gác lửng, Quạt trần, WC riêng',
            'description': 'Phòng đang cho sinh viên thuê.'
        },
        {
            'room_number': '201', 'floor': 2, 'area': 25.0, 'rent_price': 4200000,
            'deposit_amount': 4200000, 'max_occupants': 3, 'status': RoomStatus.AVAILABLE,
            'amenities': 'Ban công view đường, Máy lạnh, Tủ lạnh 150L, Gác cao đứng được',
            'description': 'Phòng góc hai mặt thoáng mát, nhiều ánh sáng tự nhiên.'
        },
        {
            'room_number': '202', 'floor': 2, 'area': 24.0, 'rent_price': 3900000,
            'deposit_amount': 3900000, 'max_occupants': 3, 'status': RoomStatus.RESERVED,
            'amenities': 'Máy lạnh, Gác lửng, Nóng lạnh mặt trời',
            'description': 'Khách đã cọc giữ phòng ngày 10 dọn vào.'
        },
        {
            'room_number': '301', 'floor': 3, 'area': 20.0, 'rent_price': 3000000,
            'deposit_amount': 3000000, 'max_occupants': 2, 'status': RoomStatus.MAINTENANCE,
            'amenities': 'Gác lửng, Quạt trần',
            'description': 'Đang thay thế vòi sen và bảo trì đường nước toilet.'
        },
    ]

    for r_data in rooms_data_1:
        Room.objects.get_or_create(
            property=prop1,
            room_number=r_data['room_number'],
            defaults=r_data
        )

    # 6. Rooms for Property 2
    rooms_data_2 = [
        {
            'room_number': 'P.101', 'floor': 1, 'area': 30.0, 'rent_price': 5500000,
            'deposit_amount': 5500000, 'max_occupants': 2, 'status': RoomStatus.AVAILABLE,
            'amenities': 'Full nội thất, Sofa, Máy giặt riêng, Smart TV 43 inch, Bếp từ',
            'description': 'Căn hộ Studio cửa sổ lớn ngập tràn ánh nắng.'
        },
        {
            'room_number': 'P.201', 'floor': 2, 'area': 32.0, 'rent_price': 6000000,
            'deposit_amount': 6000000, 'max_occupants': 3, 'status': RoomStatus.OCCUPIED,
            'amenities': 'Full nội thất cao cấp, Ban công riêng rộng',
            'description': 'Khách người đi làm thuê lâu dài.'
        },
    ]

    for r_data in rooms_data_2:
        Room.objects.get_or_create(
            property=prop2,
            room_number=r_data['room_number'],
            defaults=r_data
        )

    # 7. Sample Maintenance Request
    m_room = prop1.rooms.filter(room_number='301').first()
    if m_room:
        MaintenanceRequest.objects.get_or_create(
            property=prop1,
            room=m_room,
            title='Hư vòi sen và rò rỉ nước toilet',
            defaults={
                'reported_by': landlord,
                'description': 'Vòi sen tắm bị rỉ nước liên tục làm tăng số nước của phòng. Cần thay van nước mới.',
                'priority': MaintenancePriority.HIGH,
                'status': MaintenanceStatus.IN_PROGRESS,
                'cost': 250000.0
            }
        )

    print("--- SEEDING COMPLETED SUCCESSFULLY! ---")

if __name__ == '__main__':
    seed()

