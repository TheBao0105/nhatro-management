import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:nhatro_frontend/core/constants/api_constants.dart';
import 'package:nhatro_frontend/core/constants/soa_services.dart';
import 'package:nhatro_frontend/core/widgets/app_sidebar.dart';
import 'package:nhatro_frontend/features/notification/presentation/settings_page.dart';
import 'package:nhatro_frontend/main.dart';
import 'package:nhatro_frontend/providers/auth_provider.dart';
import 'package:nhatro_frontend/shared/services/api_client.dart';
import 'package:nhatro_frontend/shared/services/app_data_repository.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// AuthProvider giả: không gọi mạng.
class FakeAuthProvider extends AuthProvider {
  AuthStatus _fakeStatus;
  FakeAuthProvider(this._fakeStatus);

  @override
  AuthStatus get status => _fakeStatus;

  @override
  bool get isAuthenticated => _fakeStatus == AuthStatus.authenticated;

  @override
  String get displayName => 'Chủ trọ Test';

  @override
  String get roleDisplay => 'Chủ nhà trọ';

  @override
  String get role => 'LANDLORD';

  @override
  Future<bool> login(String username, String password) async {
    _fakeStatus = AuthStatus.authenticated;
    notifyListeners();
    return true;
  }

  @override
  Future<void> logout() async {
    _fakeStatus = AuthStatus.unauthenticated;
    notifyListeners();
  }
}

/// Repository giả: không đồng bộ qua mạng (dữ liệu rỗng, chưa kết nối Gateway).
class OfflineRepository extends AppDataRepository {
  int syncCalls = 0;

  @override
  Future<void> syncWithBackend() async {
    syncCalls++;
  }
}

