import 'package:dio/dio.dart';

import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';

/// One-time deep link that binds this account to a Telegram chat.
///
/// The [deepLink] is the whole payload: an opaque random token in a
/// `t.me` URL. It deliberately carries no email, phone, balance, user id
/// or access token — a link that leaks from a chat history must not be
/// usable to learn anything about the account, and once redeemed or
/// expired it is not usable at all.
class TelegramLink {
  const TelegramLink({
    required this.deepLink,
    required this.botUsername,
    required this.expiresInSeconds,
  });

  final String deepLink;
  final String botUsername;
  final int expiresInSeconds;
}

/// Whether the Telegram top-up route is available and already linked.
class TelegramLinkStatus {
  const TelegramLinkStatus({
    required this.linked,
    required this.botConfigured,
    required this.botUsername,
  });

  const TelegramLinkStatus.unavailable()
      : linked = false,
        botConfigured = false,
        botUsername = '';

  final bool linked;

  /// False when the server has no bot token/username set. The UI hides
  /// the Telegram button entirely in that case rather than showing one
  /// that cannot work.
  final bool botConfigured;

  final String botUsername;
}

/// Reads the teacher's balance and starts the Telegram top-up flow.
///
/// Still nothing here can add credit. `/telegram/link` only mints an
/// account-linking token; the balance changes on the server, after an
/// administrator confirms in the bot that money actually arrived. A
/// modified client can get a link token for its own account and nothing
/// more, which is why this is safe to expose to the app at all.
class BillingService {
  final Dio _dio = ApiClient.instance.dio;

  /// Balance in somoni. Throws an [ApiException] on failure so the caller
  /// can show the real reason — an expired session and a dropped
  /// connection need different messages, and a silent 0 would read as
  /// "you have no credit", which is a different and alarming claim.
  Future<double> balance() async {
    try {
      final resp = await _dio.get(ApiConstants.billingBalance);
      final data = resp.data as Map<String, dynamic>;
      return (data['balance_somoni'] as num?)?.toDouble() ?? 0;
    } catch (e) {
      throw toApiException(e, context: 'billing-balance');
    }
  }

  /// Whether to offer the Telegram button, and what it should say.
  ///
  /// Degrades to [TelegramLinkStatus.unavailable] instead of throwing:
  /// this only decides whether an optional button is drawn, and failing
  /// the whole balance screen because one secondary call timed out would
  /// hide the number the teacher actually came to see.
  Future<TelegramLinkStatus> telegramStatus() async {
    try {
      final resp = await _dio.get(ApiConstants.billingTelegramStatus);
      final data = resp.data as Map<String, dynamic>;
      return TelegramLinkStatus(
        linked: data['linked'] as bool? ?? false,
        botConfigured: data['bot_configured'] as bool? ?? false,
        botUsername: data['bot_username'] as String? ?? '',
      );
    } catch (_) {
      return const TelegramLinkStatus.unavailable();
    }
  }

  /// Mint a fresh single-use link. Throws so the button can report why.
  ///
  /// Always called at tap time, never cached: the token is valid for ten
  /// minutes and single-use, so a link fetched when the screen opened
  /// would often be dead by the time it was tapped.
  Future<TelegramLink> telegramLink() async {
    try {
      final resp = await _dio.post(ApiConstants.billingTelegramLink);
      final data = resp.data as Map<String, dynamic>;
      final link = data['deep_link'] as String?;
      if (link == null || link.isEmpty) {
        throw ApiException.generic('empty deep_link');
      }
      return TelegramLink(
        deepLink: link,
        botUsername: data['bot_username'] as String? ?? '',
        expiresInSeconds: (data['expires_in_seconds'] as num?)?.toInt() ?? 0,
      );
    } catch (e) {
      if (e is ApiException) rethrow;
      throw toApiException(e, context: 'billing-telegram-link');
    }
  }
}
