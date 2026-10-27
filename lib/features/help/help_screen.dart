import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../widgets/contact_channels.dart';
import '../../widgets/ui/ui.dart';

/// Help and contact.
///
/// Thin on purpose: the channels themselves live in [ContactChannels] so
/// this screen and the balance screen offer exactly the same set, and a
/// channel configured later appears in both without either being edited.
class HelpScreen extends StatelessWidget {
  const HelpScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(title: Text(t.helpTitle)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(Ui.s4, Ui.s4, Ui.s4, Ui.s8),
          children: [
            Text(t.helpIntro,
                style: Ui.body.copyWith(color: AppColors.inkSoft)),
            const SizedBox(height: Ui.s5),
            const ContactChannels(),
          ],
        ),
      ),
    );
  }
}
