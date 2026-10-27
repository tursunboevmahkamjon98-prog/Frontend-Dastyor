import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'core/localization/tg_fallback_localizations.dart';
import 'core/routing/app_router.dart';
import 'core/theme/app_theme.dart';
import 'l10n/gen/app_localizations.dart';
import 'providers/auth_provider.dart';
import 'providers/locale_provider.dart';
import 'providers/onboarding_provider.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final localeProvider = LocaleProvider();
  final onboardingProvider = OnboardingProvider();
  
  
  await Future.wait([localeProvider.load(), onboardingProvider.load()]);
  runApp(DastyorApp(localeProvider: localeProvider, onboardingProvider: onboardingProvider));
}

class DastyorApp extends StatefulWidget {
  const DastyorApp({super.key, required this.localeProvider, required this.onboardingProvider});

  final LocaleProvider localeProvider;
  final OnboardingProvider onboardingProvider;

  @override
  State<DastyorApp> createState() => _DastyorAppState();
}

class _DastyorAppState extends State<DastyorApp> {
  final _authProvider = AuthProvider();
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _authProvider.initialize();
    
    
    _router = AppRouter.build(
      locale: widget.localeProvider,
      onboarding: widget.onboardingProvider,
      auth: _authProvider,
    );
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: widget.localeProvider),
        ChangeNotifierProvider.value(value: widget.onboardingProvider),
        ChangeNotifierProvider.value(value: _authProvider),
      ],
      child: AnimatedBuilder(
        
        
        animation: widget.localeProvider,
        builder: (context, _) => MaterialApp.router(
          title: 'Dastyor',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          
          
          
          
          
          
          
          
          
          
          
          themeMode: ThemeMode.light,
          locale: widget.localeProvider.locale,
          supportedLocales: LocaleProvider.supported,
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
            
            
            TgMaterialLocalizationsDelegate(),
            TgCupertinoLocalizationsDelegate(),
          ],
          routerConfig: _router,
        ),
      ),
    );
  }
}
