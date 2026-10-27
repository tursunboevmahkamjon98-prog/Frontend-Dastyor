import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart' hide MaterialType;
import 'package:go_router/go_router.dart';

import '../../features/admin/admin_dashboard_screen.dart';
import '../../features/admin/admin_shell.dart';
import '../../features/admin/admin_users_screen.dart';
import '../../features/auth/forgot_otp_screen.dart';
import '../../features/materials/generate_all_screen.dart';
import '../../features/auth/forgot_password_screen.dart';
import '../../features/auth/login_otp_screen.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/register_otp_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/auth/reset_password_screen.dart';
import '../../features/dashboard/dashboard_shell.dart';
import '../../features/dashboard/home_tab.dart';
import '../../features/materials/material_detail_screen.dart';
import '../../features/materials/materials_list_screen.dart';
import '../../models/material_item.dart';
import '../../models/material_type.dart';
import '../../features/onboarding/language_select_screen.dart';
import '../../features/onboarding/onboarding_screen.dart';
import '../../features/billing/balance_screen.dart';
import '../../features/help/help_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/splash/splash_screen.dart';
import '../../providers/auth_provider.dart';
import '../../providers/locale_provider.dart';
import '../../providers/onboarding_provider.dart';
import 'routes.dart';






class AppRouter {
  AppRouter._();

  static final _authRoutes = <String>{
    Routes.login,
    Routes.loginOtp,
    Routes.register,
    Routes.registerOtp,
    Routes.forgotPassword,
    Routes.forgotPasswordOtp,
    Routes.forgotPasswordReset,
  };

  static final _webAuthRoutes = <String>{
    Routes.login,
    Routes.loginOtp,
    Routes.register,
    Routes.registerOtp,
    Routes.forgotPassword,
    Routes.forgotPasswordOtp,
    Routes.forgotPasswordReset,
  };

