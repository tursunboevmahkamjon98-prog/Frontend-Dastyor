import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:dastyor/core/localization/tg_fallback_localizations.dart';
import 'package:dastyor/features/billing/balance_screen.dart';
import 'package:dastyor/l10n/gen/app_localizations.dart';
import 'package:dastyor/providers/auth_provider.dart';
import 'package:dastyor/services/billing_service.dart';
import 'package:dastyor/widgets/brand/telegram_glyph.dart';

/// Regression test for a bug that shipped once: the Telegram top-up
/// button was wrapped in `if (botConfigured)`, so on a server without a
/// bot token the balance screen showed no top-up control at all — and no
/// hint as to why. The screen was indistinguishable from one where the
/// feature had never been built.
///
/// These tests pin the corrected behaviour: the button is **always**
/// rendered, and the unconfigured case is a disabled button plus a
/// reason, never an empty screen.
class _FakeBilling extends BillingService {
  _FakeBilling({required this.status});

  final TelegramLinkStatus status;

  @override
  Future<double> balance() async => 12.34;

  @override
  Future<TelegramLinkStatus> telegramStatus() async => status;
}

Widget _wrap(BillingService billing) {
  return ChangeNotifierProvider<AuthProvider>(
    create: (_) => AuthProvider(),
    child: MaterialApp(
      locale: const Locale('tg'),
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        // Tajik has no Material/Cupertino translations upstream; these
        // fall back to Russian, exactly as main.dart does.
        TgMaterialLocalizationsDelegate(),
        TgCupertinoLocalizationsDelegate(),
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: BalanceScreen(billing: billing),
    ),
  );
}

void main() {
  testWidgets('shows an enabled Telegram top-up button when the bot is '
      'configured', (tester) async {
    await tester.pumpWidget(_wrap(_FakeBilling(
      status: const TelegramLinkStatus(
        linked: false,
        botConfigured: true,
        botUsername: 'dastyor_pay_bot',
      ),
    )));
    await tester.pumpAndSettle();

    expect(find.byType(TelegramGlyph), findsOneWidget,
        reason: 'the Telegram mark must be on the button');

    final label = find.text('🔗 Пайваст кардани ҳисоби Dastyor');
    expect(label, findsOneWidget, reason: 'the top-up button must be labelled');

    // Tappable: an InkWell with a non-null onTap wrapping the label.
    final inkWell = tester.widget<InkWell>(
      find.ancestor(of: label, matching: find.byType(InkWell)).first,
    );
    expect(inkWell.onTap, isNotNull, reason: 'the button must be tappable');

    // And no "not configured" excuse.
    expect(find.textContaining('танзим нашудааст'), findsNothing);
  });

  testWidgets('still shows the button, disabled and explained, when the bot '
      'is NOT configured', (tester) async {
    await tester.pumpWidget(_wrap(_FakeBilling(
      status: const TelegramLinkStatus.unavailable(),
    )));
    await tester.pumpAndSettle();

    // This is the regression: the button used to vanish entirely.
    expect(find.byType(TelegramGlyph), findsOneWidget,
        reason: 'the button must NOT disappear when the bot is unconfigured');
    final label = find.text('🔗 Пайваст кардани ҳисоби Dastyor');
    expect(label, findsOneWidget);

    final inkWell = tester.widget<InkWell>(
      find.ancestor(of: label, matching: find.byType(InkWell)).first,
    );
    expect(inkWell.onTap, isNull,
        reason: 'an unconfigured bot must not be tappable');

    expect(find.textContaining('танзим нашудааст'), findsOneWidget,
        reason: 'the teacher must be told why it is unavailable');
  });

  testWidgets('says "open the bot" once the account is linked',
      (tester) async {
    await tester.pumpWidget(_wrap(_FakeBilling(
      status: const TelegramLinkStatus(
        linked: true,
        botConfigured: true,
        botUsername: 'dastyor_pay_bot',
      ),
    )));
    await tester.pumpAndSettle();

    expect(find.text('🤖 Кушодани боти Telegram'), findsOneWidget);
    expect(find.textContaining('аллакай ба бот пайваст'), findsOneWidget);
  });

  testWidgets('the balance screen never claims a receipt alone adds credit',
      (tester) async {
    await tester.pumpWidget(_wrap(_FakeBilling(
      status: const TelegramLinkStatus(
        linked: false,
        botConfigured: true,
        botUsername: 'dastyor_pay_bot',
      ),
    )));
    await tester.pumpAndSettle();

    // The subtitle must carry the "an admin checks it first" condition.
    expect(find.textContaining('маъмур воридшавии пулро месанҷад'),
        findsOneWidget);
  });
}
