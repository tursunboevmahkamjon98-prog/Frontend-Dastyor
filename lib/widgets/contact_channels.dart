import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/constants/contact_info.dart';
import '../core/theme/app_colors.dart';
import '../l10n/gen/app_localizations.dart';

/// The ways to reach the Dastyor team, as a block of buttons.
///
/// Used on the balance screen and in the profile's help section, so the
/// two cannot drift apart and a newly configured channel appears in both.
///
/// A channel that has not been configured is not drawn — see
/// [ContactInfo], which keeps Telegram and WhatsApp empty until someone
/// supplies real values. If nothing at all is configured, the widget
/// renders only the email row, which is the one channel this repository
/// genuinely has.
class ContactChannels extends StatelessWidget {
  const ContactChannels({super.key, this.dense = false});

  /// Compact form for the profile list; the balance screen uses the full
  /// size so the buttons read as the primary action there.
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (ContactInfo.hasTelegram) ...[
          _ChannelButton(
            icon: Icons.send_rounded,
            label: t.contactTelegram,
            // Telegram's own blue is used here on purpose and is not a
            // brand colour: these buttons are recognised by the colour of
            // the service they open, and painting them Dastyor red would
            // make two different destinations look like one action.
            color: const Color(0xFF229ED9),
            dense: dense,
            onTap: () => _open(context, ContactInfo.telegramUri),
          ),
          SizedBox(height: dense ? 8 : 10),
        ],
        if (ContactInfo.hasWhatsApp) ...[
          _ChannelButton(
            icon: Icons.chat_rounded,
            label: t.contactWhatsapp,
            color: const Color(0xFF25D366),
            dense: dense,
            onTap: () => _open(context, ContactInfo.whatsappUri),
          ),
          SizedBox(height: dense ? 8 : 10),
        ],
        _ChannelButton(
          icon: Icons.mail_outline_rounded,
          label: t.contactEmail,
          color: AppColors.inkSoft,
          dense: dense,
          outlined: true,
          onTap: () => _open(context, ContactInfo.emailUri),
        ),
        if (!ContactInfo.hasMessaging) ...[
          SizedBox(height: dense ? 8 : 10),
          Text(
            t.contactChannelsUnconfigured,
            style: const TextStyle(fontSize: 12, color: AppColors.inkFaint),
          ),
        ],
      ],
    );
  }

  /// Launch, and say so when it fails.
  ///
  /// `launchUrl` returns false when Android finds nothing to handle the
  /// intent, and throws when the platform channel itself errors. Both end
  /// as a visible message rather than a button that silently does nothing
  /// — which is the only feedback a teacher without Telegram installed
  /// would otherwise get. The https:// form means that is already rare:
  /// the browser handles it when the app is missing.
  static Future<void> _open(BuildContext context, Uri uri) async {
    final t = AppLocalizations.of(context);
    var ok = false;
    try {
      ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      ok = false;
    }
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(t.contactOpenFailed)),
      );
    }
  }
}

class _ChannelButton extends StatelessWidget {
  const _ChannelButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
    this.dense = false,
    this.outlined = false,
  });

  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  final bool dense;
  final bool outlined;

  @override
  Widget build(BuildContext context) {
    final height = dense ? 44.0 : 52.0;
    final style = TextStyle(
      fontSize: dense ? 14 : 15,
      fontWeight: FontWeight.w600,
      color: outlined ? AppColors.ink : Colors.white,
    );

    return SizedBox(
      height: height,
      child: Material(
        color: outlined ? AppColors.white : color,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: outlined
              ? const BorderSide(color: AppColors.borderStrong)
              : BorderSide.none,
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: dense ? 18 : 20, color: style.color),
              const SizedBox(width: 10),
              Flexible(
                child: Text(label, style: style, overflow: TextOverflow.ellipsis),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
