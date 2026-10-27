






















class ApiConstants {
  ApiConstants._();

  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://rahnamo.tj',
  );

  static const String apiPrefix = '/api';

  
  static const String registerSendCode = '$apiPrefix/auth/register/send-code';
  static const String register = '$apiPrefix/auth/register';
  static const String login = '$apiPrefix/auth/login';
  static const String loginSendCode = '$apiPrefix/auth/login/send-code';
  static const String loginVerify = '$apiPrefix/auth/login/verify';
  static const String refresh = '$apiPrefix/auth/refresh';
  static const String logout = '$apiPrefix/auth/logout';
  static const String me = '$apiPrefix/auth/me';
  static const String avatar = '$apiPrefix/auth/avatar';
  static const String changePassword = '$apiPrefix/auth/change-password';
  static const String deleteAccount = '$apiPrefix/auth/me';
  static const String forgotPassword = '$apiPrefix/auth/forgot-password';
  static const String verifyCode = '$apiPrefix/auth/verify-code';
  static const String resetPassword = '$apiPrefix/auth/reset-password';

  
  
  
  static const String stats = '$apiPrefix/materials/stats';
  static const String search = '$apiPrefix/materials/search';
  static const String konspekts = '$apiPrefix/materials/konspekts';
  static const String lectures = '$apiPrefix/materials/lectures';
  static const String presentations = '$apiPrefix/materials/presentations';
  static const String tests = '$apiPrefix/materials/tests';
  static const String generate = '$apiPrefix/materials/generate';
  static const String generateAll = '$apiPrefix/materials/generate-all';
  static const String uploadSource = '$apiPrefix/materials/upload-source';
  static const String generateKonspektStream =
      '$apiPrefix/materials/generate-konspekt-stream';
  static const String downloadDocx = '$apiPrefix/materials/download-docx';
  static const String downloadPdf = '$apiPrefix/materials/download-pdf';
  static const String downloadPptx = '$apiPrefix/materials/download-pptx';
  static const String downloadTxt = '$apiPrefix/materials/download-txt';
  static const String downloadZip = '$apiPrefix/materials/download-zip';

  
  
  
  static const String quizSet = '$apiPrefix/materials/quiz-set';

  // Billing. The balance is read-only and there is still no endpoint
  // that adds credit from the app — a client cannot grant itself
  // anything. The two Telegram routes below only mint and report an
  // account-linking token; crediting happens on the server after an
  // administrator confirms a payment in the bot.
  static const String billingBalance = '$apiPrefix/billing/balance';

  /// POST. Returns a single-use `https://t.me/<bot>?start=<token>` deep
  /// link for the authenticated account. The token is opaque and carries
  /// no account data — see the backend route's docstring.
  static const String billingTelegramLink =
      '$apiPrefix/billing/telegram/standalone-link';

  /// GET. Whether this account already has a Telegram chat bound, and
  /// whether the server has a bot configured at all.
  static const String billingTelegramStatus =
      '$apiPrefix/billing/telegram/standalone-status';

  
  
  
  
  
  static const String adminStats = '$apiPrefix/admin/stats';
  static const String adminUsers = '$apiPrefix/admin/users';
  static String adminUserRole(String id) => '$apiPrefix/admin/users/$id/role';
  static String adminUserPremium(String id) =>
      '$apiPrefix/admin/users/$id/premium';
  static String adminUserBalance(String id) =>
      '$apiPrefix/admin/users/$id/balance';
  static String adminUserDelete(String id) => '$apiPrefix/admin/users/$id';


  static const Duration connectTimeout = Duration(seconds: 20);
  static const Duration receiveTimeout = Duration(seconds: 60);
  
  
  
  
  
  
  
  
  
  
  
  static const Duration generateTimeout = Duration(seconds: 300);
}
