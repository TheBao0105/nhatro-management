import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../core/constants/api_constants.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/status_badge.dart';
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
    const _ProfileTab(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
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

class _ProfileTab extends StatelessWidget {
  const _ProfileTab();

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final user = auth.user;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tài Khoản & Phân Quyền', style: TextStyle(fontWeight: FontWeight.w700)),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // User Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.04),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 38,
                    backgroundColor: AppTheme.primary.withOpacity(0.12),
                    child: Text(
                      (user?.displayName.isNotEmpty ?? false)
                          ? user!.displayName[0].toUpperCase()
                          : 'U',
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.primary,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    user?.displayName ?? 'Người dùng',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '@${user?.username ?? ''}',
                    style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                  ),
                  const SizedBox(height: 10),
                  RoleBadge(
                    role: user?.role ?? 'LANDLORD',
                    label: user?.roleDisplay,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // Profile info card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Thông tin định danh',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 14),
                    _buildRow(Icons.phone_outlined, 'Số điện thoại', user?.phoneNumber ?? 'Chưa cập nhật'),
                    const Divider(height: 16),
                    _buildRow(Icons.email_outlined, 'Email', user?.email ?? 'Chưa cập nhật'),
                    const Divider(height: 16),
                    _buildRow(Icons.badge_outlined, 'Số CCCD / CMND', user?.identityCard ?? 'Chưa cập nhật'),
                    const Divider(height: 16),
                    _buildRow(Icons.home_outlined, 'Địa chỉ thường trú', user?.address ?? 'Chưa cập nhật'),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 20),

            // System info card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Kiến trúc hệ thống (Sprint 1)',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 12),
                    _buildTechItem('Frontend', 'Flutter 3.x (Clean Provider State & Material 3)'),
                    _buildTechItem('Backend', 'Django 6.x REST Framework + SimpleJWT'),
                    _buildTechItem('Database', 'Microsoft SQL Server 2022 (mssql-django)'),
                    _buildTechItem('Dịch vụ hoạt động', 'SERVICE 1 — Identity & SERVICE 2 — Property'),
                    _buildTechItem('Dịch vụ scaffold sẵn', 'SERVICE 3 (Tenant), SERVICE 4 (Contract), SERVICE 5 (Billing)'),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

            // Logout Button
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.redAccent,
                side: const BorderSide(color: Colors.redAccent),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              icon: const Icon(Icons.logout),
              label: const Text('ĐĂNG XUẤT', style: TextStyle(fontWeight: FontWeight.w700)),
              onPressed: () {
                showDialog(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: const Text('Xác nhận đăng xuất?'),
                    content: const Text('Bạn có chắc chắn muốn đăng xuất khỏi tài khoản này?'),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.of(ctx).pop(),
                        child: const Text('HỦY'),
                      ),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
                        onPressed: () {
                          Navigator.of(ctx).pop();
                          auth.logout();
                        },
                        child: const Text('ĐĂNG XUẤT'),
                      ),
                    ],
                  ),
                );
              },
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildRow(IconData icon, String title, String val) {
    return Row(
      children: [
        Icon(icon, size: 18, color: const Color(0xFF64748B)),
        const SizedBox(width: 10),
        Text(title, style: const TextStyle(fontSize: 13, color: Color(0xFF64748B))),
        const Spacer(),
        Text(val, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
      ],
    );
  }

  Widget _buildTechItem(String title, String desc) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: const EdgeInsets.only(top: 4),
            width: 6,
            height: 6,
            decoration: const BoxDecoration(
              color: AppTheme.primary,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: const TextStyle(fontSize: 12.5, color: Color(0xFF334155)),
                children: [
                  TextSpan(text: '$title: ', style: const TextStyle(fontWeight: FontWeight.w700)),
                  TextSpan(text: desc),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

