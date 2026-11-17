import 'package:flutter/material.dart';

import '../../core/constants/api_constants.dart';
import '../../core/theme/app_theme.dart';
import '../auth/profile_screen.dart';
import '../property/property_list_screen.dart';
import '../future_services/future_service_screen.dart';

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;

  final List<Widget> _pages = [
    // 0: SERVICE 2 — Property & Room Management
    const PropertyListScreen(),

    // 1: SERVICE 3 — Tenant Service (Sprint 2)
    FutureServiceScreen(
      title: 'Quản Lý Người Thuê',
      serviceName: 'SERVICE 3 — TENANT SERVICE',
      sprintName: '🟡 SPRINT 2 — Lộ trình tiếp theo',
      icon: Icons.people_alt_rounded,
      themeColor: const Color(0xFF0D9488),
      statusApiUrl: ApiConstants.tenantStatus,
      plannedFeatures: const [
        'Hồ sơ định danh khách thuê (CCCD/CMND, quê quán, nghề nghiệp)',
        'Quản lý khai báo đăng ký tạm trú',
        'Lịch sử cư trú và đổi chuyển phòng trọ',
        'Lưu trữ thông tin liên hệ khẩn cấp của người thân',
      ],
    ),

    // 2: SERVICE 4 — Contract Service (Sprint 2)
    FutureServiceScreen(
      title: 'Hợp Đồng Thuê Trọ',
      serviceName: 'SERVICE 4 — CONTRACT SERVICE',
      sprintName: '🟡 SPRINT 2 — Lộ trình tiếp theo',
      icon: Icons.assignment_rounded,
      themeColor: const Color(0xFF7C3AED),
      statusApiUrl: ApiConstants.contractStatus,
      plannedFeatures: const [
        'Tạo mới hợp đồng thuê phòng trực tiếp trên app',
        'Gia hạn hợp đồng (Contract Extension)',
        'Kết thúc / Thanh lý hợp đồng & Hoàn tiền cọc',
        'Xuất hợp đồng chuẩn mẫu pháp lý dạng PDF & Chữ ký điện tử',
      ],
    ),

    // 3: SERVICE 5 — Billing & Notification Service (Sprint 3)
    FutureServiceScreen(
      title: 'Hóa Đơn & Thông Báo',
      serviceName: 'SERVICE 5 — BILLING & NOTIFICATION',
      sprintName: '⚪ SPRINT 3 — Sắp ra mắt',
      icon: Icons.receipt_long_rounded,
      themeColor: const Color(0xFFEA580C),
      statusApiUrl: ApiConstants.billingStatus,
      plannedFeatures: const [
        'Tính toán hóa đơn phòng + điện nước tự động theo chỉ số công tơ',
        'Tạo mã QR VietQR chuyển khoản ngân hàng tự động kèm nội dung',
        'Quản lý trạng thái thanh toán (Chưa thanh toán, Đã trả, Quá hạn)',
        'Gửi thông báo đẩy và email nhắc hạn đóng tiền phòng định kỳ',
      ],
    ),

    // 4: SERVICE 1 — Identity (Tài khoản & Phân quyền)
    const ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _currentIndex, children: _pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        backgroundColor: Colors.white,
        elevation: 3,
        indicatorColor: AppTheme.primary.withOpacity(0.12),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.apartment_outlined),
            selectedIcon: Icon(Icons.apartment, color: AppTheme.primary),
            label: 'Nhà trọ',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline),
            selectedIcon: Icon(Icons.people, color: Color(0xFF0D9488)),
            label: 'Người thuê',
          ),
          NavigationDestination(
            icon: Icon(Icons.assignment_outlined),
            selectedIcon: Icon(Icons.assignment, color: Color(0xFF7C3AED)),
            label: 'Hợp đồng',
          ),
          NavigationDestination(
            icon: Icon(Icons.receipt_long_outlined),
            selectedIcon: Icon(Icons.receipt_long, color: Color(0xFFEA580C)),
            label: 'Hóa đơn',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person, color: AppTheme.primary),
            label: 'Tài khoản',
          ),
        ],
      ),
    );
  }
}
