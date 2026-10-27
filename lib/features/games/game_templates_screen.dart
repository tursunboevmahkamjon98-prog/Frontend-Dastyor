import 'package:flutter/material.dart';
import 'magicbox/magicbox_setup_screen.dart';
import 'seclab/seclab_setup_screen.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../widgets/ui/ui.dart';












class GameTemplatesScreen extends StatelessWidget {
  const GameTemplatesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(t.gameTemplatesTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          Text(
            t.gameTemplatesPrompt,
            style: const TextStyle(
                fontSize: 13, color: Colors.black54, height: 1.4),
          ),
          const SizedBox(height: 18),
          _TemplateCard(
            emoji: '🎁',
            title: t.gameMagicBoxName,
            description: t.gameMagicBoxDesc,
            preview: const _MagicBoxPreview(),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const MagicBoxSetupScreen()),
            ),
          ),
          const SizedBox(height: 16),
          _TemplateCard(
            emoji: '🧪',
            title: t.gameSecLabName,
            description: t.gameSecLabDesc,
            preview: const _SecLabPreview(),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const SecLabSetupScreen()),
            ),
          ),
          const SizedBox(height: 16),
          
          Container(
            height: 110,
            decoration: BoxDecoration(
              color: AppColors.surfaceMuted,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: AppColors.borderStrong,
                width: 2,
                strokeAlign: BorderSide.strokeAlignInside,
              ),
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('✨', style: TextStyle(fontSize: 24)),
                  const SizedBox(height: 6),
                  Text(t.gameMoreSoonTitle,
                      style: const TextStyle(
                          fontWeight: FontWeight.w700, color: Colors.black54)),
                  const SizedBox(height: 2),
                  Text(t.gameMoreSoonDesc,
                      style: const TextStyle(
                          fontSize: 11, color: Colors.black38)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TemplateCard extends StatelessWidget {
  const _TemplateCard({
    required this.emoji,
    required this.title,
    required this.description,
    required this.preview,
    required this.onTap,
  });

  final String emoji;
  final String title;
  final String description;
  final Widget preview;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return UiCard(
      onTap: onTap,
      padding: EdgeInsets.zero,
      radius: Ui.r3xl,
      shadow: Ui.md,
      child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            
            
            ClipRRect(
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(Ui.r3xl - 1),
              ),
              child: SizedBox(height: 150, child: preview),
            ),
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(children: [
                    Text(emoji, style: const TextStyle(fontSize: 20)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(title,
                          style: Ui.h2.copyWith(color: AppColors.ink)),
                    ),
                  ]),
                  const SizedBox(height: 6),
                  Text(description,
                      style: Ui.body.copyWith(color: AppColors.inkSoft)),
                  const SizedBox(height: 14),
                  
                  
                  Container(
                    height: 42,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: AppColors.warning,
                      borderRadius: BorderRadius.circular(Ui.rXl),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.check_rounded,
                            color: AppColors.white, size: 18),
                        const SizedBox(width: 6),
                        Text(AppLocalizations.of(context).gameSelect,
                            style: const TextStyle(
                                color: AppColors.white,
                                fontWeight: FontWeight.w600,
                                fontSize: 14)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
    );
  }
}



class _MagicBoxPreview extends StatelessWidget {
  const _MagicBoxPreview();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF3B1D7A), Color(0xFF1B0F3A)],
        ),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          const Positioned(top: 14, child: Text('🎩', style: TextStyle(fontSize: 30))),
          Positioned(
            bottom: 18,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(
                3,
                (i) => Container(
                  margin: const EdgeInsets.symmetric(horizontal: 7),
                  width: 44,
                  height: 46,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFFC084FC), Color(0xFF6B21A8)],
                    ),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF4C1D95), width: 2),
                    boxShadow: const [
                      BoxShadow(color: Color(0x66A855F7), blurRadius: 14, spreadRadius: 1),
                    ],
                  ),
                  child: const Center(
                    child: Text('?',
                        style: TextStyle(
                            color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}


class _SecLabPreview extends StatelessWidget {
  const _SecLabPreview();

  @override
  Widget build(BuildContext context) {
    const liquids = [Color(0xFF38BDF8), Color(0xFFA855F7), Color(0xFF34D399), Color(0xFFFB923C)];
    return Container(
      decoration: const BoxDecoration(
        gradient: RadialGradient(
          center: Alignment(0, -1),
          radius: 1.2,
          colors: [Color(0xFF1E3A5F), Color(0xFF0A1226), Color(0xFF070C1A)],
        ),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          const Positioned(right: 16, top: 14, child: Text('⚗️', style: TextStyle(fontSize: 18))),
          const Positioned(left: 16, top: 20, child: Text('🔬', style: TextStyle(fontSize: 16))),
          Positioned(
            bottom: 26,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final c in liquids)
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 5),
                    width: 22,
                    height: 34,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.14),
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(3),
                        bottom: Radius.circular(8),
                      ),
                      border: Border.all(color: Colors.white54),
                      boxShadow: [BoxShadow(color: c.withValues(alpha: 0.6), blurRadius: 10)],
                    ),
                    child: Align(
                      alignment: Alignment.bottomCenter,
                      child: Container(
                        height: 20,
                        decoration: BoxDecoration(
                          color: c,
                          borderRadius: const BorderRadius.vertical(bottom: Radius.circular(7)),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: Container(height: 18, color: const Color(0xFF0C1526)),
          ),
        ],
      ),
    );
  }
}
