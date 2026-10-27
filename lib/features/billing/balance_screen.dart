import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/constants/contact_info.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/error_translator.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../providers/auth_provider.dart';
import '../../services/billing_service.dart';
import '../../widgets/brand/telegram_glyph.dart';
import '../../widgets/contact_channels.dart';
import '../../widgets/ui/ui.dart';

/// Balance, and the two ways to top it up.
///
/// What this screen still deliberately does not do:
///
///  1. It does not take payment. There is no card form, no checkout and
///     no gateway. The Telegram route below does not change that — the
///     app hands off to a bot, a human transfers money through their own
///     bank, and an administrator confirms it. No money moves through
///     this code.
///  2. It does not promise anything in return for a tap. Opening the bot
///     is opening the bot: it does not confirm a payment, raise a limit
///     or add credit. That is why the Telegram card says the balance
///     changes only after an admin checks the money arrived, rather than
///     implying the receipt itself is enough.
///  3. It cannot grant credit even if modified. `/telegram/link` mints an
///     account-linking token and nothing else; crediting lives behind the
///     admin's confirmation on the server, and generation limits stay
///     enforced there in every case.
///
/// The number comes from the backend on every visit rather than from the
/// cached user, because a top-up granted while the app was open would
/// otherwise not appear until the next sign-in. The cached value is used
/// as the first paint so the screen is never blank.
class BalanceScreen extends StatefulWidget {
  const BalanceScreen({super.key, this.billing});

  /// Injectable so a widget test can drive the screen without a network.
  /// Production passes nothing and gets the real service.
  final BillingService? billing;

  @override
  State<BalanceScreen> createState() => _BalanceScreenState();
}

class _BalanceScreenState extends State<BalanceScreen> {
  late final BillingService _billing = widget.billing ?? BillingService();

  double? _balance;
  ApiException? _error;
  bool _loading = true;

  TelegramLinkStatus _telegram = const TelegramLinkStatus.unavailable();
  bool _openingTelegram = false;

  @override
  void initState() {
    super.initState();
    _balance = context.read<AuthProvider>().user?.balanceSomoni;
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    // Two independent calls, awaited together: the Telegram status is
    // optional decoration and must not add its latency to the number the
    // teacher came for. telegramStatus() swallows its own failures.
    final results = await Future.wait([
      _billing.balance().then<Object?>((v) => v).catchError((Object e) => e),
      _billing.telegramStatus(),
    ]);

    if (!mounted) return;
    final balanceResult = results[0];
    setState(() {
      _loading = false;
      _telegram = results[1] as TelegramLinkStatus;
      if (balanceResult is double) {
        _balance = balanceResult;
        _error = null;
      } else if (balanceResult is ApiException) {
        _error = balanceResult;
      } else {
        _error = ApiException.generic();
      }
    });
  }

