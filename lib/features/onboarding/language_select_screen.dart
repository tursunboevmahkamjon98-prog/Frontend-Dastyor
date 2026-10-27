import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../providers/locale_provider.dart';
import '../../widgets/brand/dastyor_logo.dart';





class LanguageSelectScreen extends StatefulWidget {
  const LanguageSelectScreen({super.key});

  @override
  State<LanguageSelectScreen> createState() => _LanguageSelectScreenState();
}

class _LanguageSelectScreenState extends State<LanguageSelectScreen> {
  static const _options = [
    (locale: Locale('ru'), label: 'Русский'),
    (locale: Locale('en'), label: 'English'),
    (locale: Locale('tg'), label: 'Тоҷикӣ'),
  ];

  Locale _selected = const Locale('ru');
  bool _saving = false;

  Future<void> _continue() async {
    setState(() => _saving = true);
    await context.read<LocaleProvider>().setLocale(_selected);
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(),
              const DastyorMark(height: 56),
              const SizedBox(height: 16),
              Text(
                t.chooseLanguageTitle,
                style: Theme.of(context)
                    .textTheme
                    .headlineSmall
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              Text(t.chooseLanguageSubtitle, style: const TextStyle(color: AppColors.inkSoft)),
              const SizedBox(height: 32),
              for (final option in _options) ...[
                _LanguageTile(
                  label: option.label,
                  selected: _selected.languageCode == option.locale.languageCode,
                  onTap: () => setState(() => _selected = option.locale),
                ),
                const SizedBox(height: 12),
              ],
              const Spacer(),
              ElevatedButton(
                onPressed: _saving ? null : _continue,
                child: Text(t.continueBtn),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}

class _LanguageTile extends StatelessWidget {
  const _LanguageTile({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        decoration: BoxDecoration(
          color: selected ? AppColors.brandSoft : AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
              color: selected ? AppColors.brand : AppColors.border, width: selected ? 1.8 : 1.2),
        ),
        child: Row(
          children: [
            Expanded(
                child:
                    Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600))),
            if (selected) const Icon(Icons.check_circle_rounded, color: AppColors.brand),
          ],
        ),
      ),
    );
  }
}
