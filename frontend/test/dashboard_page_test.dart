// Chặng 5 – Bước 3 (E5.2): Dashboard phản ánh đúng trạng thái dữ liệu từ backend.
// Dùng AppDataRepository THẬT + Gateway giả (MockClient) để đi qua đúng luồng syncWithBackend.
import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:nhatro_frontend/features/dashboard/presentation/dashboard_page.dart';
import 'package:nhatro_frontend/features/dashboard/presentation/widgets/monthly_revenue_chart.dart';
import 'package:nhatro_frontend/features/dashboard/presentation/widgets/room_ratio_chart.dart';
import 'package:nhatro_frontend/main.dart';
import 'package:nhatro_frontend/providers/auth_provider.dart';
import 'package:nhatro_frontend/shared/services/api_client.dart';
import 'package:nhatro_frontend/shared/services/app_data_repository.dart';
import 'package:shared_preferences/shared_preferences.dart';

http.Response _json(Object? body, [int status = 200]) => http.Response.bytes(
      utf8.encode(jsonEncode(body)),
      status,
      headers: const {'content-type': 'application/json; charset=utf-8'},
    );

class _LandlordAuth extends AuthProvider {
  @override
  AuthStatus get status => AuthStatus.authenticated;
  @override
  bool get isAuthenticated => true;
  @override
  String get role => 'LANDLORD';
  @override
  String get displayName => 'Chủ trọ Test';
  @override
  String get roleDisplay => 'Chủ nhà trọ';
}

/// Dạng phản hồi thật của GET /api/dashboard/summary/ (Gateway gộp 4 nguồn).
Map<String, dynamic> _summary({
  Map<String, dynamic> override = const {},
  List<Map<String, dynamic>> errors = const [],
}) =>
    {
      'total_properties': 2,
      'total_rooms': 5,
      'occupied_rooms': 3,
      'available_rooms': 1,
      'maintenance_rooms': 1,
      'reserved_rooms': 0,
      'full_rooms': 0,
      'inactive_rooms': 0,
      'occupancy_rate_percent': 60.0,
      'estimated_monthly_revenue': 12000000.0, // Property Service: tổng giá thuê phòng đang thuê
      'open_maintenance_requests': 1,
      'total_tenants': 3,
      'active_tenants': 3,
      'active_contracts': 3,
      'expiring_soon_contracts': 0,
      'unpaid_invoices': 2,
      'overdue_invoices': 1,
      'unpaid_amount': '3500000.00', // Billing Service trả chuỗi Decimal
      ...override,
      'errors': errors,
      'complete': errors.isEmpty,
    };

/// Các trường do Property Service cung cấp: null khi service đó DOWN (Gateway gộp với `errors`).
const _propertyFields = [
  'total_properties',
  'total_rooms',
  'occupied_rooms',
  'available_rooms',
  'maintenance_rooms',
  'reserved_rooms',
  'full_rooms',
  'inactive_rooms',
  'occupancy_rate_percent',
  'estimated_monthly_revenue',
  'open_maintenance_requests',
];

class _Gateway {
  final Map<String, FutureOr<http.Response> Function()> overrides = {};
  Completer<void>? holdAll;
  int healthCalls = 0;

  MockClient get client => MockClient((req) async {
        if (holdAll != null) await holdAll!.future;
        final path = req.url.path;
        if (path == '/api/system/health/') healthCalls++;
        final o = overrides[path];
        if (o != null) return o();
        switch (path) {
          case '/api/system/health/':
            return _json({
              'gateway': {'status': 'UP', 'port': 8000},
              'overall_status': 'UP',
              'services': [],
            });
          case '/api/dashboard/summary/':
            return _json(_summary());
          case '/api/properties/':
            return _json([
              {'id': 1, 'code': 'NT-01', 'name': 'Nhà trọ Gateway', 'status': 'ACTIVE', 'total_rooms_count': 5},
            ]);
          case '/api/billing/invoices/':
            return _json([
              {
                'id': 40,
                'invoice_code': 'HDN-REAL-01',
                'room_id': 10,
                'tenant_id': 20,
                'total_amount': 4500000,
                'due_date': '2026-11-25',
                'status': 'UNPAID',
              },
            ]);
          default:
            return _json([]);
        }
      });
}

