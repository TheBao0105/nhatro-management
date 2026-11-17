import 'package:flutter_test/flutter_test.dart';
import 'package:nhatro_frontend/main.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const NhaTroApp());
    await tester.pumpAndSettle();
    expect(find.byType(NhaTroApp), findsOneWidget);
    expect(find.text('ĐĂNG NHẬP'), findsOneWidget);
  });

  testWidgets('Registration form is reachable from login', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const NhaTroApp());
    await tester.pumpAndSettle();
    final register = find.text('Chưa có tài khoản? Đăng ký chủ trọ');
    await tester.ensureVisible(register);
    await tester.tap(register);
    await tester.pumpAndSettle();
    expect(find.text('Đăng ký chủ trọ'), findsOneWidget);
    expect(find.text('Xác nhận mật khẩu'), findsOneWidget);
    await tester.ensureVisible(find.text('ĐĂNG KÝ'));
    await tester.tap(find.text('ĐĂNG KÝ'));
    await tester.pumpAndSettle();
    expect(find.text('Vui lòng nhập Tên đăng nhập'), findsOneWidget);
  });
}
