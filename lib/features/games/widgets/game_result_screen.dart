import 'package:flutter/material.dart';
import '../../../l10n/gen/app_localizations.dart';




class GameResultScreen extends StatefulWidget {
  const GameResultScreen({
    super.key,
    required this.accent,
    required this.score,
    required this.correct,
    required this.wrong,
    required this.total,
    required this.outOfLives,
    required this.onReplay,
    required this.onExit,
  });

  final Color accent;
  final int score;
  final int correct;
  final int wrong;
  final int total;

  
  
  
  final bool outOfLives;
  final VoidCallback onReplay;
  final VoidCallback onExit;

  @override
  State<GameResultScreen> createState() => _GameResultScreenState();
}

class _GameResultScreenState extends State<GameResultScreen> {
  int _shown = 0;

  @override
  void initState() {
    super.initState();
    _revealNext();
  }

  
  
  
  void _revealNext() {
    if (!mounted || _shown >= 4) return;
    Future.delayed(const Duration(milliseconds: 420), () {
      if (!mounted) return;
      setState(() => _shown++);
      _revealNext();
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final celebrating = !widget.outOfLives || widget.correct > 0;
    final accuracy = widget.total == 0 ? 0 : (widget.correct * 100 ~/ widget.total);

    final stats = [
      (icon: Icons.star_rounded, label: t.gameScore, value: '${widget.score}', tint: const Color(0xFFFCD34D)),
      (icon: Icons.check_rounded, label: t.gameCorrectCount, value: '${widget.correct}', tint: const Color(0xFF6EE7B7)),
      (icon: Icons.close_rounded, label: t.gameWrongCount, value: '${widget.wrong}', tint: const Color(0xFFFCA5A5)),
      (icon: Icons.percent_rounded, label: t.gameAccuracy, value: '$accuracy%', tint: widget.accent),
    ];

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
        child: Column(
          children: [
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: 1),
              duration: const Duration(milliseconds: 700),
              curve: Curves.elasticOut,
              builder: (_, v, child) => Transform.scale(scale: v, child: child),
              child: Text(celebrating ? '🏆' : '🧪', style: const TextStyle(fontSize: 64)),
            ),
            const SizedBox(height: 10),
            Text(
              widget.outOfLives ? t.gameOver : t.gameCongrats,
              textAlign: TextAlign.center,
              style: const TextStyle(
                  color: Colors.white, fontSize: 24, fontWeight: FontWeight.w900),
            ),
            if (!widget.outOfLives) ...[
              const SizedBox(height: 6),
              Text(t.gameFinishedSuccess,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      color: widget.accent, fontSize: 13, fontWeight: FontWeight.w700)),
            ],
            const SizedBox(height: 22),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              childAspectRatio: 1.5,
              children: [
                for (var i = 0; i < stats.length; i++)
                  AnimatedOpacity(
                    opacity: i < _shown ? 1 : 0,
                    duration: const Duration(milliseconds: 380),
                    child: AnimatedSlide(
                      offset: i < _shown ? Offset.zero : const Offset(0, 0.25),
                      duration: const Duration(milliseconds: 380),
                      curve: Curves.easeOutCubic,
                      child: _StatCard(
                        icon: stats[i].icon,
                        label: stats[i].label,
                        value: stats[i].value,
                        tint: stats[i].tint,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 24),
            _ResultButton(
              label: t.gamePlayAgain,
              icon: Icons.refresh_rounded,
              filled: true,
              accent: widget.accent,
              onTap: widget.onReplay,
            ),
            const SizedBox(height: 10),
            _ResultButton(
              label: t.gameBackToTemplates,
              icon: Icons.home_rounded,
              filled: false,
              accent: widget.accent,
              onTap: widget.onExit,
            ),
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.tint,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color tint;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.1), shape: BoxShape.circle),
            child: Icon(icon, size: 17, color: tint),
          ),
          const SizedBox(height: 5),
          Text(value,
              style: const TextStyle(
                  color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 2),
          Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
                color: Colors.white.withValues(alpha: 0.55),
                fontSize: 9,
                height: 1.2,
                fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _ResultButton extends StatelessWidget {
  const _ResultButton({
    required this.label,
    required this.icon,
    required this.filled,
    required this.accent,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool filled;
  final Color accent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 52,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          gradient: filled
              ? LinearGradient(colors: [accent, Color.lerp(accent, Colors.black, 0.35)!])
              : null,
          color: filled ? null : Colors.white.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(16),
          border: filled ? null : Border.all(color: Colors.white.withValues(alpha: 0.2)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Colors.white, size: 18),
            const SizedBox(width: 8),
            Text(label,
                style: const TextStyle(
                    color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14)),
          ],
        ),
      ),
    );
  }
}
