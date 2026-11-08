import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../core/constants/api_constants.dart';
import '../../core/network/api_client.dart';
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
    // 0: SERVICE 2 — Property & Room Management (Sprint 1)
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
        'Lịch sử cư trú và chuyển đổi phòng',
        'Quản lý thành viên cùng phòng',
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
        'Tạo mới hợp đồng điện tử theo mẫu pháp lý chuẩn',
        'Gia hạn hợp đồng (Contract Extension)',
        'Thanh lý hợp đồng và hoàn tiền cọc',
        'Xuất hợp đồng chuẩn định dạng PDF & Chữ ký điện tử',
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
        'Quản lý trạng thái phiếu thu (Chưa thanh toán, Đã thanh toán, Quá hạn)',
        'Gửi thông báo đẩy và email nhắc hạn đóng tiền phòng định kỳ',
      ],
    ),

    // 4: SERVICE 1 & ARCHITECTURE — Identity, Role Authorization & SOA Integration
    const _ProfileAndArchitectureTab(),
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
        indicatorColor: const Color(0xFFEFF6FF),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.apartment_outlined),
            selectedIcon: Icon(Icons.apartment_rounded, color: Color(0xFF2563EB)),
            label: 'Nhà trọ',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline_rounded),
            selectedIcon: Icon(Icons.people_rounded, color: Color(0xFF0D9488)),
            label: 'Người thuê',
          ),
          NavigationDestination(
            icon: Icon(Icons.assignment_outlined),
            selectedIcon: Icon(Icons.assignment_rounded, color: Color(0xFF7C3AED)),
            label: 'Hợp đồng',
          ),
          NavigationDestination(
            icon: Icon(Icons.receipt_long_outlined),
            selectedIcon: Icon(Icons.receipt_long_rounded, color: Color(0xFFEA580C)),
            label: 'Hóa đơn',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline_rounded),
            selectedIcon: Icon(Icons.person_rounded, color: Color(0xFF2563EB)),
            label: 'Tài khoản',
          ),
        ],
      ),
    );
  }
}

class _ProfileAndArchitectureTab extends StatefulWidget {
  const _ProfileAndArchitectureTab();

  @override
  State<_ProfileAndArchitectureTab> createState() => _ProfileAndArchitectureTabState();
}

class _ProfileAndArchitectureTabState extends State<_ProfileAndArchitectureTab> {
  Map<String, dynamic>? _architectureData;
  bool _isLoadingArch = false;

  @override
  void initState() {
    super.initState();
    _fetchArchitectureStatus();
  }

  Future<void> _fetchArchitectureStatus() async {
    setState(() => _isLoadingArch = true);
    try {
      final res = await ApiClient.get(ApiConstants.architectureStatus, requireAuth: false);
      if (res is Map<String, dynamic> && mounted) {
        setState(() {
          _architectureData = res;
          _isLoadingArch = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoadingArch = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final user = auth.user;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Tài Khoản & Kiến Trúc SOA', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: _fetchArchitectureStatus,
            tooltip: 'Kiểm tra lại',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(18),
        child: Column(
          children: [
            // 1. User Profile Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0xFFE2E8F0)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.02),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 36,
                    backgroundColor: const Color(0xFFEFF6FF),
                    child: Text(
                      (user?.displayName.isNotEmpty ?? false)
                          ? user!.displayName[0].toUpperCase()
                          : 'U',
                      style: const TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF2563EB),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    user?.displayName ?? 'Người dùng',
                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: Color(0xFF0F172A)),
                  ),
                  const SizedBox(height: 3),
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

            const SizedBox(height: 16),

            // 2. Identity info
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Thông tin tài khoản (Identity Service)',
                    style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                  ),
                  const SizedBox(height: 12),
                  _buildRow(Icons.phone_outlined, 'Số điện thoại', user?.phoneNumber ?? 'Chưa cập nhật'),
                  const Divider(height: 18, color: Color(0xFFF1F5F9)),
                  _buildRow(Icons.email_outlined, 'Email', user?.email ?? 'Chưa cập nhật'),
                  const Divider(height: 18, color: Color(0xFFF1F5F9)),
                  _buildRow(Icons.badge_outlined, 'Số CCCD / CMND', user?.identityCard ?? 'Chưa cập nhật'),
                  const Divider(height: 18, color: Color(0xFFF1F5F9)),
                  _buildRow(Icons.home_outlined, 'Địa chỉ thường trú', user?.address ?? 'Chưa cập nhật'),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // 3. ⚙️ Project Setup & Architecture: Service Integration Check
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.hub_rounded, size: 20, color: Color(0xFF2563EB)),
                          SizedBox(width: 8),
                          Text(
                            'Kiến trúc SOA & Tách biệt Database',
                            style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                          ),
                        ],
                      ),
                      if (_isLoadingArch)
                        const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      else
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: const Color(0xFFDCFCE7),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Text(
                            'KẾT NỐI OK',
                            style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: Color(0xFF15803D)),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Mỗi service sở hữu 1 database riêng biệt, độc lập hoàn toàn, không liên kết khóa ngoại (Foreign Key) chéo.',
                    style: TextStyle(fontSize: 12.5, color: Color(0xFF64748B)),
                  ),
                  const SizedBox(height: 14),

