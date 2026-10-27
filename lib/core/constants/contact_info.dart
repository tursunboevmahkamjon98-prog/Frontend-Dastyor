/// Where a teacher reaches the Dastyor team.
///
/// Every channel here is build-time configurable through `--dart-define`,
/// and the two messaging ones are **deliberately empty by default**.
///
/// They are empty rather than filled with a plausible-looking handle
/// because nothing in this repository contains a real Telegram username or
/// WhatsApp number — not the backend config, not the web frontend, not the
/// previous versions of this file. Inventing one would ship a button that
/// opens a stranger's chat, or a dead link that looks alive. The UI asks
/// [hasTelegram] / [hasWhatsApp] and simply does not draw a channel that
/// has not been configured, so an unset value degrades to "this channel is
/// not offered" instead of to a broken button.
///
/// To turn them on, pass them at build time:
///
/// ```
/// flutter build apk --release \
///   --dart-define=TELEGRAM_USERNAME=dastyor_support \
///   --dart-define=WHATSAPP_PHONE=992900000000
/// ```
///
/// `TELEGRAM_USERNAME` is the @name without the @.
/// `WHATSAPP_PHONE` is digits only, with country code, no + and no spaces —
/// that is the format wa.me requires.
class ContactInfo {
  ContactInfo._();

  static const email = 'dastyor.rahnamo@gmail.com';

  /// Telegram @username, without the leading @. Empty = not configured.
  static const telegramUsername =
      String.fromEnvironment('TELEGRAM_USERNAME', defaultValue: '');

  /// WhatsApp number in wa.me form: country code + number, digits only.
  /// Empty = not configured.
  static const whatsappPhone =
      String.fromEnvironment('WHATSAPP_PHONE', defaultValue: '');

  static bool get hasTelegram => telegramUsername.trim().isNotEmpty;
  static bool get hasWhatsApp => whatsappPhone.trim().isNotEmpty;

  /// True when at least one messaging channel is configured. The balance
  /// screen uses this to decide whether it can offer "contact us for
  /// top-up instructions" at all.
  static bool get hasMessaging => hasTelegram || hasWhatsApp;

  /// `https://t.me/<name>` — a universal link, so it opens the Telegram app
  /// when installed and the web client when it is not. `tg://` would fail
  /// outright without the app.
  static Uri get telegramUri => Uri.parse('https://t.me/$telegramUsername');

  /// `https://wa.me/<digits>` — same reasoning: this resolves in a browser
  /// when WhatsApp is missing rather than throwing an activity-not-found.
  static Uri get whatsappUri {
    final digits = whatsappPhone.replaceAll(RegExp(r'[^0-9]'), '');
    return Uri.parse('https://wa.me/$digits');
  }

  static Uri get emailUri => Uri.parse('mailto:$email');

  static const webBaseUrl = String.fromEnvironment(
    'WEB_BASE_URL',
    defaultValue: 'https://rahnamo.tj',
  );
  static const termsUrl = '$webBaseUrl/terms';
  static const privacyUrl = '$webBaseUrl/privacy';
}