  static GoRouter build({
    required LocaleProvider locale,
    required OnboardingProvider onboarding,
    required AuthProvider auth,
  }) {
    return GoRouter(
      initialLocation: Routes.splash,
      refreshListenable: Listenable.merge([locale, onboarding, auth]),
      redirect: (context, state) =>
          _redirect(state.matchedLocation, locale, onboarding, auth),
      routes: [
        GoRoute(path: Routes.splash, builder: (_, __) => const SplashScreen()),
        GoRoute(
            path: Routes.language,
            builder: (_, __) => const LanguageSelectScreen()),
        GoRoute(
            path: Routes.onboarding,
            builder: (_, __) => const OnboardingScreen()),
        GoRoute(path: Routes.login, builder: (_, __) => const LoginScreen()),
        GoRoute(
          path: Routes.loginOtp,
          builder: (_, state) {
            final args = state.extra as Map<String, String>?;
            return args == null
                ? const _ExtraLostFallback(to: Routes.login)
                : LoginOtpScreen(args: args);
          },
        ),
        GoRoute(
            path: Routes.register, builder: (_, __) => const RegisterScreen()),
        GoRoute(
          path: Routes.registerOtp,
          builder: (_, state) {
            final args = state.extra as Map<String, String>?;
            return args == null
                ? const _ExtraLostFallback(to: Routes.register)
                : RegisterOtpScreen(args: args);
          },
        ),
        GoRoute(
            path: Routes.forgotPassword,
            builder: (_, __) => const ForgotPasswordScreen()),
        GoRoute(
          path: Routes.forgotPasswordOtp,
          builder: (_, state) {
            final phone = (state.extra as Map<String, String>?)?['phone'];
            return phone == null
                ? const _ExtraLostFallback(to: Routes.forgotPassword)
                : ForgotOtpScreen(phone: phone);
          },
        ),
        GoRoute(
          path: Routes.forgotPasswordReset,
          builder: (_, state) {
            final args = state.extra as Map<String, String>?;
            return args == null
                ? const _ExtraLostFallback(to: Routes.forgotPassword)
                : ResetPasswordScreen(args: args);
          },
        ),
        
        
        
        GoRoute(
          path: Routes.balance,
          builder: (_, __) => const BalanceScreen(),
        ),
        GoRoute(
          path: Routes.help,
          builder: (_, __) => const HelpScreen(),
        ),
        GoRoute(
          path: Routes.createDetails,
          builder: (_, __) => const GenerateAllScreen(),
        ),
        GoRoute(
          path: Routes.generating,
          builder: (_, __) => const GenerateAllScreen(),
        ),
        GoRoute(
          
          
          
          
          
          path: '${Routes.materialDetail}/:type/:id',
          builder: (_, state) {
            final type =
                MaterialTypeX.fromApiValue(state.pathParameters['type'] ?? '');
            final id = state.pathParameters['id'] ?? '';
            final hint = state.extra as MaterialItem?;
            return MaterialDetailScreen(type: type, id: id, initial: hint);
          },
        ),
        StatefulShellRoute.indexedStack(
          builder: (context, state, shell) =>
              AdminShell(navigationShell: shell),
          branches: [
            StatefulShellBranch(
              routes: [
                GoRoute(
                    path: Routes.adminDashboard,
                    builder: (_, __) => const AdminDashboardScreen())
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                    path: Routes.adminUsers,
                    builder: (_, __) => const AdminUsersScreen())
              ],
            ),
          ],
        ),
        GoRoute(
          path: Routes.generateAllForm,
          builder: (_, __) => const GenerateAllScreen(selectAll: true),
        ),
        StatefulShellRoute.indexedStack(
          builder: (context, state, shell) =>
              DashboardShell(navigationShell: shell),
          branches: [
            StatefulShellBranch(
              routes: [
                GoRoute(
                    path: Routes.dashboard, builder: (_, __) => const HomeTab())
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                    path: Routes.materials,
                    builder: (_, __) => const MaterialsListScreen())
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                    path: Routes.create,
                    builder: (_, __) => const GenerateAllScreen())
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                    path: Routes.profile,
                    builder: (_, __) => const ProfileScreen())
              ],
            ),
          ],
        ),
      ],
    );
  }

  static String? _redirect(
    String loc,
    LocaleProvider locale,
    OnboardingProvider onboarding,
    AuthProvider auth,
  ) {
    if (!locale.hasChosen) {
      return loc == Routes.language ? null : Routes.language;
    }
    if (!onboarding.seen) {
      return loc == Routes.onboarding ? null : Routes.onboarding;
    }
    if (auth.status == AuthStatus.unknown) {
      return loc == Routes.splash ? null : Routes.splash;
    }

    final onAuthRoute = _authRoutes.contains(loc);
    if (auth.status == AuthStatus.unauthenticated) {
      
      
      
      
      
      if (kIsWeb) return _webAuthRoutes.contains(loc) ? null : Routes.login;
      return onAuthRoute ? null : Routes.login;
    }
    
    
    
    
    
    
    final isAdmin = auth.user?.role == 'admin';
    if (onAuthRoute || loc == Routes.splash) {
      
      
      
      
      if (kIsWeb && !isAdmin) return Routes.materials;
      return isAdmin ? Routes.adminDashboard : Routes.dashboard;
    }
    final onAdminRoute =
        loc == Routes.adminDashboard || loc == Routes.adminUsers;
    if (isAdmin && !onAdminRoute) return Routes.adminDashboard;
    
    
    
    
    if (!isAdmin && onAdminRoute) return Routes.dashboard;
    return null;
  }
}






class _ExtraLostFallback extends StatefulWidget {
  const _ExtraLostFallback({required this.to});

  final String to;

  @override
  State<_ExtraLostFallback> createState() => _ExtraLostFallbackState();
}

class _ExtraLostFallbackState extends State<_ExtraLostFallback> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      
      
      
      
      
      
      
      
      
      
      if (context.canPop()) {
        context.pop();
      } else {
        context.go(widget.to);
      }
    });
  }

  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: CircularProgressIndicator()));
}
