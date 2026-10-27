


class Routes {
  Routes._();

  static const splash = '/splash';
  static const language = '/language';
  static const onboarding = '/onboarding';

  static const login = '/login';
  static const loginOtp = '/login/otp';
  static const register = '/register';
  static const registerOtp = '/register/otp';
  static const forgotPassword = '/forgot-password';
  static const forgotPasswordOtp = '/forgot-password/otp';
  static const forgotPasswordReset = '/forgot-password/reset';

  
  
  
  static const dashboard = '/dashboard';
  static const materials = '/dashboard/materials';
  static const create = '/dashboard/create';
  static const createDetails = '/dashboard/create/details';
  static const generating = '/dashboard/create/generating';
  static const materialDetail = '/dashboard/materials/detail';
  
  static String materialDetailPath(String type, String id) =>
      '$materialDetail/$type/$id';
  static const profile = '/dashboard/profile';

  // Balance is read-only and help is a contact list; neither is a tab,
  // because both are destinations you arrive at from somewhere else
  // (a limit error, the profile) rather than places you browse.
  static const balance = '/dashboard/balance';
  static const help = '/dashboard/help';

  
  
  
  static const adminDashboard = '/admin';
  static const adminUsers = '/admin/users';

  
  static const generateAllForm = '/dashboard/create/all';

  
  
}
