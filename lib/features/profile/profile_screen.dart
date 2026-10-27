import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/error_translator.dart';
import '../../core/routing/routes.dart';
import '../../core/theme/app_colors.dart';
import '../../core/constants/contact_info.dart';
import '../../widgets/ui/ui.dart';
import '../../core/utils/validators.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../providers/auth_provider.dart';
import '../../providers/locale_provider.dart';
import '../../widgets/loading_button.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  static const _languageOptions = [
    (locale: Locale('ru'), label: 'Русский'),
    (locale: Locale('en'), label: 'English'),
    (locale: Locale('tg'), label: 'Тоҷикӣ'),
  ];

  Future<void> _confirmLogout(BuildContext context) async {
    final t = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(t.logoutConfirmTitle),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(t.cancel)),
          TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(t.logout)),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      await context.read<AuthProvider>().logout();
    }
  }

  Future<void> _editProfile(BuildContext context) async {
    await showDialog<void>(
      context: context,
      builder: (_) => _EditProfileDialog(
          currentName: context.read<AuthProvider>().user?.fullName ?? ''),
    );
  }

  void _pickLanguage(BuildContext context) {
    final localeProvider = context.read<LocaleProvider>();
    showModalBottomSheet<void>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final option in _languageOptions)
              ListTile(
                title: Text(option.label),
                trailing: localeProvider.locale?.languageCode ==
                        option.locale.languageCode
                    ? const Icon(Icons.check_rounded, color: AppColors.brand)
                    : null,
                onTap: () {
                  localeProvider.setLocale(option.locale);
                  Navigator.pop(context);
                },
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final user = context.watch<AuthProvider>().user;
    final initial =
        (user?.fullName.isNotEmpty == true ? user!.fullName[0] : '?')
            .toUpperCase();

    return Scaffold(
      appBar: AppBar(title: Text(t.profileTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(Ui.s4, Ui.s2, Ui.s4, Ui.s6),
        children: [
          
          
          
          Column(
            children: [
              CircleAvatar(
                radius: 38,
                backgroundColor: AppColors.brandSoft,
                child: Text(initial,
                    style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        color: AppColors.brand)),
              ),
              const SizedBox(height: Ui.s3),
              Text(user?.fullName ?? '',
                  textAlign: TextAlign.center,
                  style: Ui.h2.copyWith(color: AppColors.ink)),
              const SizedBox(height: 2),
              Text(user?.phone ?? '',
                  style: Ui.body.copyWith(color: AppColors.inkSoft)),
              const SizedBox(height: Ui.s2),
              Wrap(
                spacing: Ui.s2,
                runSpacing: Ui.s1,
                alignment: WrapAlignment.center,
                children: [
                  if (user?.shortId != null) _Pill('ID: ${user!.shortId}'),
                  
                  
                  
                  
                  
                  
                  
                  
                  if (user?.isPremium == true) _Pill(t.premiumBadge),
                ],
              ),
            ],
          ),
          const SizedBox(height: Ui.s6),
          
          
          
          _BalanceCard(
            balanceSomoni: user?.balanceSomoni ?? 0,
            onTap: () => context.push(Routes.balance),
          ),
          const SizedBox(height: Ui.s6),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.language_rounded),
                  title: Text(t.appLanguage),
                  onTap: () => _pickLanguage(context),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.edit_outlined),
                  title: Text(t.editProfile),
                  onTap: () => _editProfile(context),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          
          
          
          Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 2),
                  child: Text(
                    t.profileContact.toUpperCase(),
                    style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.6,
                        color: AppColors.inkFaint),
                  ),
                ),
                ListTile(
                  leading: const Icon(Icons.mail_outline_rounded,
                      color: AppColors.brand),
                  title: Text(t.contactEmail),
                  subtitle: const Text(ContactInfo.email),
                  trailing: const Icon(Icons.chevron_right_rounded,
                      color: AppColors.inkFaint),
                  onTap: () =>
                      _openLink(context, 'mailto:${ContactInfo.email}'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              leading:
                  const Icon(Icons.logout_rounded, color: AppColors.danger),
              title: Text(t.logout,
                  style: const TextStyle(
                      color: AppColors.danger, fontWeight: FontWeight.w600)),
              onTap: () => _confirmLogout(context),
            ),
          ),
          const SizedBox(height: 20),
          
          
          Center(
            child: Wrap(
              alignment: WrapAlignment.center,
              spacing: 6,
              children: [
                GestureDetector(
                  onTap: () => _openLink(context, ContactInfo.termsUrl),
                  child: Text(t.registerTerms,
                      style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.inkFaint,
                          decoration: TextDecoration.underline)),
                ),
                const Text('·',
                    style: TextStyle(fontSize: 12, color: AppColors.inkFaint)),
                GestureDetector(
                  onTap: () => _openLink(context, ContactInfo.privacyUrl),
                  child: Text(t.registerPrivacy,
                      style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.inkFaint,
                          decoration: TextDecoration.underline)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}




class _Pill extends StatelessWidget {
  const _Pill(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: Ui.s3, vertical: 5),
      decoration: BoxDecoration(
        color: AppColors.brandSoft,
        borderRadius: BorderRadius.circular(Ui.rFull),
      ),
      child: Text(
        label,
        style: Ui.caption.copyWith(
          color: AppColors.brandDark,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}






class _BalanceCard extends StatelessWidget {
  const _BalanceCard({required this.balanceSomoni, required this.onTap});

  final double balanceSomoni;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    
    
    
    
    return UiCard(
      onTap: onTap,
      child: Row(
        children: [
          const UiIconChip(
            icon: Icons.account_balance_wallet_outlined,
            color: AppColors.brand,
            background: AppColors.brandSoft,
            size: 44,
            radius: Ui.rXl,
          ),
          const SizedBox(width: Ui.s4),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(t.balanceLabel,
                    style: Ui.caption.copyWith(color: AppColors.inkFaint)),
                const SizedBox(height: 1),
                Text('${balanceSomoni.toStringAsFixed(0)} c.',
                    style: Ui.h2.copyWith(color: AppColors.ink)),
                const SizedBox(height: Ui.s1),
                Text(t.profileBalanceCta,
                    style: Ui.caption.copyWith(color: AppColors.inkSoft)),
              ],
            ),
          ),
          const Icon(Icons.chevron_right_rounded, color: AppColors.inkFaint),
        ],
      ),
    );
  }
}