  /// Mint a one-time link and hand off to Telegram.
  ///
  /// The link is requested at tap time, never cached: it is valid for ten
  /// minutes and single-use, so one fetched when the screen opened would
  /// usually be dead by the time anyone pressed the button.
  Future<void> _openTelegram() async {
    if (_openingTelegram) return;
    final t = AppLocalizations.of(context);
    setState(() => _openingTelegram = true);

    try {
      final link = await _billing.telegramLink();
      // https://t.me/... rather than tg://, for the same reason
      // ContactInfo documents: it resolves in a browser when Telegram is
      // not installed instead of failing as activity-not-found.
      final ok = await launchUrl(
        Uri.parse(link.deepLink),
        mode: LaunchMode.externalApplication,
      );
      if (!ok && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(t.contactOpenFailed)),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            e is ApiException ? messageFor(context, e) : t.balanceTelegramFailed,
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _openingTelegram = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(title: Text(t.balanceTitle)),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(Ui.s4, Ui.s4, Ui.s4, Ui.s8),
            children: [
              _BalanceCard(
                balance: _balance,
                loading: _loading,
                errorText: _error == null ? null : messageFor(context, _error!),
                onRetry: _refresh,
              ),
              const SizedBox(height: Ui.s5),

              // The primary top-up route, above the contact block: it is
              // the one a teacher can act on immediately.
              //
              // Always drawn, never hidden. An earlier version showed it
              // only when the server reported a configured bot, which
              // read as "this feature does not exist" — the screen just
              // had nothing on it, with no way to tell a missing deploy
              // from a missing bot token from a bug. A disabled button
              // with its reason is strictly more informative.
              _TelegramTopUpCard(
                configured: _telegram.botConfigured,
                linked: _telegram.linked,
                busy: _openingTelegram,
                onTap: _openTelegram,
              ),
              const SizedBox(height: Ui.s5),

              Text(t.balanceTopUpTitle, style: Ui.title),
              const SizedBox(height: Ui.s2),
              Text(
                ContactInfo.hasMessaging
                    ? t.balanceTopUpBody
                    : t.balanceTopUpBodyEmailOnly,
                style: Ui.body.copyWith(color: AppColors.inkSoft),
              ),
              const SizedBox(height: Ui.s4),
              const ContactChannels(),

              const SizedBox(height: Ui.s5),
              UiCard(
                fill: AppColors.surface,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.info_outline_rounded,
                        size: 18, color: AppColors.inkFaint),
                    const SizedBox(width: Ui.s3),
                    Expanded(
                      child: Text(
                        t.balanceNoPaymentNote,
                        style: Ui.caption.copyWith(color: AppColors.inkSoft),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// The Telegram top-up block: heading, one honest sentence, one button.
///
/// Brand red rather than Telegram's blue, which is the opposite of what
/// [ContactChannels] does and is deliberate. Those rows are a list of
/// outside services to contact, and colouring each one after its service
/// is how a reader tells them apart. This is Dastyor's own primary
/// top-up action that happens to be delivered over Telegram, so it wears
/// Dastyor's colour and the mark alone carries the destination.
class _TelegramTopUpCard extends StatelessWidget {
  const _TelegramTopUpCard({
    required this.configured,
    required this.linked,
    required this.busy,
    required this.onTap,
  });

  /// False when the server has no bot token/username set, or when the
  /// status call failed. The button is drawn but disabled, with
  /// [AppLocalizations.balanceTelegramUnavailable] explaining why.
  final bool configured;

  final bool linked;
  final bool busy;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final label = configured && linked
        ? t.balanceTelegramButtonLinked
        : t.balanceTelegramButton;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(t.balanceTelegramTitle, style: Ui.title),
        const SizedBox(height: Ui.s2),
        Text(
          t.balanceTelegramSubtitle,
          style: Ui.body.copyWith(color: AppColors.inkSoft),
        ),
        if (configured && linked) ...[
          const SizedBox(height: Ui.s1),
          Text(
            t.balanceTelegramLinkedNote,
            style: Ui.caption.copyWith(color: AppColors.inkFaint),
          ),
        ],
        const SizedBox(height: Ui.s4),
        _TelegramButton(
          label: label,
          busy: busy,
          onTap: configured ? onTap : null,
        ),
        if (!configured) ...[
          const SizedBox(height: Ui.s2),
          Text(
            t.balanceTelegramUnavailable,
            style: Ui.caption.copyWith(color: AppColors.inkFaint),
          ),
        ],
      ],
    );
  }
}

/// Red-and-white, full-width, and sized by the label rather than fixed.
///
/// Accessibility notes, since this is the screen's primary action:
///
///  * The tap target grows with the system text scale instead of being
///    pinned to 52 px. At the largest accessibility font a fixed-height
///    button clips its own label, which is exactly when a user can least
///    afford to guess what a button does. `minHeight` keeps it at or
///    above the 48 px touch-target floor at every scale.
///  * The label wraps to two lines rather than ellipsising. "Пур кардани
///    баланс тавассути Telegram" does not fit one line on a narrow phone,
///    and a truncated instruction is worse than a taller button.
///  * `Semantics(button: true)` with the label and a busy flag, so a
///    screen reader announces one button with its text — the glyph is
///    decorative and stays unannounced.
class _TelegramButton extends StatelessWidget {
  const _TelegramButton({
    required this.label,
    required this.busy,
    required this.onTap,
  });

  final String label;
  final bool busy;

  /// Null disables the button — the bot is not configured on the server.
  /// Rendered at reduced opacity rather than removed, so the teacher can
  /// see the channel exists and read why it is not available yet.
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context).scale(1.0);
    final enabled = !busy && onTap != null;

    return Semantics(
      button: true,
      enabled: enabled,
      label: label,
      child: ExcludeSemantics(
        child: Material(
          color: enabled
              ? AppColors.brand
              // Flattened against the page rather than given a grey of
              // its own, so a disabled button still reads as the same
              // button and not as a different control.
              : AppColors.brand.withValues(alpha: 0.45),
          borderRadius: BorderRadius.circular(Ui.rXl),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: enabled ? onTap : null,
            // A visible ripple and a focus highlight: the button is
            // reachable by keyboard on web and by a switch device.
            splashColor: Colors.white24,
            highlightColor: Colors.white10,
            focusColor: Colors.white24,
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: 52 * scale.clamp(1.0, 1.6)),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: Ui.s4,
                  vertical: Ui.s3,
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    if (busy)
                      const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    else
                      const TelegramGlyph(size: 20, color: Colors.white),
                    const SizedBox(width: Ui.s3),
                    Flexible(
                      child: Text(
                        label,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                          height: 1.25,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _BalanceCard extends StatelessWidget {
  const _BalanceCard({
    required this.balance,
    required this.loading,
    required this.errorText,
    required this.onRetry,
  });

  final double? balance;
  final bool loading;
  final String? errorText;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);

    return UiCard(
      fill: AppColors.brand,
      padding: const EdgeInsets.all(Ui.s5),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                t.balanceCurrent.toUpperCase(),
                style: Ui.eyebrow.copyWith(color: Colors.white70),
              ),
              const Spacer(),
              if (loading)
                const SizedBox(
                  height: 14,
                  width: 14,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white70),
                ),
            ],
          ),
          const SizedBox(height: Ui.s3),

          // An error must not be shown as a number. A balance of "0" when
          // the request actually failed is a specific and wrong claim.
          if (errorText != null) ...[
            Text(errorText!,
                style: Ui.body.copyWith(color: Colors.white)),
            const SizedBox(height: Ui.s3),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded, size: 18),
              label: Text(t.retry),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.white,
                side: const BorderSide(color: Colors.white54),
              ),
            ),
          ] else
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Text(
                  balance == null ? '—' : balance!.toStringAsFixed(2),
                  style: const TextStyle(
                    fontSize: 38,
                    height: 1.05,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(width: Ui.s2),
                Text(
                  t.currencySomoni,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: Colors.white70,
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }
}
