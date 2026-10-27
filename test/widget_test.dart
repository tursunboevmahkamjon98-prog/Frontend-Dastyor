// Smoke test: the app boots to a language-select screen before anything
// else (first-ever launch: no locale, no onboarding, no session).
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:dastyor/main.dart';
import 'package:dastyor/providers/locale_provider.dart';
import 'package:dastyor/providers/onboarding_provider.dart';

void main() {
  testWidgets('boots to language select on first launch', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final localeProvider = LocaleProvider();
    final onboardingProvider = OnboardingProvider();
    await localeProvider.load();
    await onboardingProvider.load();

    await tester.pumpWidget(DastyorApp(
      localeProvider: localeProvider,
      onboardingProvider: onboardingProvider,
    ));
    await tester.pumpAndSettle();

    expect(find.text('Русский'), findsOneWidget);
  });
}
