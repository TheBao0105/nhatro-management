// Chặng 5 – Bước 4 (E5.3): trang Nhà trọ / Phòng / Thêm phòng / Chi tiết phòng phản ánh đúng
// trạng thái dữ liệu backend và chỉ báo thành công khi backend xác nhận.
// Dùng AppDataRepository THẬT + Gateway giả có trạng thái phía server (MockClient).
import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:nhatro_frontend/core/widgets/app_search_bar.dart';
import 'package:nhatro_frontend/core/widgets/app_text_field.dart';
import 'package:nhatro_frontend/core/widgets/pagination_widget.dart';
import 'package:nhatro_frontend/features/property/presentation/property_page.dart';
import 'package:nhatro_frontend/features/room/presentation/room_create_page.dart';
import 'package:nhatro_frontend/features/room/presentation/room_page.dart';
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

/// `full_address` chỉ đọc, ghép giống Property.full_address của backend: address, ward, district, city.
String _fullAddress(Map<String, dynamic> p) =>
    [p['address'], p['ward'], p['district'], p['city']].where((v) => '${v ?? ''}'.isNotEmpty).join(', ');

Map<String, dynamic> _property(int id, String name, {String status = 'ACTIVE', int rooms = 0}) {
  final p = <String, dynamic>{
      'id': id,
      'code': 'NT-0$id',
      'name': name,
      'address': '$id Đường Số $id',
      'district': 'Quận $id',
      'ward': 'Phường 1',
      'city': 'TP. Hồ Chí Minh',
      'status': status,
      'total_rooms_count': rooms,
      'occupied_rooms_count': 0,
      'available_rooms_count': rooms,
      'maintenance_rooms_count': 0,
    };
  p['full_address'] = _fullAddress(p);
  return p;
}

Map<String, dynamic> _room(int id, String number, int propertyId, String propertyName,
        {String status = 'AVAILABLE', double price = 3000000}) =>
    {
      'id': id,
      'code': 'P-$id',
      'property': propertyId,
      'property_name': propertyName,
      'room_number': number,
      'floor': 1,
      'rent_price': price,
      'area': 20,
      'max_occupants': 2,
      'current_occupants': 0,
      'status': status,
    };

/// Gateway giả có dữ liệu phía server: thao tác ghi đổi dữ liệu, lần đồng bộ sau đọc lại đúng dữ liệu đó.
class _Server {
  final properties = <Map<String, dynamic>>[
    _property(1, 'Nhà A', rooms: 2),
    _property(2, 'Nhà B', rooms: 1),
  ];
  final rooms = <Map<String, dynamic>>[
    _room(10, 'Phòng A1', 1, 'Nhà A'),
    _room(11, 'Phòng A2', 1, 'Nhà A', status: 'OCCUPIED', price: 4500000),
    _room(20, 'Phòng B1', 2, 'Nhà B'),
  ];
  final contracts = <Map<String, dynamic>>[];
  final requests = <http.Request>[];
  final Map<String, FutureOr<http.Response> Function(http.Request req)> overrides = {};
  Completer<void>? hold;
  int nextId = 100;

  List<http.Request> writes(String method, String path) =>
      requests.where((r) => r.method == method && r.url.path == path).toList();

  MockClient get client => MockClient((req) async {
        if (hold != null) await hold!.future;
        requests.add(req);
        final path = req.url.path;
        final o = overrides['${req.method} $path'];
        if (o != null) return o(req);
        Map<String, dynamic> body() => jsonDecode(req.body) as Map<String, dynamic>;

        if (path == '/api/system/health/') {
          return _json({'gateway': {'status': 'UP', 'port': 8000}, 'overall_status': 'UP', 'services': []});
        }
        if (path == '/api/dashboard/summary/') return _json({'complete': true, 'errors': []});

        if (path == '/api/properties/') {
          if (req.method == 'POST') {
            final b = body();
            final p = _property(nextId++, '${b['name']}');
            properties.add(p);
            return _json(p, 201);
          }
          return _json(properties);
        }
        final propMatch = RegExp(r'^/api/properties/(\d+)/$').firstMatch(path);
        if (propMatch != null && req.method == 'DELETE') {
          properties.removeWhere((p) => p['id'] == int.parse(propMatch.group(1)!));
          return _json({'message': 'ok'});
        }
        if (propMatch != null && req.method == 'PATCH') {
          final p = properties.firstWhere((p) => p['id'] == int.parse(propMatch.group(1)!));
          // Như DRF: chỉ ghi các trường ghi được; `full_address` là read-only và được ghép lại.
          const writable = ['code', 'name', 'address', 'ward', 'district', 'city', 'status', 'description'];
          body().forEach((k, v) {
            if (writable.contains(k)) p[k] = v;
          });
          p['full_address'] = _fullAddress(p);
          return _json(p);
        }

        if (path == '/api/rooms/') {
          if (req.method == 'POST') {
            final b = body();
            final pid = b['property'] as int;
            final prop = properties.firstWhere((p) => p['id'] == pid);
            final r = _room(nextId++, '${b['room_number']}', pid, '${prop['name']}');
            rooms.add(r);
            return _json(r, 201);
          }
          return _json(rooms);
        }
        final roomMatch = RegExp(r'^/api/rooms/(\d+)/$').firstMatch(path);
        if (roomMatch != null && req.method == 'DELETE') {
          rooms.removeWhere((r) => r['id'] == int.parse(roomMatch.group(1)!));
          return _json({'message': 'ok'});
        }
        final statusMatch = RegExp(r'^/api/rooms/(\d+)/status/$').firstMatch(path);
        if (statusMatch != null) {
          final r = rooms.firstWhere((r) => r['id'] == int.parse(statusMatch.group(1)!));
          r['status'] = body()['status'];
          return _json(r);
        }
        if (path == '/api/contracts/') return _json(contracts);
        return _json([]);
      });
}