Future<void> _openLink(BuildContext context, String url) async {
  final t = AppLocalizations.of(context);
  final uri = Uri.tryParse(url);
  final opened = uri != null &&
      await launchUrl(uri, mode: LaunchMode.externalApplication);
  if (!opened && context.mounted) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(t.errorGeneric)));
  }
}


class _EditProfileDialog extends StatefulWidget {
  const _EditProfileDialog({required this.currentName});
  final String currentName;

  @override
  State<_EditProfileDialog> createState() => _EditProfileDialogState();
}

class _EditProfileDialogState extends State<_EditProfileDialog> {
  late final _nameCtrl = TextEditingController(text: widget.currentName);
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!Validators.isValidName(_nameCtrl.text)) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await context
          .read<AuthProvider>()
          .updateProfile(fullName: _nameCtrl.text.trim());
      if (mounted) Navigator.pop(context);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = messageFor(context, e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(t.editProfile),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _nameCtrl,
            decoration: InputDecoration(
                labelText: t.fullName, hintText: t.fullNameHint),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(_error!,
                style: const TextStyle(color: AppColors.danger, fontSize: 12)),
          ],
        ],
      ),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(context), child: Text(t.cancel)),
        LoadingButton(label: t.save, loading: _loading, onPressed: _save),
      ],
    );
  }
}