void _desktop(WidgetTester tester) {
  tester.view.physicalSize = const Size(1440, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('Chưa đăng nhập -> chuyển tới màn hình đăng nhập', (tester) async {
    _desktop(tester);
    final repo = OfflineRepository();
    await tester.pumpWidget(NhaTroManagerApp(
      authProvider: FakeAuthProvider(AuthStatus.unauthenticated),
      repository: repo,
    ));
    await tester.pumpAndSettle();

    expect(find.text('NHÀ TRỌ MANAGER'), findsOneWidget);
    expect(find.text('Đăng nhập'), findsOneWidget);
    expect(find.text('Tổng quan hệ thống'), findsNothing);
    expect(repo.syncCalls, 0);
  });

  testWidgets('Đăng nhập -> vào Dashboard và đồng bộ dữ liệu qua Gateway', (tester) async {
    _desktop(tester);
    final repo = OfflineRepository();
    final auth = FakeAuthProvider(AuthStatus.unauthenticated);
    await tester.pumpWidget(NhaTroManagerApp(authProvider: auth, repository: repo));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextFormField).first, 'chutro1');
    await tester.enterText(find.byKey(const Key('login_password')), 'secret');
    await tester.tap(find.text('Đăng nhập'));
    await tester.pumpAndSettle();

    expect(find.text('Tổng quan nhà trọ của bạn'), findsOneWidget); // Dashboard theo vai trò LANDLORD
    expect(find.text('Chủ trọ Test'), findsWidgets);
    expect(repo.syncCalls, 1);
    // Chưa kết nối Gateway -> báo chưa có số liệu, không hiển thị dữ liệu mẫu thay thế.
    expect(find.textContaining('chưa kết nối được API Gateway'), findsOneWidget);
    expect(find.textContaining('DỮ LIỆU MẪU'), findsNothing);
  });

  test('Frontend chỉ dùng API Gateway, không trỏ trực tiếp port 8001–8005', () {
    expect(ApiConstants.baseUrl, startsWith(ApiConstants.gatewayUrl));
    for (final s in SoaServices.all) {
      expect(s.gatewayEndpoint, startsWith(ApiConstants.baseUrl));
      expect(s.gatewayEndpoint, isNot(contains(':${s.port}')));
    }
  });

  testWidgets('Đổi mật khẩu che ký tự ở cả ba ô mật khẩu', (tester) async {
    _desktop(tester);
    final auth = FakeAuthProvider(AuthStatus.authenticated);
    addTearDown(auth.dispose);
    await tester.pumpWidget(
      ChangeNotifierProvider<AuthProvider>.value(
        value: auth,
        child: const MaterialApp(
          home: Scaffold(body: SingleChildScrollView(child: SettingsPage())),
        ),
      ),
    );

    await tester.tap(find.text('Đổi mật khẩu'));
    await tester.pumpAndSettle();

    final fields = find.descendant(
      of: find.byType(AlertDialog),
      matching: find.byType(EditableText),
    );
    expect(fields, findsNWidgets(3));
    expect(
      tester.widgetList<EditableText>(fields).map((field) => field.obscureText),
      everyElement(isTrue),
    );
  });

  test('ApiClient tự động refresh JWT khi nhận 401 và gọi lại Gateway', () async {
    int protectedCalls = 0;
    ApiClient.httpClient = MockClient((req) async {
      final path = req.url.path;
      if (path == '/api/auth/refresh/') {
        return http.Response(jsonEncode({'access': 'new-access-token'}), 200);
      }
      if (path == '/api/properties/') {
        protectedCalls++;
        if (protectedCalls == 1) {
          return http.Response(jsonEncode({'detail': 'Token expired'}), 401);
        }
        expect(req.headers['Authorization'], 'Bearer new-access-token');
        return http.Response(jsonEncode([]), 200);
      }
      return http.Response('Not found', 404);
    });
    addTearDown(() => ApiClient.httpClient = http.Client());

    await ApiClient.saveSession(access: 'expired-token', refresh: 'valid-refresh');
    final res = await ApiClient.get(ApiConstants.properties);
    expect(res, isA<List>());
    expect(protectedCalls, 2);
    expect(await ApiClient.getAccessToken(), 'new-access-token');
  });

  test('AppDataRepository đồng bộ đủ 5 service và thực hiện action qua Gateway', () async {
    http.Response jsonRes(Object? body, [int status = 200]) =>
        http.Response.bytes(
          utf8.encode(jsonEncode(body)),
          status,
          headers: const {'content-type': 'application/json; charset=utf-8'},
        );

    final calledEndpoints = <String>[];
    ApiClient.httpClient = MockClient((req) async {
      calledEndpoints.add('${req.method} ${req.url.path}');
      switch (req.url.path) {
        case '/api/system/health/':
          return jsonRes({
            'gateway': {'status': 'UP', 'port': 8000},
            'overall_status': 'UP',
            'services': [
              {'key': 'identity', 'name': 'Identity', 'port': 8001, 'status': 'UP'},
              {'key': 'property', 'name': 'Property', 'port': 8002, 'status': 'UP'},
              {'key': 'tenant', 'name': 'Tenant', 'port': 8003, 'status': 'UP'},
              {'key': 'contract', 'name': 'Contract', 'port': 8004, 'status': 'UP'},
              {'key': 'billing', 'name': 'Billing', 'port': 8005, 'status': 'UP'},
            ],
          });
        case '/api/dashboard/summary/':
          return jsonRes({'total_properties': 1, 'total_rooms': 1});
        case '/api/properties/':
          return jsonRes([
            {
              'id': 1,
              'code': 'NT-01',
              'name': 'Nhà trọ Gateway',
              'address': '10 Lê Lợi',
              'district': 'Quận 1',
              'status': 'ACTIVE',
              'total_rooms_count': 1,
              'occupied_rooms_count': 0,
              'available_rooms_count': 1,
            }
          ]);
        case '/api/rooms/':
          return jsonRes([
            {
              'id': 10,
              'code': 'P-101',
              'property': 1,
              'property_name': 'Nhà trọ Gateway',
              'room_number': 'Phòng 101',
              'floor': 1,
              'area': 25,
              'rent_price': 4000000,
              'max_occupants': 2,
              'current_occupants': 0,
              'status': 'AVAILABLE',
              'is_rentable': true,
            }
          ]);
        case '/api/maintenance/':
          return jsonRes([]);
        case '/api/maintenance-history/':
          return jsonRes([]);
        case '/api/tenants/':
          return jsonRes([
            {
              'id': 20,
              'room_id': 10,
              'full_name': 'Nguyễn Minh A',
              'phone_number': '0901234567',
              'email': 'a@test.com',
              'status': 'ACTIVE',
            }
          ]);
        case '/api/contracts/':
          return jsonRes([
            {
              'id': 30,
              'contract_number': 'HD-001',
              'room_id': 10,
              'tenant_id': 20,
              'start_date': '2026-11-01',
              'end_date': '2027-11-01',
              'rental_price': 4000000,
              'deposit_amount': 8000000,
              'status': 'DRAFT',
            }
          ]);
        case '/api/billing/invoices/':
          return jsonRes([
            {
              'id': 40,
              'invoice_code': 'HDN-001',
              'room_id': 10,
              'tenant_id': 20,
              'billing_month': 11,
              'billing_year': 2026,
              'total_amount': 4500000,
              'due_date': '2026-11-25',
              'status': 'UNPAID',
            }
          ]);
        case '/api/notifications/':
          return jsonRes([
            {
              'id': 50,
              'title': 'Hóa đơn mới',
              'content': 'Có hóa đơn tháng 11',
              'category': 'INVOICE',
              'is_read': false,
              'created_at': '2026-11-15',
            }
          ]);
        case '/api/contracts/30/activate/':
        case '/api/billing/invoices/40/pay/':
        case '/api/notifications/50/read/':
          return jsonRes({'ok': true});
        default:
          return jsonRes({});
      }
    });
    addTearDown(() => ApiClient.httpClient = http.Client());

    await ApiClient.saveSession(access: 'token');
    final repo = AppDataRepository();
    await repo.syncWithBackend();

    expect(repo.isBackendConnected, isTrue);
    expect(repo.properties.single.name, 'Nhà trọ Gateway');
    expect(repo.rooms.single.name, 'Phòng 101');
    expect(repo.tenants.single.fullName, 'Nguyễn Minh A');
    expect(repo.contracts.single.code, 'HD-001');
    expect(repo.invoices.single.code, 'HDN-001');
    expect(repo.notifications.single.title, 'Hóa đơn mới');

    expect(await repo.activateContract(30), isNull);
    expect(await repo.payInvoice(40), isNull);
    expect(await repo.markNotificationRead(50), isNull);
    expect(calledEndpoints, contains('POST /api/contracts/30/activate/'));
    expect(calledEndpoints, contains('POST /api/billing/invoices/40/pay/'));
    expect(calledEndpoints, contains('POST /api/notifications/50/read/'));
  });

  testWidgets('Điều hướng đầy đủ tất cả các trang SOA trên desktop không lỗi', (tester) async {
    _desktop(tester);
    final repo = OfflineRepository();
    await tester.pumpWidget(NhaTroManagerApp(
      authProvider: FakeAuthProvider(AuthStatus.authenticated),
      repository: repo,
    ));
    await tester.pumpAndSettle();

    // Menu LANDLORD (Giai đoạn 3): Bảo trì đã ẩn; tài khoản / quản trị hệ thống chỉ có ở ADMIN.
    final navLabels = [
      ('Nhà trọ', 'Quản lý Tòa nhà'),
      ('Phòng', 'Quản lý phòng'),
      ('Khách thuê', 'Quản lý người thuê'),
      ('Hợp đồng', 'Quản lý hợp đồng'),
      ('Hóa đơn', 'Hóa đơn'),
      ('Thông báo', 'Thông báo'),
      ('Cài đặt', 'Cài đặt'),
      ('Dashboard', 'Tổng quan nhà trọ của bạn'),
    ];

    Finder sidebar(String text) => find.descendant(of: find.byType(AppSidebar), matching: find.text(text));
    for (final (sidebarText, pageTitle) in navLabels) {
      await tester.tap(sidebar(sidebarText).first);
      await tester.pumpAndSettle();
      expect(find.text(pageTitle), findsWidgets);
    }

    // Kiểm tra điều hướng sang Thêm phòng mới (/rooms/create) và Chi tiết phòng (/rooms/:id)
    await tester.tap(sidebar('Phòng').first);
    await tester.pumpAndSettle();
    // Danh sách rỗng nên "+ Thêm phòng" có ở cả header và EmptyState: bấm nút ở header.
    await tester.tap(find.text('+ Thêm phòng').first);
    await tester.pumpAndSettle();
    expect(find.text('Thêm phòng mới'), findsOneWidget);

    await tester.tap(find.text('Hủy').first);
    await tester.pumpAndSettle();
    expect(find.text('Quản lý phòng'), findsWidgets);
  });
}
