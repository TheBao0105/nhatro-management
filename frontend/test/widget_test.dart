import 'package:flutter_test/flutter_test.dart';
import 'package:nhatro_frontend/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const NhaTroApp());
    expect(find.byType(NhaTroApp), findsOneWidget);
  });
}
