class ApiConstants {
  // Mặc định chạy local trên Windows / Web / Desktop
  // Nếu test trên Android Emulator: đổi thành 'http://10.0.2.2:8000/api/v1'
  static String baseUrl = 'http://127.0.0.1:8000/api/v1';

  // SPRINT 1 — ARCHITECTURE & SERVICE INTEGRATION CHECK
  static String architectureStatus = '$baseUrl/architecture/status/';

  // SPRINT 1 — SERVICE 1: IDENTITY & AUTHENTICATION
  static String login = '$baseUrl/auth/login/';
  static String register = '$baseUrl/auth/register/';
  static String refreshToken = '$baseUrl/auth/refresh/';
  static String currentUser = '$baseUrl/auth/me/';
  static String users = '$baseUrl/users/';

  // SPRINT 1 — SERVICE 2: PROPERTY & ROOM MANAGEMENT
  static String properties = '$baseUrl/properties/';
  static String rooms = '$baseUrl/rooms/';

  // SPRINT 2 (LỘ TRÌNH TIẾP THEO) — SERVICE 3: TENANT
  static String tenantStatus = '$baseUrl/tenants/status/';

  // SPRINT 2 (LỘ TRÌNH TIẾP THEO) — SERVICE 4: CONTRACT
  static String contractStatus = '$baseUrl/contracts/status/';

  // SPRINT 3 (LỘ TRÌNH TIẾP THEO) — SERVICE 5: BILLING & NOTIFICATION
  static String billingStatus = '$baseUrl/billing/status/';
}
