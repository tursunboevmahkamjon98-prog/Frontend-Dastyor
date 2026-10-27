import 'package:flutter/material.dart';
import '../../../l10n/gen/app_localizations.dart';
import '../../../models/quiz_question.dart';




class GameHud extends StatelessWidget {
  const GameHud({
    super.key,
    required this.round,
    required this.totalRounds,
    required this.score,
    required this.lives,
    required this.startingLives,
    required this.accent,
    this.playerName,
  });

  final int round; 
  final int totalRounds;
  final int score;
  final int lives;
  final int startingLives;
  final Color accent;
  final String? playerName;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (playerName != null && playerName!.isNotEmpty)
          _Chip(
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              CircleAvatar(
                radius: 12,
                backgroundColor: accent,
                child: Text(
                  playerName!.trim().characters.first.toUpperCase(),
                  style: const TextStyle(
                      color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900),
                ),
              ),
            ]),
          ),
        const Spacer(),
        _Chip(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(AppLocalizations.of(context).gameRound,
                style: TextStyle(
                    fontSize: 8,
                    letterSpacing: 1.1,
                    fontWeight: FontWeight.w800,
                    color: accent.withValues(alpha: 0.8))),
            Text('${round + 1} / $totalRounds',
                style: const TextStyle(
                    color: Colors.white, fontSize: 13, fontWeight: FontWeight.w900)),
          ]),
        ),
        const Spacer(),
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            _Chip(
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.star_rounded, size: 15, color: Color(0xFFFCD34D)),
                const SizedBox(width: 4),
                
                TweenAnimationBuilder<double>(
                  key: ValueKey(score),
                  tween: Tween(begin: 1.35, end: 1),
                  duration: const Duration(milliseconds: 380),
                  curve: Curves.easeOutBack,
                  builder: (_, v, child) => Transform.scale(scale: v, child: child),
                  child: Text('$score',
                      style: const TextStyle(
                          color: Colors.white, fontSize: 13, fontWeight: FontWeight.w900)),
                ),
              ]),
            ),
            const SizedBox(height: 5),
            _Chip(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (var i = 0; i < startingLives; i++)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 1),
                      child: AnimatedScale(
                        scale: i < lives ? 1 : 0.75,
                        duration: const Duration(milliseconds: 350),
                        child: Icon(
                          i < lives ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                          size: 13,
                          color: i < lives
                              ? const Color(0xFFFB7185)
                              : Colors.white.withValues(alpha: 0.25),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.child, this.padding});
  final Widget child;
  final EdgeInsets? padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding ?? const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.35),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
      ),
      child: child,
    );
  }
}




class ExplanationCard extends StatelessWidget {
  const ExplanationCard({
    super.key,
    required this.question,
    required this.picked,
    required this.accent,
    required this.onContinue,
  });

  final QuizQuestion question;
  final int? picked;
  final Color accent;
  final VoidCallback onContinue;

  static const _letters = ['A', 'B', 'C', 'D'];

  @override
  Widget build(BuildContext context) {
    final correctText = question.options[question.correctIndex];
    final pickedText = picked != null ? question.options[picked!] : null;

    return Container(
      color: const Color(0xFF070C1A).withValues(alpha: 0.82),
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: 0.9, end: 1),
            duration: const Duration(milliseconds: 380),
            curve: Curves.easeOutBack,
            builder: (_, v, child) => Transform.scale(scale: v, child: child),
            child: Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Color(0xFF16233F), Color(0xFF0C1526)],
                ),
                borderRadius: BorderRadius.circular(26),
                border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
                boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 40)],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('❌', style: TextStyle(fontSize: 30)),
                  const SizedBox(height: 6),
                  Text(AppLocalizations.of(context).gameWrongAnswer,
                      style: const TextStyle(
                          color: Color(0xFFFDA4AF),
                          fontSize: 20,
                          fontWeight: FontWeight.w900)),
                  const SizedBox(height: 14),
                  if (pickedText != null)
                    _Row(
                      title: AppLocalizations.of(context).gameYourAnswer,
                      text: '${_letters[picked!]}  $pickedText',
                      color: const Color(0xFFFB7185),
                    ),
                  if (pickedText != null) const SizedBox(height: 8),
                  _Row(
                    title: AppLocalizations.of(context).gameCorrectAnswer,
                    text: '${_letters[question.correctIndex]}  $correctText',
                    color: const Color(0xFF34D399),
                  ),
                  
                  
                  
                  if (question.explanation.trim().isNotEmpty) ...[
                    const SizedBox(height: 8),
                    _Row(
                      title: AppLocalizations.of(context).gameWhyCorrect,
                      text: question.explanation,
                      color: const Color(0xFFFCD34D),
                    ),
                  ],
                  const SizedBox(height: 18),
                  GestureDetector(
                    onTap: onContinue,
                    child: Container(
                      height: 50,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                            colors: [accent, Color.lerp(accent, Colors.black, 0.35)!]),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(AppLocalizations.of(context).gameContinue,
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w900,
                                  fontSize: 15)),
                          const SizedBox(width: 6),
                          const Icon(Icons.arrow_forward_rounded,
                              color: Colors.white, size: 18),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({required this.title, required this.text, required this.color});
  final String title;
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: TextStyle(
                  fontSize: 9,
                  letterSpacing: 1.1,
                  fontWeight: FontWeight.w900,
                  color: color.withValues(alpha: 0.9))),
          const SizedBox(height: 3),
          Text(text,
              style: const TextStyle(
                  color: Colors.white, fontSize: 13, fontWeight: FontWeight.w700, height: 1.35)),
        ],
      ),
    );
  }
}
