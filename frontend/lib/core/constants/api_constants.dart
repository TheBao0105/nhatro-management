class ApiConstants {
  // Mặc định chạy local trên Windows / Web / Desktop
  // Nếu test trên Android Emulator: đổi thành 'http://10.0.2.2:8000/api/v1'
  static String baseUrl = 'http://127.0.0.1:8000/api/v1';

  // SERVICE 1 — IDENTITY
  static String login = '$baseUrl/auth/login/';
  static String register = '$baseUrl/auth/register/';
  static String refreshToken = '$baseUrl/auth/refresh/';
  static String currentUser = '$baseUrl/auth/me/';
  static String users = '$baseUrl/users/';

  // SERVICE 2 — PROPERTY & MAINTENANCE
  static String properties = '$baseUrl/properties/';
  static String rooms = '$baseUrl/rooms/';
  static String maintenance = '$baseUrl/maintenance/';

  // SERVICE 3 — TENANT (Sprint 2)
  static String tenantStatus = '$baseUrl/tenants/status/';

  // SERVICE 4 — CONTRACT (Sprint 2)
  static String contractStatus = '$baseUrl/contracts/status/';

  // SERVICE 5 — BILLING & NOTIFICATION (Sprint 3)
  static String billingStatus = '$baseUrl/billing/status/';
}

