import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:nhatro_frontend/core/network/api_client.dart';
import 'package:nhatro_frontend/core/storage/auth_storage.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() {
    ApiClient.resetSession();
    ApiClient.onUnauthorized = null;
    SharedPreferences.setMockInitialValues({
      'jwt_access_token': 'expired-access', 'jwt_refresh_token': 'valid-refresh',
    });
  });
  tearDown(() { ApiClient.onUnauthorized = null; ApiClient.resetSession(); });

  test('401 refreshes tokens and retries the protected request', () async {
    var refreshCalls = 0;
    await http.runWithClient(() async {
      final result = await ApiClient.get('http://localhost/protected');
      expect(result['ok'], true);
      expect(await AuthStorage.getAccessToken(), 'new-access');
      expect(await AuthStorage.getRefreshToken(), 'new-refresh');
    }, () => MockClient((request) async {
      if (request.url.path.endsWith('/auth/refresh/')) {
        refreshCalls++;
        expect(jsonDecode(request.body)['refresh'], 'valid-refresh');
        return http.Response('{"access":"new-access","refresh":"new-refresh"}', 200);
      }
      return request.headers['Authorization'] == 'Bearer new-access'
          ? http.Response('{"ok":true}', 200) : http.Response('{}', 401);
    }));
    expect(refreshCalls, 1);
  });

  test('simultaneous 401 responses share one refresh request', () async {
    var refreshCalls = 0;
    var initialCalls = 0;
    final bothInitialRequests = Completer<void>();
    await http.runWithClient(() async {
      final result = await Future.wait([
        ApiClient.get('http://localhost/one'), ApiClient.get('http://localhost/two'),
      ]);
      expect(result.length, 2);
    }, () => MockClient((request) async {
      if (request.url.path.endsWith('/auth/refresh/')) {
        refreshCalls++;
        await bothInitialRequests.future;
        return http.Response('{"access":"new-access","refresh":"new-refresh"}', 200);
      }
      if (request.headers['Authorization'] != 'Bearer new-access') {
        initialCalls++;
        if (initialCalls == 2) bothInitialRequests.complete();
        return http.Response('{}', 401);
      }
      return http.Response('{"ok":true}', 200);
    }));
    expect(refreshCalls, 1);
  });

  test('revoked refresh clears local credentials and notifies auth', () async {
    var signedOut = false;
    ApiClient.onUnauthorized = () { signedOut = true; };
    await http.runWithClient(() async {
      await expectLater(ApiClient.get('http://localhost/protected'),
          throwsA(isA<ApiException>().having((error) => error.statusCode, 'status', 401)));
    }, () => MockClient((request) async => http.Response('{}', 401)));
    expect(signedOut, true);
    expect(await AuthStorage.getAccessToken(), isNull);
    expect(await AuthStorage.getRefreshToken(), isNull);
  });

  test('temporary server failure preserves refresh for retry', () async {
    await http.runWithClient(() async {
      await expectLater(ApiClient.get('http://localhost/protected'), throwsA(isA<ApiException>()));
    }, () => MockClient((request) async => http.Response('{}',
      request.url.path.endsWith('/auth/refresh/') ? 503 : 401)));
    expect(await AuthStorage.getRefreshToken(), 'valid-refresh');
  });
}
