import 'package:flutter/foundation.dart';
import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../core/storage/auth_storage.dart';
import '../models/user_model.dart';

class AuthProvider with ChangeNotifier {
  UserModel? _user;
  bool _isAuthenticated = false;
  bool _isLoading = true;
  String? _errorMessage;

  UserModel? get user => _user;
  bool get isAuthenticated => _isAuthenticated;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  AuthProvider() {
    initAuth();
  }

  Future<void> initAuth() async {
    _isLoading = true;
    notifyListeners();

    try {
      final token = await AuthStorage.getAccessToken();
      final savedUser = await AuthStorage.getUser();

      if (token != null && savedUser != null) {
        _user = savedUser;
        _isAuthenticated = true;
        // Background verify or refresh profile
        _fetchProfileSilently();
      } else {
        _isAuthenticated = false;
        _user = null;
      }
    } catch (_) {
      _isAuthenticated = false;
      _user = null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> _fetchProfileSilently() async {
    try {
      final res = await ApiClient.get(ApiConstants.currentUser);
      if (res is Map<String, dynamic>) {
        _user = UserModel.fromJson(res);
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<bool> login(String username, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final response = await ApiClient.post(
        ApiConstants.login,
        {
          'username': username.trim(),
          'password': password.trim(),
        },
        requireAuth: false,
      );

      final accessToken = response['access'] as String;
      final refreshToken = response['refresh'] as String;
      final userMap = response['user'] as Map<String, dynamic>;
      final userObj = UserModel.fromJson(userMap);

      await AuthStorage.saveAuthData(
        accessToken: accessToken,
        refreshToken: refreshToken,
        user: userObj,
      );

      _user = userObj;
      _isAuthenticated = true;
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await AuthStorage.clearAuthData();
    _user = null;
    _isAuthenticated = false;
    _errorMessage = null;
    notifyListeners();
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}

