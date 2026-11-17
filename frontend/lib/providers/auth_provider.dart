import 'package:flutter/foundation.dart';
import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../core/storage/auth_storage.dart';
import '../models/user_model.dart';

class AuthProvider with ChangeNotifier {
  UserModel? _user;
  bool _isAuthenticated = false;
  bool _isLoading = false;
  bool _isInitializing = true;
  String? _errorMessage;

  UserModel? get user => _user;
  bool get isAuthenticated => _isAuthenticated;
  bool get isLoading => _isLoading;
  bool get isInitializing => _isInitializing;
  String? get errorMessage => _errorMessage;

  AuthProvider() {
    ApiClient.onUnauthorized = _handleUnauthorized;
    initAuth();
  }

  void _handleUnauthorized() {
    _user = null;
    _isAuthenticated = false;
    _errorMessage = 'Phiên đã hết hạn. Vui lòng đăng nhập lại.';
    notifyListeners();
  }

  Future<void> initAuth() async {
    try {
      if (await AuthStorage.getAccessToken() != null) {
        final response = await ApiClient.get(ApiConstants.currentUser);
        _user = UserModel.fromJson(response as Map<String, dynamic>);
        await AuthStorage.saveUser(_user!);
        _isAuthenticated = true;
      }
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isInitializing = false;
      notifyListeners();
    }
  }

  Future<bool> _perform(Future<void> Function() action) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await action();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> login(String username, String password) => _perform(() async {
    final response = await ApiClient.post(ApiConstants.login,
        {'username': username.trim(), 'password': password}, requireAuth: false);
    final user = UserModel.fromJson(response['user'] as Map<String, dynamic>);
    ApiClient.resetSession();
    await AuthStorage.saveAuthData(accessToken: response['access'] as String,
        refreshToken: response['refresh'] as String, user: user);
    _user = user;
    _isAuthenticated = true;
  });

  Future<bool> register(Map<String, dynamic> data) => _perform(() async {
    await ApiClient.post(ApiConstants.register, data, requireAuth: false);
  });

  Future<bool> updateProfile(Map<String, dynamic> data) => _perform(() async {
    final response = await ApiClient.patch(ApiConstants.currentUser, data);
    _user = UserModel.fromJson(response as Map<String, dynamic>);
    await AuthStorage.saveUser(_user!);
  });

  Future<bool> changePassword(Map<String, dynamic> data) => _perform(() async {
    await ApiClient.post(ApiConstants.changePassword, data);
    await _clearSession();
  });

  Future<void> _clearSession() async {
    ApiClient.resetSession();
    await AuthStorage.clearAuthData();
    _user = null;
    _isAuthenticated = false;
  }

  Future<void> logout() async {
    final token = await AuthStorage.getRefreshToken();
    try {
      if (token != null) {
        await ApiClient.post(ApiConstants.logout, {'refresh': token}, requireAuth: false);
      }
    } catch (_) {
      // Local sign-out must still work when the server is offline.
    } finally {
      await _clearSession();
      _errorMessage = null;
      notifyListeners();
    }
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  @override
  void dispose() {
    if (ApiClient.onUnauthorized == _handleUnauthorized) ApiClient.onUnauthorized = null;
    super.dispose();
  }
}
