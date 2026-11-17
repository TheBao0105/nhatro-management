import 'dart:convert';
import 'package:http/http.dart' as http;
import '../constants/api_constants.dart';
import '../storage/auth_storage.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic details;
  ApiException(this.message, {this.statusCode, this.details});
  @override
  String toString() => message;
}

class ApiClient {
  static const _timeout = Duration(seconds: 20);
  static void Function()? onUnauthorized;
  static Future<bool>? _refreshing;
  static int _sessionVersion = 0;

  static void resetSession() {
    _sessionVersion++;
    _refreshing = null;
  }

  static Future<dynamic> get(String url, {bool requireAuth = true}) =>
      _send('GET', url, requireAuth: requireAuth);
  static Future<dynamic> post(String url, Map<String, dynamic> data,
          {bool requireAuth = true}) =>
      _send('POST', url, data: data, requireAuth: requireAuth);
  static Future<dynamic> put(String url, Map<String, dynamic> data,
          {bool requireAuth = true}) =>
      _send('PUT', url, data: data, requireAuth: requireAuth);
  static Future<dynamic> patch(String url, Map<String, dynamic> data,
          {bool requireAuth = true}) =>
      _send('PATCH', url, data: data, requireAuth: requireAuth);
  static Future<dynamic> delete(String url, {bool requireAuth = true}) =>
      _send('DELETE', url, requireAuth: requireAuth);

  static Future<http.Response> _request(String method, String url,
      Map<String, dynamic>? data, bool requireAuth) async {
    final token = requireAuth ? await AuthStorage.getAccessToken() : null;
    final headers = <String, String>{
      'Content-Type': 'application/json', 'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
    final uri = Uri.parse(url);
    final body = data == null ? null : jsonEncode(data);
    final request = switch (method) {
      'GET' => http.get(uri, headers: headers),
      'POST' => http.post(uri, headers: headers, body: body),
      'PUT' => http.put(uri, headers: headers, body: body),
      'PATCH' => http.patch(uri, headers: headers, body: body),
      _ => http.delete(uri, headers: headers),
    };
    return request.timeout(_timeout);
  }

  static Future<bool> _refresh(int version) async {
    final token = await AuthStorage.getRefreshToken();
    if (token == null) return false;
    final response = await _request('POST', ApiConstants.refreshToken,
        {'refresh': token}, false);
    if (version != _sessionVersion) return false;
    if (response.statusCode == 400 || response.statusCode == 401) return false;
    final data = _processResponse(response) as Map<String, dynamic>;
    await AuthStorage.saveTokens(data['access'] as String,
        data['refresh'] as String? ?? token);
    return true;
  }

  static Future<dynamic> _send(String method, String url,
      {Map<String, dynamic>? data, bool requireAuth = true}) async {
    final version = _sessionVersion;
    try {
      var response = await _request(method, url, data, requireAuth);
      if (requireAuth && version != _sessionVersion) {
        throw ApiException('Phiên đăng nhập đã thay đổi.', statusCode: 401);
      }
      if (requireAuth && response.statusCode == 401) {
        final pending = _refreshing ??= _refresh(version);
        bool refreshed;
        try {
          refreshed = await pending;
        } finally {
          if (identical(_refreshing, pending)) _refreshing = null;
        }
        if (version != _sessionVersion) {
          throw ApiException('Phiên đăng nhập đã thay đổi.', statusCode: 401);
        }
        if (refreshed) response = await _request(method, url, data, requireAuth);
        if (!refreshed || response.statusCode == 401) {
          resetSession();
          await AuthStorage.clearAuthData();
          onUnauthorized?.call();
          throw ApiException('Phiên đã hết hạn. Vui lòng đăng nhập lại.', statusCode: 401);
        }
      }
      if (requireAuth && version != _sessionVersion) {
        throw ApiException('Phiên đăng nhập đã thay đổi.', statusCode: 401);
      }
      return _processResponse(response);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw ApiException('Không thể kết nối máy chủ. Kiểm tra mạng và backend.');
    }
  }

  static dynamic _processResponse(http.Response response) {
    if (response.statusCode == 204) return null;
    dynamic body;
    try {
      body = jsonDecode(utf8.decode(response.bodyBytes));
    } catch (_) {
      body = null;
    }
    if (response.statusCode >= 200 && response.statusCode < 300) return body;
    final message = response.statusCode == 403
        ? 'Bạn không có quyền thực hiện thao tác này.'
        : _errorText(body);
    throw ApiException(message, statusCode: response.statusCode, details: body);
  }

  static String _errorText(dynamic body) {
    if (body is Map) {
      if (body['detail'] != null) return body['detail'].toString();
      return body.entries.map((entry) => '${entry.key}: ${_errorText(entry.value)}').join('\n');
    }
    if (body is List) return body.map(_errorText).join(' ');
    return body?.toString() ?? 'Máy chủ trả về lỗi. Vui lòng thử lại.';
  }
}