void main() {
  late _Server server;
  late AppDataRepository repo;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    ApiClient.resetForTest();
    server = _Server();
    ApiClient.httpClient = server.client;
    await ApiClient.saveSession(access: 'access', refresh: 'refresh');
    repo = AppDataRepository();
  });

  tearDown(() {
    ApiClient.httpClient = http.Client();
    ApiClient.resetForTest();
  });

  Future<void> go(WidgetTester tester, String location, {bool settle = true}) async {
    GoRouter.of(tester.element(find.byType(Scaffold).first)).go(location);
    if (settle) {
      await tester.pumpAndSettle();
    } else {
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
    }
  }

  Future<void> openApp(WidgetTester tester, String location, {bool settle = true}) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(NhaTroManagerApp(authProvider: _LandlordAuth(), repository: repo));
    if (settle) {
      await tester.pumpAndSettle();
    } else {
      await tester.pump();
    }
    await go(tester, location, settle: settle);
  }

  Finder field(String label) => find.descendant(
        of: find.ancestor(of: find.text(label), matching: find.byType(AppTextField)).first,
        matching: find.byType(TextFormField),
      );

  Future<void> tapVisible(WidgetTester tester, Finder f) async {
    await tester.ensureVisible(f);
    await tester.pumpAndSettle();
    await tester.tap(f);
    await tester.pumpAndSettle();
  }

  Finder key(String k) => find.byKey(Key(k));

  // ================================================================ PROPERTY
  group('Nhà trọ', () {
    testWidgets('Hiển thị đúng và đủ danh sách backend trả về (phạm vi do backend lọc)', (tester) async {
      await openApp(tester, '/property');

      expect(find.byType(PropertyPage), findsOneWidget);
      expect(find.text('Nhà A'), findsOneWidget);
      expect(find.text('Nhà B'), findsOneWidget);
      expect(find.text('Hiển thị 1–2 trong tổng số 2 bản ghi'), findsOneWidget);
      expect(key('property_list_error'), findsNothing);
      expect(find.text('3 phòng quản lý'), findsOneWidget, reason: 'đếm từ danh sách phòng thật');
    });

    testWidgets('Property Service lỗi (Gateway vẫn chạy): báo lỗi + Thử lại, không phải "chưa có tòa nhà"',
        (tester) async {
      server.overrides['GET /api/properties/'] = (_) => _json({'error': 'Property Service DOWN'}, 503);
      await openApp(tester, '/property');

      expect(repo.isBackendConnected, isTrue);
      expect(key('property_list_error'), findsOneWidget);
      expect(find.textContaining('Không tải được danh sách tòa nhà: Property Service DOWN'), findsOneWidget);
      expect(key('property_list_empty'), findsNothing);
      expect(find.text('Chưa có tòa nhà nào'), findsNothing);
      expect(find.text('— tòa nhà hoạt động'), findsOneWidget, reason: 'không hiện 0/0 như số thật');

      server.overrides.remove('GET /api/properties/');
      await tapVisible(tester, find.descendant(of: key('property_list_error'), matching: find.text('Thử lại')));

      expect(key('property_list_error'), findsNothing);
      expect(find.text('Nhà A'), findsOneWidget);
    });

    testWidgets('403: báo không có quyền, không phải lỗi, không phải rỗng', (tester) async {
      server.overrides['GET /api/properties/'] = (_) => _json({'detail': 'Không có quyền.'}, 403);
      await openApp(tester, '/property');

      expect(key('property_list_forbidden'), findsOneWidget);
      expect(key('property_list_error'), findsNothing);
      expect(key('property_list_empty'), findsNothing);
    });

    testWidgets('Backend thật sự không có tòa nhà: hiển thị trạng thái rỗng', (tester) async {
      server.properties.clear();
      server.rooms.clear();
      await openApp(tester, '/property');

      expect(key('property_list_empty'), findsOneWidget);
      expect(find.text('Chưa có tòa nhà nào'), findsOneWidget);
      expect(find.text('0/0 tòa nhà hoạt động'), findsOneWidget, reason: 'số 0 thật vẫn là 0');
    });

    testWidgets('Đang tải: có chỉ báo tải, chưa kết luận rỗng', (tester) async {
      server.hold = Completer<void>();
      await openApp(tester, '/property', settle: false);

      expect(key('property_list_loading'), findsOneWidget);
      expect(key('property_list_empty'), findsNothing);

      server.hold!.complete();
      await tester.pumpAndSettle();
      expect(find.text('Nhà A'), findsOneWidget);
    });

    testWidgets('Lỗi ở lần tải sau: giữ dữ liệu cũ kèm cảnh báo + Thử lại', (tester) async {
      await openApp(tester, '/property');
      server.overrides['GET /api/properties/'] = (_) => _json({'error': 'Timeout'}, 504);
      await repo.syncWithBackend();
      await tester.pumpAndSettle();

      expect(find.text('Nhà A'), findsOneWidget);
      expect(key('property_list_stale'), findsOneWidget);
      expect(find.textContaining('Đang hiển thị dữ liệu của lần tải trước'), findsOneWidget);
    });

    testWidgets('Room Service lỗi: thẻ tổng quan hiện "—", không hiện 0 phòng giả', (tester) async {
      server.overrides['GET /api/rooms/'] = (_) => _json({'error': 'Room DOWN'}, 500);
      await openApp(tester, '/property');

      expect(find.text('— phòng quản lý'), findsOneWidget);
      expect(find.text('0 phòng quản lý'), findsNothing);
      expect(find.text('Nhà A'), findsOneWidget, reason: 'danh sách tòa nhà vẫn tải được');
    });

    testWidgets('Thêm tòa nhà: gửi đúng payload, chỉ báo thành công sau khi backend xác nhận, danh sách cập nhật',
        (tester) async {
      await openApp(tester, '/property');
      await tapVisible(tester, find.text('+ Thêm tòa nhà mới').first);

      expect(find.text('Tổng số phòng'), findsNothing, reason: 'backend tự tính, không có ô nhập không được lưu');
      await tester.enterText(field('Tên nhà trọ'), 'Nhà C');
      await tester.enterText(field('Địa chỉ chi tiết'), '9 Lê Lợi');
      await tester.enterText(field('Quận / Huyện / Khu vực'), 'Quận 9');
      await tapVisible(tester, find.text('Thêm nhà trọ'));

      final posts = server.writes('POST', '/api/properties/');
      expect(posts, hasLength(1));
      final payload = jsonDecode(posts.single.body) as Map<String, dynamic>;
      expect(payload['name'], 'Nhà C');
      expect(payload['address'], '9 Lê Lợi');
      expect(payload['district'], 'Quận 9');
      expect(payload.containsKey('code'), isFalse, reason: 'để trống -> backend tự sinh mã');
      expect(payload.containsKey('id'), isFalse);

      expect(find.text('Đã thêm nhà trọ "Nhà C"'), findsOneWidget);
      expect(find.text('Thêm nhà trọ mới'), findsNothing, reason: 'hộp thoại đã đóng');
      expect(find.text('Nhà C'), findsOneWidget, reason: 'dữ liệu đọc lại từ backend');
    });

    testWidgets('Thêm tòa nhà bị backend từ chối: báo lỗi, không báo thành công, danh sách không đổi',
        (tester) async {
      server.overrides['POST /api/properties/'] = (_) => _json({'code': ['Mã nhà trọ đã tồn tại.']}, 400);
      await openApp(tester, '/property');
      await tapVisible(tester, find.text('+ Thêm tòa nhà mới').first);
      await tester.enterText(field('Tên nhà trọ'), 'Nhà C');
      await tester.enterText(field('Địa chỉ chi tiết'), '9 Lê Lợi');
      await tester.enterText(field('Quận / Huyện / Khu vực'), 'Quận 9');
      await tapVisible(tester, find.text('Thêm nhà trọ'));

      expect(find.textContaining('Đã thêm nhà trọ'), findsNothing);
      expect(find.textContaining('Mã nhà trọ đã tồn tại'), findsOneWidget);
      expect(find.text('Thêm nhà trọ mới'), findsOneWidget, reason: 'hộp thoại vẫn mở để sửa');
      expect(repo.properties, hasLength(2));
    });

    testWidgets('Xóa tòa nhà ở trang cuối: danh sách cập nhật, không kẹt ở trang trống', (tester) async {
      server.properties
        ..clear()
        ..addAll([for (var i = 1; i <= 7; i++) _property(i, 'Tòa $i')]);
      server.rooms.clear();
      await openApp(tester, '/property');

      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')));
      expect(find.text('Tòa 7'), findsOneWidget);
      expect(find.text('Tòa 1'), findsNothing);

      await tapVisible(tester, find.byTooltip('Xóa'));
      await tapVisible(tester, find.text('Xác nhận xóa'));

      expect(server.writes('DELETE', '/api/properties/7/'), hasLength(1));
      expect(find.text('Đã xóa nhà trọ "Tòa 7"'), findsOneWidget);
      expect(find.text('Tòa 7'), findsNothing);
      expect(find.text('Tòa 1'), findsOneWidget, reason: 'quay về trang cuối còn dữ liệu');
      expect(find.text('Hiển thị 1–6 trong tổng số 6 bản ghi'), findsOneWidget);
    });

    testWidgets('Chi tiết tòa nhà khi Room Service lỗi: không nói "chưa có phòng nào"', (tester) async {
      server.overrides['GET /api/rooms/'] = (_) => _json({'error': 'Room DOWN'}, 500);
      await openApp(tester, '/property');
      await tapVisible(tester, find.byTooltip('Xem chi tiết').first);

      expect(find.text('Chưa có phòng nào được gán.'), findsNothing);
      expect(find.textContaining('Không tải được danh sách phòng'), findsOneWidget);
    });

    testWidgets(
        '[QLNT-302] Phân trang danh sách nhà trọ (>6 phần tử): hiển thị 6 phần tử trang đầu, chuyển trang Sau/Trước, chặn biên trang 0 và vượt trang cuối, xử lý danh sách 1 trang',
        (tester) async {
      // Trường hợp 1 trang (2 phần tử mặc định): chỉ có trang 1, nút Trước và Sau đều bị vô hiệu hóa.
      await openApp(tester, '/property');
      expect(find.text('Hiển thị 1–2 trong tổng số 2 bản ghi'), findsOneWidget);
      expect(find.descendant(of: find.byType(PaginationWidget), matching: find.text('1')), findsOneWidget);
      expect(find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')), findsNothing);
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Trước')));
      expect(find.text('Hiển thị 1–2 trong tổng số 2 bản ghi'), findsOneWidget);
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Sau')));
      expect(find.text('Hiển thị 1–2 trong tổng số 2 bản ghi'), findsOneWidget);

      // Trường hợp > 6 phần tử (8 nhà trọ: trang 1 có 6 phần tử, trang 2 có 2 phần tử).
      server.properties
        ..clear()
        ..addAll([for (var i = 1; i <= 8; i++) _property(i, 'Tòa $i')]);
      await repo.syncWithBackend();
      await tester.pumpAndSettle();

      // Trang đầu (trang 1): hiển thị đúng 6 phần tử đầu (Tòa 1..Tòa 6), ẩn Tòa 7..Tòa 8.
      expect(find.text('Hiển thị 1–6 trong tổng số 8 bản ghi'), findsOneWidget);
      for (var i = 1; i <= 6; i++) {
        expect(find.text('Tòa $i'), findsOneWidget);
      }
      expect(find.text('Tòa 7'), findsNothing);
      expect(find.text('Tòa 8'), findsNothing);

      // Ở trang 1, bấm "Trước" không được chuyển về trang 0.
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Trước')));
      expect(find.text('Hiển thị 1–6 trong tổng số 8 bản ghi'), findsOneWidget);
      expect(find.text('Tòa 1'), findsOneWidget);

      // Chuyển sang trang tiếp theo bằng nút "Sau": hiển thị đúng 2 phần tử cuối (Tòa 7, Tòa 8), ẩn toàn bộ Tòa 1..6.
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Sau')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);
      expect(find.text('Tòa 7'), findsOneWidget);
      expect(find.text('Tòa 8'), findsOneWidget);
      for (var i = 1; i <= 6; i++) {
        expect(find.text('Tòa $i'), findsNothing);
      }

      // Ở trang cuối (trang 2), bấm "Sau" không được vượt quá trang cuối.
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Sau')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);
      expect(find.text('Tòa 7'), findsOneWidget);

      // Chuyển về trang trước bằng nút "Trước": quay lại trang 1 (đủ Tòa 1..Tòa 6, ẩn Tòa 7..Tòa 8).
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Trước')));
      expect(find.text('Hiển thị 1–6 trong tổng số 8 bản ghi'), findsOneWidget);
      for (var i = 1; i <= 6; i++) {
        expect(find.text('Tòa $i'), findsOneWidget);
      }
      expect(find.text('Tòa 7'), findsNothing);
      expect(find.text('Tòa 8'), findsNothing);
    });

    testWidgets(
        '[QLNT-302] Khi tìm kiếm hoặc lọc trạng thái nhà trọ ở trang 2: tự động quay về trang 1 và tính lại phân trang',
        (tester) async {
      server.properties
        ..clear()
        ..addAll([
          for (var i = 1; i <= 7; i++) _property(i, 'Tòa $i', status: 'ACTIVE'),
          _property(8, 'Tòa Tạm Ngưng 8', status: 'INACTIVE'),
        ]);
      await openApp(tester, '/property');

      // Chuyển sang trang 2 trước khi lọc/tìm kiếm.
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);

      // Tìm kiếm theo từ khóa: phân trang tính toán lại về trang 1 với 1 kết quả.
      final propSearch = find.descendant(of: find.byType(AppSearchBar), matching: find.byType(TextField));
      await tester.enterText(propSearch, 'NT-02');
      await tester.pumpAndSettle();
      expect(find.text('Hiển thị 1–1 trong tổng số 1 bản ghi'), findsOneWidget);
      expect(find.text('Tòa 2'), findsOneWidget);
      expect(find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')), findsNothing);

      // Đặt lại rồi chuyển sang trang 2 và lọc theo trạng thái "Tạm ngưng".
      await tapVisible(tester, find.text('Đặt lại'));
      expect(find.text('Hiển thị 1–6 trong tổng số 8 bản ghi'), findsOneWidget);
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);

      await tapVisible(tester, find.text('Tất cả trạng thái'));
      await tapVisible(tester, find.text('Tạm ngưng').last);
      expect(find.text('Hiển thị 1–1 trong tổng số 1 bản ghi'), findsOneWidget);
      expect(find.text('Tòa Tạm Ngưng 8'), findsOneWidget);
    });
  });

  // ==================================================================== ROOM
  group('Phòng', () {
    testWidgets('Room Service lỗi: báo lỗi + Thử lại, không phải rỗng / không khớp bộ lọc', (tester) async {
      server.overrides['GET /api/rooms/'] = (_) => _json({'error': 'Room DOWN'}, 503);
      await openApp(tester, '/rooms');

      expect(find.byType(RoomPage), findsOneWidget);
      expect(key('room_list_error'), findsOneWidget);
      expect(key('room_list_empty'), findsNothing);
      expect(find.text('Không có phòng nào phù hợp'), findsNothing);

      server.overrides.remove('GET /api/rooms/');
      await tapVisible(tester, find.descendant(of: key('room_list_error'), matching: find.text('Thử lại')));
      expect(find.text('Phòng A1'), findsOneWidget);
    });

    testWidgets('Backend thật sự không có phòng: trạng thái rỗng', (tester) async {
      server.rooms.clear();
      await openApp(tester, '/rooms');
      expect(key('room_list_empty'), findsOneWidget);
      expect(key('room_list_error'), findsNothing);
    });

    testWidgets('Tìm kiếm theo tên phòng; không khớp thì báo "không phù hợp" và Đặt lại được', (tester) async {
      await openApp(tester, '/rooms');
      expect(find.text('Phòng B1'), findsOneWidget);
      final roomSearch = find.descendant(of: find.byType(AppSearchBar), matching: find.byType(TextField));

      await tester.enterText(roomSearch, 'A2');
      await tester.pumpAndSettle();
      expect(find.text('Phòng A2'), findsOneWidget);
      expect(find.text('Phòng A1'), findsNothing);
      expect(find.text('Phòng B1'), findsNothing);

      await tester.enterText(roomSearch, 'không-tồn-tại');
      await tester.pumpAndSettle();
      expect(key('room_list_no_match'), findsOneWidget);
      expect(key('room_list_empty'), findsNothing);

      await tapVisible(tester, find.text('Đặt lại bộ lọc'));
      expect(find.text('Phòng A1'), findsOneWidget);
      expect(find.text('Phòng B1'), findsOneWidget);
    });

    testWidgets('Lọc theo nhà trọ; nhà trọ đang lọc bị xóa thì quay về "Tất cả", không lỗi', (tester) async {
      await openApp(tester, '/rooms');
      await tapVisible(tester, find.text('Tất cả tòa nhà'));
      await tapVisible(tester, find.text('Nhà B').last);

      expect(find.text('Phòng B1'), findsOneWidget);
      expect(find.text('Phòng A1'), findsNothing);

      server.properties.removeWhere((p) => p['id'] == 2);
      server.rooms.removeWhere((r) => r['property'] == 2);
      await repo.syncWithBackend();
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.text('Tất cả tòa nhà'), findsOneWidget);
      expect(find.text('Phòng A1'), findsOneWidget);
    });

    testWidgets('Đổi trạng thái phòng: gọi API trạng thái, chỉ báo thành công sau khi backend xác nhận',
        (tester) async {
      await openApp(tester, '/rooms/10');
      await tapVisible(tester, find.text('Đổi trạng thái'));
      await tapVisible(tester, find.text('AVAILABLE — Phòng trống'));
      await tapVisible(tester, find.text('MAINTENANCE — Đang bảo trì').last);
      await tapVisible(tester, find.text('Cập nhật trạng thái'));

      final posts = server.writes('POST', '/api/rooms/10/status/');
      expect(posts, hasLength(1));
      expect((jsonDecode(posts.single.body) as Map)['status'], 'MAINTENANCE');
      expect(find.text('Đã cập nhật trạng thái phòng Phòng A1.'), findsOneWidget);
      expect(repo.rooms.firstWhere((r) => r.id == 10).status, 'MAINTENANCE', reason: 'đọc lại từ backend');
    });

    testWidgets(
        '[QLNT-315] Phân trang danh sách phòng trọ (>6 phần tử): hiển thị 6 phòng trang đầu, chuyển trang Sau/Trước, chặn biên trang 0 và vượt trang cuối, xử lý danh sách 1 trang',
        (tester) async {
      // Trường hợp 1 trang (3 phòng mặc định): chỉ có nút trang 1, nút Trước và Sau đều bị khóa.
      await openApp(tester, '/rooms');
      expect(find.text('Hiển thị 1–3 trong tổng số 3 bản ghi'), findsOneWidget);
      expect(find.descendant(of: find.byType(PaginationWidget), matching: find.text('1')), findsOneWidget);
      expect(find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')), findsNothing);
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Trước')));
      expect(find.text('Hiển thị 1–3 trong tổng số 3 bản ghi'), findsOneWidget);
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Sau')));
      expect(find.text('Hiển thị 1–3 trong tổng số 3 bản ghi'), findsOneWidget);

      // Trường hợp > 6 phần tử (8 phòng: trang 1 có 6 phòng, trang 2 có 2 phòng).
      server.rooms
        ..clear()
        ..addAll([for (var i = 1; i <= 8; i++) _room(100 + i, 'Phòng P$i', 1, 'Nhà A')]);
      await repo.syncWithBackend();
      await tester.pumpAndSettle();

      // Trang đầu (trang 1): hiển thị đúng 6 phòng đầu (Phòng P1..Phòng P6), ẩn Phòng P7..Phòng P8.
      expect(find.text('Hiển thị 1–6 trong tổng số 8 bản ghi'), findsOneWidget);
      for (var i = 1; i <= 6; i++) {
        expect(find.text('Phòng P$i'), findsOneWidget);
      }
      expect(find.text('Phòng P7'), findsNothing);
      expect(find.text('Phòng P8'), findsNothing);

      // Ở trang 1, bấm "Trước" không được chuyển về trang 0.
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Trước')));
      expect(find.text('Hiển thị 1–6 trong tổng số 8 bản ghi'), findsOneWidget);
      expect(find.text('Phòng P1'), findsOneWidget);

      // Chuyển sang trang tiếp theo bằng nút "Sau": hiển thị đúng 2 phòng cuối (Phòng P7, Phòng P8), ẩn toàn bộ Phòng P1..P6.
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Sau')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);
      expect(find.text('Phòng P7'), findsOneWidget);
      expect(find.text('Phòng P8'), findsOneWidget);
      for (var i = 1; i <= 6; i++) {
        expect(find.text('Phòng P$i'), findsNothing);
      }

      // Ở trang cuối (trang 2), bấm "Sau" không được vượt quá trang cuối.
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Sau')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);
      expect(find.text('Phòng P7'), findsOneWidget);

      // Chuyển về trang trước bằng nút "Trước": quay lại trang 1 (đủ Phòng P1..Phòng P6, ẩn Phòng P7..P8).
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('Trước')));
      expect(find.text('Hiển thị 1–6 trong tổng số 8 bản ghi'), findsOneWidget);
      for (var i = 1; i <= 6; i++) {
        expect(find.text('Phòng P$i'), findsOneWidget);
      }
      expect(find.text('Phòng P7'), findsNothing);
      expect(find.text('Phòng P8'), findsNothing);

      // Chuyển sang chế độ hiển thị "Thẻ" (GridView): phân trang vẫn giữ đồng bộ 6 thẻ trang 1 và 2 thẻ trang 2.
      await tapVisible(tester, find.text('Thẻ'));
      expect(find.text('Hiển thị 1–6 trong tổng số 8 bản ghi'), findsOneWidget);
      expect(find.text('Phòng P1'), findsOneWidget);
      expect(find.text('Phòng P7'), findsNothing);
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);
      expect(find.text('Phòng P7'), findsOneWidget);
      expect(find.text('Phòng P8'), findsOneWidget);
      expect(find.text('Phòng P1'), findsNothing);
      await tapVisible(tester, find.text('Bảng'));
    });

    testWidgets(
        '[QLNT-315] Khi tìm kiếm hoặc lọc phòng trọ (nhà trọ/trạng thái/mức giá) ở trang 2: tự động quay về trang 1 và tính lại phân trang',
        (tester) async {
      server.rooms
        ..clear()
        ..addAll([
          for (var i = 1; i <= 6; i++) _room(100 + i, 'Phòng A$i', 1, 'Nhà A', status: 'AVAILABLE', price: 2800000),
          _room(107, 'Phòng B7', 2, 'Nhà B', status: 'OCCUPIED', price: 4500000),
          _room(108, 'Phòng B8', 2, 'Nhà B', status: 'OCCUPIED', price: 4800000),
        ]);
      await openApp(tester, '/rooms');

      // 1. Sang trang 2 rồi gõ tìm kiếm: tự động về trang 1 với số lượng bản ghi mới.
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);

      final roomSearch = find.descendant(of: find.byType(AppSearchBar), matching: find.byType(TextField));
      await tester.enterText(roomSearch, 'A3');
      await tester.pumpAndSettle();
      expect(find.text('Hiển thị 1–1 trong tổng số 1 bản ghi'), findsOneWidget);
      expect(find.text('Phòng A3'), findsOneWidget);
      expect(find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')), findsNothing);

      // 2. Đặt lại bộ lọc, sang trang 2 rồi lọc theo trạng thái "Đang thuê": về trang 1 hiển thị 2 phòng B7, B8.
      await tapVisible(tester, find.text('Đặt lại'));
      expect(find.text('Hiển thị 1–6 trong tổng số 8 bản ghi'), findsOneWidget);
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);

      await tapVisible(tester, find.text('Tất cả trạng thái'));
      await tapVisible(tester, find.text('Đang thuê').last);
      expect(find.text('Hiển thị 1–2 trong tổng số 2 bản ghi'), findsOneWidget);
      expect(find.text('Phòng B7'), findsOneWidget);
      expect(find.text('Phòng B8'), findsOneWidget);
      expect(find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')), findsNothing);

      // 3. Đặt lại bộ lọc, sang trang 2 rồi lọc theo tòa nhà "Nhà B": về trang 1 hiển thị 2 phòng B7, B8.
      await tapVisible(tester, find.text('Đặt lại'));
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);

      await tapVisible(tester, find.text('Tất cả tòa nhà'));
      await tapVisible(tester, find.text('Nhà B').last);
      expect(find.text('Hiển thị 1–2 trong tổng số 2 bản ghi'), findsOneWidget);
      expect(find.text('Phòng B7'), findsOneWidget);
      expect(find.text('Phòng B8'), findsOneWidget);

      // 4. Đặt lại bộ lọc, sang trang 2 rồi lọc theo mức giá "Trên 4.000.000 đ": về trang 1 hiển thị 2 phòng B7, B8.
      await tapVisible(tester, find.text('Đặt lại'));
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')));
      expect(find.text('Hiển thị 7–8 trong tổng số 8 bản ghi'), findsOneWidget);

      await tapVisible(tester, find.text('Tất cả mức giá'));
      await tapVisible(tester, find.text('Trên 4.000.000 đ').last);
      expect(find.text('Hiển thị 1–2 trong tổng số 2 bản ghi'), findsOneWidget);
      expect(find.text('Phòng B7'), findsOneWidget);
      expect(find.text('Phòng B8'), findsOneWidget);
    });

    testWidgets(
        '[QLNT-315] Xóa phòng ở trang cuối khiến trang hiện tại không còn hợp lệ: tự động lùi về trang cuối còn dữ liệu',
        (tester) async {
      server.rooms
        ..clear()
        ..addAll([for (var i = 1; i <= 7; i++) _room(200 + i, 'Phòng X$i', 1, 'Nhà A')]);
      await openApp(tester, '/rooms');

      // Sang trang 2 (chỉ có 1 phòng duy nhất là Phòng X7).
      await tapVisible(tester, find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')));
      expect(find.text('Hiển thị 7–7 trong tổng số 7 bản ghi'), findsOneWidget);
      expect(find.text('Phòng X7'), findsOneWidget);
      expect(find.text('Phòng X1'), findsNothing);

      // Xóa Phòng X7 ở trang 2 -> trang 2 không còn tồn tại, giao diện tự động lùi về trang 1 (6 bản ghi).
      await tapVisible(tester, find.byTooltip('Xóa phòng'));
      await tapVisible(tester, find.text('Xác nhận xóa'));

      expect(server.writes('DELETE', '/api/rooms/207/'), hasLength(1));
      expect(find.text('Đã xóa Phòng X7'), findsOneWidget);
      expect(find.text('Phòng X7'), findsNothing);
      for (var i = 1; i <= 6; i++) {
        expect(find.text('Phòng X$i'), findsOneWidget, reason: 'tự động lùi về trang 1 hiển thị đủ 6 phòng còn lại');
      }
      expect(find.text('Hiển thị 1–6 trong tổng số 6 bản ghi'), findsOneWidget);
      expect(find.descendant(of: find.byType(PaginationWidget), matching: find.text('2')), findsNothing);
    });

    testWidgets(
        '[QLNT-302, QLNT-315] PaginationWidget xử lý trực tiếp danh sách 0 bản ghi và khóa nút Trước/Sau ở biên',
        (tester) async {
      int? changedTo;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PaginationWidget(
              currentPage: 1,
              totalItems: 0,
              pageSize: 6,
              onPageChanged: (p) => changedTo = p,
            ),
          ),
        ),
      );
      expect(find.text('Hiển thị 0–0 trong tổng số 0 bản ghi'), findsOneWidget);
      await tester.tap(find.text('Trước'));
      await tester.tap(find.text('Sau'));
      await tester.pump();
      expect(changedTo, isNull, reason: 'danh sách rỗng khóa cả hai nút Trước và Sau');
    });
  });

  // ============================================================ ROOM CREATE
  group('Thêm phòng', () {
    Future<void> fillRoom(WidgetTester tester) async {
      await tester.enterText(field('Mã phòng'), 'P-B2');
      await tester.enterText(field('Tên phòng'), 'Phòng B2');
      await tester.enterText(field('Giá thuê (VNĐ/tháng)'), '3200000');
      await tester.enterText(field('Diện tích (m²)'), '22');
    }

    testWidgets('Gắn đúng nhà trọ đã chọn, báo thành công sau khi backend xác nhận, danh sách cập nhật',
        (tester) async {
      await openApp(tester, '/rooms/create');
      expect(find.byType(RoomCreatePage), findsOneWidget);

      await tapVisible(tester, find.text('NT-01 — Nhà A'));
      await tapVisible(tester, find.text('NT-02 — Nhà B').last);
      await fillRoom(tester);
      await tapVisible(tester, find.text('Lưu phòng').last);

      final posts = server.writes('POST', '/api/rooms/');
      expect(posts, hasLength(1));
      final payload = jsonDecode(posts.single.body) as Map<String, dynamic>;
      expect(payload['property'], 2, reason: 'đúng nhà trọ đang chọn');
      expect(payload['room_number'], 'Phòng B2');
      expect(payload.containsKey('id'), isFalse);

      expect(find.text('Đã tạo phòng "Phòng B2" trên hệ thống.'), findsOneWidget);
      expect(find.byType(RoomPage), findsOneWidget);
      expect(find.text('Phòng B2'), findsOneWidget);
    });

    testWidgets('Nhà trọ được tải sau khi mở trang: vẫn lưu được với nhà trọ đang hiển thị', (tester) async {
      server.hold = Completer<void>();
      await openApp(tester, '/rooms/create', settle: false);
      // (đang chuyển trang nên có thể có 2 bản dựng của cùng ô trạng thái)
      expect(find.text('Đang tải danh sách tòa nhà...'), findsWidgets);
      expect(find.textContaining('Chưa có tòa nhà nào'), findsNothing);

      server.hold!.complete();
      await tester.pumpAndSettle();
      expect(find.text('NT-01 — Nhà A'), findsOneWidget);
      await fillRoom(tester);
      await tapVisible(tester, find.text('Lưu phòng').last);

      final posts = server.writes('POST', '/api/rooms/');
      expect(posts, hasLength(1), reason: 'trước đây báo "Vui lòng chọn nhà trọ" dù ô chọn đang hiện Nhà A');
      expect((jsonDecode(posts.single.body) as Map)['property'], 1);
    });

    testWidgets('Backend từ chối: báo lỗi, ở lại trang, không báo thành công', (tester) async {
      server.overrides['POST /api/rooms/'] = (_) => _json({'code': ['Mã phòng đã tồn tại.']}, 400);
      await openApp(tester, '/rooms/create');
      await fillRoom(tester);
      await tapVisible(tester, find.text('Lưu phòng').last);

      expect(find.textContaining('Mã phòng đã tồn tại'), findsOneWidget);
      expect(find.textContaining('Đã tạo phòng'), findsNothing);
      expect(find.byType(RoomCreatePage), findsOneWidget);
    });

    testWidgets('Property Service lỗi: báo lỗi tải tòa nhà, không nói "chưa có tòa nhà"', (tester) async {
      server.overrides['GET /api/properties/'] = (_) => _json({'error': 'Property DOWN'}, 503);
      await openApp(tester, '/rooms/create');

      expect(find.textContaining('Không tải được danh sách tòa nhà'), findsOneWidget);
      expect(find.textContaining('Chưa có tòa nhà nào'), findsNothing);
    });
  });

  // ============================================================ ROOM DETAIL
  group('Chi tiết phòng (P4)', () {
    testWidgets('Mở thẳng /rooms/<id> khi đang tải: hiện đang tải, không phải "không tìm thấy"', (tester) async {
      server.hold = Completer<void>();
      await openApp(tester, '/rooms/10', settle: false);

      expect(key('room_detail_loading'), findsOneWidget);
      expect(find.text('Không tìm thấy phòng'), findsNothing);

      server.hold!.complete();
      await tester.pumpAndSettle();
      expect(find.text('Phòng A1'), findsWidgets);
      expect(key('room_detail_loading'), findsNothing);
    });

    testWidgets('Phòng không tồn tại sau khi tải xong: "không tìm thấy"', (tester) async {
      await openApp(tester, '/rooms/999');
      expect(key('room_detail_not_found'), findsOneWidget);
    });

    testWidgets('Room Service lỗi: báo lỗi + Thử lại, không phải "không tìm thấy"', (tester) async {
      server.overrides['GET /api/rooms/'] = (_) => _json({'error': 'Room DOWN'}, 503);
      await openApp(tester, '/rooms/10');

      expect(key('room_detail_error'), findsOneWidget);
      expect(key('room_detail_not_found'), findsNothing);
    });

    testWidgets('Hợp đồng liên quan ghép theo room_id; Contract Service lỗi thì báo lỗi', (tester) async {
      server.contracts.addAll([
        {'id': 1, 'contract_number': 'HD-A1', 'room_id': 10, 'status': 'ACTIVE', 'rental_price': 3000000},
        {'id': 2, 'contract_number': 'HD-B1', 'room_id': 20, 'status': 'ACTIVE', 'rental_price': 3000000},
      ]);
      await openApp(tester, '/rooms/10');
      expect(find.text('HD-A1'), findsOneWidget);
      expect(find.text('HD-B1'), findsNothing);

      server.contracts.clear();
      server.overrides['GET /api/contracts/'] = (_) => _json({'error': 'Contract DOWN'}, 503);
      await repo.syncWithBackend();
      await tester.pumpAndSettle();
      // Không còn hợp đồng nào giữ lại cho phòng này? Dữ liệu cũ được giữ khi lỗi (E5.1):
      expect(find.text('HD-A1'), findsOneWidget);
    });

    testWidgets('Contract Service lỗi ngay từ đầu: không nói "chưa có hợp đồng"', (tester) async {
      server.overrides['GET /api/contracts/'] = (_) => _json({'error': 'Contract DOWN'}, 503);
      await openApp(tester, '/rooms/10');

      expect(find.text('Hiện chưa có hợp đồng nào gắn với phòng này.'), findsNothing);
      expect(find.textContaining('Không tải được danh sách hợp đồng'), findsOneWidget);
    });
  });

  // ========================================================= ĐỊA CHỈ NHÀ TRỌ
  group('Địa chỉ nhà trọ khi chỉnh sửa (hồi quy)', () {
    Map<String, dynamic> serverA() => server.properties.firstWhere((p) => p['id'] == 1);

    Future<void> openEditA(WidgetTester tester) async {
      await tapVisible(tester, find.byTooltip('Chỉnh sửa').first);
      expect(find.text('Chỉnh sửa nhà trọ'), findsOneWidget);
    }

    String addressFieldText(WidgetTester tester) =>
        tester.widget<TextFormField>(field('Địa chỉ chi tiết')).controller!.text;

    testWidgets('Repository tách đúng địa chỉ chi tiết và địa chỉ đã ghép', (tester) async {
      await openApp(tester, '/property');
      final a = repo.properties.firstWhere((p) => p.id == 1);
      expect(a.address, '1 Đường Số 1', reason: 'address = trường address của backend');
      expect(a.ward, 'Phường 1');
      expect(a.district, 'Quận 1');
      expect(a.city, 'TP. Hồ Chí Minh');
      expect(a.fullAddress, '1 Đường Số 1, Phường 1, Quận 1, TP. Hồ Chí Minh');
      // Bảng vẫn hiển thị địa chỉ đầy đủ như trước.
      expect(find.text('1 Đường Số 1, Phường 1, Quận 1, TP. Hồ Chí Minh'), findsOneWidget);
    });

    testWidgets('Mở form sửa: ô địa chỉ chi tiết chỉ chứa số nhà / tên đường', (tester) async {
      await openApp(tester, '/property');
      await openEditA(tester);

      final text = addressFieldText(tester);
      expect(text, '1 Đường Số 1');
      expect(text, isNot(contains('Phường')));
      expect(text, isNot(contains('Quận')));
      expect(text, isNot(contains('TP. Hồ Chí Minh')));
    });

    testWidgets('Lưu nhiều lần không làm địa chỉ bị ghép lặp; đọc lại vẫn đúng từng thành phần',
        (tester) async {
      await openApp(tester, '/property');

      for (var i = 0; i < 3; i++) {
        await openEditA(tester);
        await tapVisible(tester, find.text('Lưu thay đổi'));
        expect(find.text('Đã cập nhật nhà trọ "Nhà A"'), findsOneWidget);
      }

      final patches = server.writes('PATCH', '/api/properties/1/');
      expect(patches, hasLength(3));
      for (final req in patches) {
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        expect(body['address'], '1 Đường Số 1');
        expect(body['ward'], 'Phường 1');
        expect(body['district'], 'Quận 1');
        expect(body.containsKey('full_address'), isFalse, reason: 'không ghi ngược chuỗi đã ghép');
      }

      // Dữ liệu phía backend sau 3 lần lưu: không bị lặp.
      expect(serverA()['address'], '1 Đường Số 1');
      expect(serverA()['ward'], 'Phường 1');
      expect(serverA()['district'], 'Quận 1');
      expect(serverA()['city'], 'TP. Hồ Chí Minh');
      expect(serverA()['full_address'], '1 Đường Số 1, Phường 1, Quận 1, TP. Hồ Chí Minh');

      // Đọc lại từ backend: model và form vẫn đúng.
      final a = repo.properties.firstWhere((p) => p.id == 1);
      expect(a.address, '1 Đường Số 1');
      expect(a.fullAddress, '1 Đường Số 1, Phường 1, Quận 1, TP. Hồ Chí Minh');
      expect('Phường 1'.allMatches(a.fullAddress), hasLength(1));
      await openEditA(tester);
      expect(addressFieldText(tester), '1 Đường Số 1');
    });

    testWidgets('Sửa địa chỉ chi tiết và quận: phường / thành phố giữ nguyên, địa chỉ ghép đúng một lần',
        (tester) async {
      await openApp(tester, '/property');
      await openEditA(tester);
      await tester.enterText(field('Địa chỉ chi tiết'), '25 Lê Lợi');
      await tester.enterText(field('Quận / Huyện / Khu vực'), 'Quận 3');
      await tapVisible(tester, find.text('Lưu thay đổi'));

      expect(serverA()['address'], '25 Lê Lợi');
      expect(serverA()['district'], 'Quận 3');
      expect(serverA()['ward'], 'Phường 1', reason: 'không có ô sửa phường: giữ giá trị cũ');
      expect(serverA()['city'], 'TP. Hồ Chí Minh', reason: 'thành phố không bị gửi đè');
      expect(serverA()['full_address'], '25 Lê Lợi, Phường 1, Quận 3, TP. Hồ Chí Minh');

      final a = repo.properties.firstWhere((p) => p.id == 1);
      expect(a.address, '25 Lê Lợi');
      expect(a.district, 'Quận 3');
      expect(find.text('25 Lê Lợi, Phường 1, Quận 3, TP. Hồ Chí Minh'), findsOneWidget);
    });
  });
}