void main() {
  late _Gateway gw;
  late AppDataRepository repo;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    ApiClient.resetForTest();
    gw = _Gateway();
    ApiClient.httpClient = gw.client;
    await ApiClient.saveSession(access: 'access', refresh: 'refresh');
    repo = AppDataRepository();
  });

  tearDown(() {
    ApiClient.httpClient = http.Client();
    ApiClient.resetForTest();
  });

  Future<void> pumpDashboard(WidgetTester tester, {bool settle = true}) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(NhaTroManagerApp(authProvider: _LandlordAuth(), repository: repo));
    if (settle) await tester.pumpAndSettle();
    expect(find.byType(DashboardPage), findsOneWidget);
  }

  /// Giá trị hiển thị của thẻ KPI có tiêu đề [title].
  String kpi(WidgetTester tester, String title) {
    final card = find.ancestor(of: find.text(title), matching: find.byWidgetPredicate((w) => w.runtimeType.toString() == 'StatCard'));
    final texts = tester.widgetList<Text>(find.descendant(of: card.first, matching: find.byType(Text)));
    final values = texts.map((t) => t.data).whereType<String>().toList();
    // Thứ tự trong StatCard: tiêu đề, giá trị, phụ đề.
    return values[values.indexOf(title) + 1];
  }

  Finder retryIn(Key key) => find.descendant(of: find.byKey(key), matching: find.text('Thử lại'));

  testWidgets('1. API thành công: hiển thị đúng số liệu thật, biểu đồ tỷ lệ phòng và hóa đơn', (tester) async {
    await pumpDashboard(tester);

    expect(kpi(tester, 'Tòa nhà đang vận hành'), '2');
    expect(kpi(tester, 'Tổng số phòng'), '5');
    expect(kpi(tester, 'Phòng đang thuê'), '3');
    expect(kpi(tester, 'Phòng còn trống'), '1');
    expect(kpi(tester, 'Hợp đồng hiệu lực'), '3');
    expect(kpi(tester, 'Hóa đơn cần thu'), '2');
    expect(find.textContaining('Tỷ lệ lấp đầy 60%'), findsOneWidget);
    expect(find.byType(RoomRatioChart), findsOneWidget);
    expect(find.text('HDN-REAL-01'), findsOneWidget);
    expect(find.text('Nhà trọ Gateway'), findsOneWidget);
    expect(find.byKey(const Key('dashboard_summary_error')), findsNothing);
    expect(find.byKey(const Key('dashboard_summary_loading')), findsNothing);
    expect(find.text('Chưa có hóa đơn nào.'), findsNothing);
  });

  testWidgets('2. Dashboard Summary đang tải: có chỉ báo tải, KPI "…", không vẽ biểu đồ 0/0/0', (tester) async {
    gw.holdAll = Completer<void>();
    await pumpDashboard(tester, settle: false);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(repo.sectionState(DataSection.dashboard).isLoading, isTrue);
    expect(find.byKey(const Key('dashboard_summary_loading')), findsOneWidget);
    expect(find.byKey(const Key('room_ratio_loading')), findsOneWidget);
    expect(find.byType(RoomRatioChart), findsNothing);
    expect(kpi(tester, 'Tổng số phòng'), '…');
    expect(kpi(tester, 'Doanh thu dự kiến / tháng'), '…');
    expect(find.text('Chưa có hóa đơn nào.'), findsNothing, reason: 'đang tải không phải là rỗng');

    gw.holdAll!.complete();
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('dashboard_summary_loading')), findsNothing);
    expect(kpi(tester, 'Tổng số phòng'), '5');
  });

  testWidgets('3. Dashboard Summary lỗi: báo lỗi + Thử lại, không đổi thành 0; thử lại thì phục hồi',
      (tester) async {
    gw.overrides['/api/dashboard/summary/'] = () => _json({'error': 'Dashboard tạm thời lỗi.'}, 500);
    await pumpDashboard(tester);

    expect(repo.sectionState(DataSection.dashboard).isError, isTrue);
    expect(find.byKey(const Key('dashboard_summary_error')), findsOneWidget);
    expect(find.textContaining('Không lấy được số liệu tổng quan: Dashboard tạm thời lỗi.'), findsOneWidget);
    expect(kpi(tester, 'Tổng số phòng'), '—');
    expect(kpi(tester, 'Doanh thu dự kiến / tháng'), '—');
    expect(kpi(tester, 'Tổng tiền chưa thanh toán'), '—');
    expect(find.text('0 đ'), findsNothing);
    expect(find.byType(RoomRatioChart), findsNothing);
    expect(find.byKey(const Key('room_ratio_error')), findsOneWidget);

    gw.overrides.remove('/api/dashboard/summary/');
    final before = gw.healthCalls;
    await tester.ensureVisible(retryIn(const Key('dashboard_summary_error')));
    await tester.tap(retryIn(const Key('dashboard_summary_error')));
    await tester.pumpAndSettle();

    expect(gw.healthCalls, before + 1, reason: 'Thử lại gọi đúng syncWithBackend');
    expect(find.byKey(const Key('dashboard_summary_error')), findsNothing);
    expect(kpi(tester, 'Tổng số phòng'), '5');
    expect(find.byType(RoomRatioChart), findsOneWidget);
  });

  testWidgets('3b. Summary lỗi ở lần tải sau: giữ số liệu thật trước đó và báo đang hiển thị dữ liệu cũ',
      (tester) async {
    await pumpDashboard(tester);
    gw.overrides['/api/dashboard/summary/'] = () => _json({'error': 'Timeout'}, 504);
    await repo.syncWithBackend();
    await tester.pumpAndSettle();

    expect(kpi(tester, 'Tổng số phòng'), '5');
    expect(find.textContaining('Đang hiển thị số liệu của lần cập nhật trước'), findsOneWidget);
  });

  testWidgets('4. Dashboard Summary Forbidden (403): báo không có quyền, không phải lỗi kết nối', (tester) async {
    gw.overrides['/api/dashboard/summary/'] = () => _json({'detail': 'Bạn không có quyền.'}, 403);
    await pumpDashboard(tester);

    expect(repo.sectionState(DataSection.dashboard).isForbidden, isTrue);
    expect(find.byKey(const Key('dashboard_summary_forbidden')), findsOneWidget);
    expect(find.byKey(const Key('dashboard_summary_error')), findsNothing);
    expect(find.byKey(const Key('room_ratio_forbidden')), findsOneWidget);
    expect(find.byType(RoomRatioChart), findsNothing);
    expect(kpi(tester, 'Tổng số phòng'), '—');
  });

  testWidgets('5–6. Doanh thu dự kiến và tổng tiền chưa thanh toán lấy đúng từ backend, định dạng VND',
      (tester) async {
    gw.overrides['/api/dashboard/summary/'] = () => _json(_summary(override: {
          'estimated_monthly_revenue': 12345000.0,
          'unpaid_amount': '7250000.00',
        }));
    await pumpDashboard(tester);

    expect(kpi(tester, 'Doanh thu dự kiến / tháng'), '12.345.000 đ');
    expect(kpi(tester, 'Tổng tiền chưa thanh toán'), '7.250.000 đ');
    expect(repo.dashboardSummary?.estimatedMonthlyRevenue, 12345000.0);
    expect(repo.dashboardSummary?.unpaidAmount, 7250000.0);
  });

  testWidgets('5b. Thiếu doanh thu (Property Service DOWN) -> "—", không hiển thị 0 đ', (tester) async {
    gw.overrides['/api/dashboard/summary/'] = () => _json(_summary(
          override: {for (final f in _propertyFields) f: null},
          errors: [
            {'source': 'property', 'service': 'Property Service', 'status': 'DOWN'},
          ],
        ));
    await pumpDashboard(tester);

    expect(kpi(tester, 'Doanh thu dự kiến / tháng'), '—');
    expect(kpi(tester, 'Tổng tiền chưa thanh toán'), '3.500.000 đ', reason: 'Billing vẫn hoạt động');
    expect(find.text('0 đ'), findsNothing);
  });

  testWidgets('7. Property Service lỗi: KHÔNG vẽ biểu đồ 0/0/0 giả, báo lỗi + Thử lại', (tester) async {
    gw.overrides['/api/dashboard/summary/'] = () => _json(_summary(
          override: {for (final f in _propertyFields) f: null},
          errors: [
            {'source': 'property', 'service': 'Property Service', 'status': 'DOWN'},
          ],
        ));
    await pumpDashboard(tester);

    expect(find.byType(RoomRatioChart), findsNothing);
    expect(find.byKey(const Key('room_ratio_error')), findsOneWidget);
    expect(find.textContaining('Property Service không trả số liệu phòng'), findsOneWidget);
    expect(find.textContaining('Thiếu số liệu do service không phản hồi: Property Service'), findsOneWidget);
    expect(kpi(tester, 'Tổng số phòng'), '—');
    expect(kpi(tester, 'Phòng đang thuê'), '—');
    expect(kpi(tester, 'Hợp đồng hiệu lực'), '3', reason: 'Contract Service vẫn hoạt động');
  });

  testWidgets('8. Số liệu thật sự bằng 0 vẫn hiển thị 0 và vẽ biểu đồ', (tester) async {
    gw.overrides['/api/dashboard/summary/'] = () => _json(_summary(override: {
          'total_properties': 0,
          'total_rooms': 0,
          'occupied_rooms': 0,
          'available_rooms': 0,
          'maintenance_rooms': 0,
          'occupancy_rate_percent': 0.0,
          'estimated_monthly_revenue': 0,
          'unpaid_invoices': 0,
          'unpaid_amount': '0',
        }));
    await pumpDashboard(tester);

    expect(kpi(tester, 'Tòa nhà đang vận hành'), '0');
    expect(kpi(tester, 'Tổng số phòng'), '0');
    expect(kpi(tester, 'Phòng đang thuê'), '0');
    expect(kpi(tester, 'Doanh thu dự kiến / tháng'), '0 đ');
    expect(kpi(tester, 'Tổng tiền chưa thanh toán'), '0 đ');
    expect(find.byType(RoomRatioChart), findsOneWidget);
    expect(find.byKey(const Key('room_ratio_error')), findsNothing);
  });

  testWidgets('9. Billing Service lỗi: không hiển thị "Chưa có hóa đơn nào", báo lỗi + Thử lại', (tester) async {
    gw.overrides['/api/billing/invoices/'] =
        () => _json({'error': 'Billing & Notification Service hiện không hoạt động (port 8005).'}, 503);
    await pumpDashboard(tester);

    expect(repo.sectionState(DataSection.invoices).isError, isTrue);
    expect(find.text('Chưa có hóa đơn nào.'), findsNothing);
    expect(find.textContaining('Không tải được danh sách hóa đơn: Billing & Notification Service'),
        findsOneWidget);
    expect(retryIn(const Key('dashboard_invoices_status')), findsOneWidget);
  });

  testWidgets('9b. Billing lỗi sau khi đã có hóa đơn: vẫn hiển thị hóa đơn cũ kèm cảnh báo', (tester) async {
    await pumpDashboard(tester);
    gw.overrides['/api/billing/invoices/'] = () => _json({'error': 'Billing DOWN'}, 503);
    await repo.syncWithBackend();
    await tester.pumpAndSettle();

    expect(find.text('HDN-REAL-01'), findsOneWidget);
    expect(find.textContaining('Đang hiển thị dữ liệu của lần tải trước'), findsOneWidget);
  });

  testWidgets('9c. Billing 403: báo không có quyền, không phải lỗi, không phải rỗng', (tester) async {
    gw.overrides['/api/billing/invoices/'] = () => _json({'detail': 'Không có quyền.'}, 403);
    await pumpDashboard(tester);

    expect(find.text('Tài khoản của bạn không có quyền xem danh sách hóa đơn.'), findsOneWidget);
    expect(find.text('Chưa có hóa đơn nào.'), findsNothing);
    expect(retryIn(const Key('dashboard_invoices_status')), findsNothing);
  });

  testWidgets('10. Billing thật sự không có hóa đơn: hiển thị trạng thái rỗng', (tester) async {
    gw.overrides['/api/billing/invoices/'] = () => _json([]);
    await pumpDashboard(tester);

    expect(repo.sectionState(DataSection.invoices).isLoaded, isTrue);
    expect(find.text('Chưa có hóa đơn nào.'), findsOneWidget);
    expect(find.textContaining('Không tải được danh sách hóa đơn'), findsNothing);
  });

  testWidgets('Property list lỗi: không hiển thị "Chưa có tòa nhà nào"', (tester) async {
    gw.overrides['/api/properties/'] = () => _json({'detail': 'boom'}, 500);
    await pumpDashboard(tester);

    expect(find.text('Chưa có tòa nhà nào.'), findsNothing);
    expect(find.textContaining('Không tải được danh sách tòa nhà'), findsOneWidget);
  });

  testWidgets('11. Biểu đồ doanh thu theo tháng không dùng dữ liệu giả: hiển thị trạng thái rỗng',
      (tester) async {
    await pumpDashboard(tester);

    expect(repo.revenuePoints, isEmpty, reason: 'backend chưa cung cấp chuỗi doanh thu theo tháng');
    expect(find.byType(MonthlyRevenueChart), findsNothing);
    expect(find.byKey(const Key('revenue_chart_empty')), findsOneWidget);
    expect(find.text('Chưa có dữ liệu doanh thu theo tháng'), findsOneWidget);
    // Không có nhãn tháng giả (T1, T2, ...) của biểu đồ mẫu.
    expect(find.textContaining('T1'), findsNothing);
  });
}