                  _buildDbStatusTile(
                    'Identity Service',
                    'nhatro_identity_db',
                    _architectureData?['databases_health']?['default']?['status'] == 'HEALTHY'
                        ? 'Tài khoản, Phân quyền, JWT (Sẵn sàng)'
                        : 'Tài khoản, Phân quyền, JWT',
                    isReady: true,
                    sprint: 'Sprint 1',
                  ),
                  const SizedBox(height: 8),
                  _buildDbStatusTile(
                    'Property Service',
                    'nhatro_property_db',
                    _architectureData?['databases_health']?['property_db']?['status'] == 'HEALTHY'
                        ? 'Nhà trọ, Phòng trọ, Tỷ lệ trống (Sẵn sàng)'
                        : 'Nhà trọ, Phòng trọ, Tỷ lệ trống',
                    isReady: true,
                    sprint: 'Sprint 1',
                  ),
                  const SizedBox(height: 8),
                  _buildDbStatusTile(
                    'Tenant Service',
                    'nhatro_tenant_db',
                    'Quản lý hồ sơ khách thuê',
                    isReady: false,
                    sprint: 'Sprint 2 (Kế hoạch)',
                  ),
                  const SizedBox(height: 8),
                  _buildDbStatusTile(
                    'Contract Service',
                    'nhatro_contract_db',
                    'Quản lý hợp đồng & gia hạn',
                    isReady: false,
                    sprint: 'Sprint 2 (Kế hoạch)',
                  ),
                  const SizedBox(height: 8),
                  _buildDbStatusTile(
                    'Billing & Notification',
                    'nhatro_billing_db',
                    'Hóa đơn điện nước & VietQR',
                    isReady: false,
                    sprint: 'Sprint 3 (Kế hoạch)',
                  ),
                ],
              ),
            ),

            const SizedBox(height: 22),

            // Logout Button
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFFDC2626),
                side: const BorderSide(color: Color(0xFFFCA5A5)),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 13),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              icon: const Icon(Icons.logout_rounded, size: 18),
              label: const Text('ĐĂNG XUẤT', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
              onPressed: () {
                showDialog(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: const Text('Xác nhận đăng xuất?'),
                    content: const Text('Bạn có chắc chắn muốn đăng xuất khỏi phiên làm việc hiện tại?'),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.of(ctx).pop(),
                        child: const Text('HỦY'),
                      ),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFDC2626)),
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
        Text(title, style: const TextStyle(fontSize: 13, color: Color(0xFF64748B), fontWeight: FontWeight.w500)),
        const Spacer(),
        Text(val, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, color: Color(0xFF0F172A))),
      ],
    );
  }

  Widget _buildDbStatusTile(
    String serviceName,
    String dbName,
    String desc, {
    required bool isReady,
    required String sprint,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: isReady ? const Color(0xFFDCFCE7) : const Color(0xFFFEF3C7),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              isReady ? Icons.check_circle_rounded : Icons.pending_rounded,
              size: 16,
              color: isReady ? const Color(0xFF16A34A) : const Color(0xFFD97706),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      serviceName,
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                    ),
                    Text(
                      sprint,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: isReady ? const Color(0xFF16A34A) : const Color(0xFFD97706),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  'DB: $dbName • $desc',
                  style: const TextStyle(fontSize: 11.5, color: Color(0xFF64748B)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
