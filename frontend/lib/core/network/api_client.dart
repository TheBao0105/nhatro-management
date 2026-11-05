import 'dart:convert';
import 'package:http/http.dart' as http;
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
  static Future<Map<String, String>> _getHeaders({bool requireAuth = true}) async {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (requireAuth) {
      final token = await AuthStorage.getAccessToken();
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    return headers;
  }

  static Future<dynamic> get(String url, {bool requireAuth = true}) async {
    try {
      final headers = await _getHeaders(requireAuth: requireAuth);
      final response = await http.get(Uri.parse(url), headers: headers);
      return _processResponse(response);
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Không thể kết nối đến máy chủ: $e');
    }
  }

  static Future<dynamic> post(String url, Map<String, dynamic> data, {bool requireAuth = true}) async {
    try {
      final headers = await _getHeaders(requireAuth: requireAuth);
      final response = await http.post(
        Uri.parse(url),
        headers: headers,
        body: jsonEncode(data),
      );
      return _processResponse(response);
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Không thể kết nối đến máy chủ: $e');
    }
  }

  static Future<dynamic> put(String url, Map<String, dynamic> data, {bool requireAuth = true}) async {
    try {
      final headers = await _getHeaders(requireAuth: requireAuth);
      final response = await http.put(
        Uri.parse(url),
        headers: headers,
        body: jsonEncode(data),
      );
      return _processResponse(response);
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Không thể kết nối đến máy chủ: $e');
    }
  }

  static Future<dynamic> patch(String url, Map<String, dynamic> data, {bool requireAuth = true}) async {
    try {
      final headers = await _getHeaders(requireAuth: requireAuth);
      final response = await http.patch(
        Uri.parse(url),
        headers: headers,
        body: jsonEncode(data),
      );
      return _processResponse(response);
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Không thể kết nối đến máy chủ: $e');
    }
  }

  static Future<dynamic> delete(String url, {bool requireAuth = true}) async {
    try {
      final headers = await _getHeaders(requireAuth: requireAuth);
      final response = await http.delete(Uri.parse(url), headers: headers);
      return _processResponse(response);
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Không thể kết nối đến máy chủ: $e');
    }
  }

  static dynamic _processResponse(http.Response response) {
    dynamic body;
    try {
      body = jsonDecode(utf8.decode(response.bodyBytes));
    } catch (_) {
      body = response.body;
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return body;
    } else if (response.statusCode == 401) {
      throw ApiException(
        body is Map && body['detail'] != null
            ? body['detail']
            : 'Phiên đăng nhập đã hết hạn hoặc thông tin không hợp lệ.',
        statusCode: 401,
      );
    } else if (response.statusCode == 403) {
      throw ApiException(
        'Bạn không có quyền thực hiện thao tác này.',
        statusCode: 403,
      );
    } else {
      String message = 'Đã có lỗi xảy ra (${response.statusCode})';
      if (body is Map) {
        if (body['detail'] != null) {
          message = body['detail'].toString();
        } else if (body['error'] != null) {
          message = body['error'].toString();
        } else {
          // Flatten first validation error
          final firstKey = body.keys.firstOrNull;
          if (firstKey != null && body[firstKey] is List) {
            message = '$firstKey: ${body[firstKey][0]}';
          }
        }
      }
      throw ApiException(message, statusCode: response.statusCode, details: body);
    }
  }
}

