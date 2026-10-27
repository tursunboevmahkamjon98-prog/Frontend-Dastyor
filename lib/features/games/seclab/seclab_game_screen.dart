import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import '../../../l10n/gen/app_localizations.dart';
import '../../../models/quiz_question.dart';
import '../widgets/game_hud.dart';
import '../widgets/game_result_screen.dart';

const _accent = Color(0xFF38BDF8);
const _startingLives = 3;
const _pointsPerCorrect = 50;





const _liquids = [
  (liquid: Color(0xFF38BDF8), deep: Color(0xFF0369A1)),
  (liquid: Color(0xFFA855F7), deep: Color(0xFF6B21A8)),
  (liquid: Color(0xFF34D399), deep: Color(0xFF047857)),
  (liquid: Color(0xFFFB923C), deep: Color(0xFFC2410C)),
];

const _letters = ['A', 'B', 'C', 'D'];

enum _Phase { roundIntro, question, pouring, reacting, explaining, result }





class SecLabGameScreen extends StatefulWidget {
  const SecLabGameScreen({super.key, required this.questions, required this.onExit});

  final List<QuizQuestion> questions;
  final VoidCallback onExit;

  @override
  State<SecLabGameScreen> createState() => _SecLabGameScreenState();
}

class _SecLabGameScreenState extends State<SecLabGameScreen> with TickerProviderStateMixin {
  final _timers = <Timer>[];

  int _round = 0;
  _Phase _phase = _Phase.roundIntro;
  int? _picked;
  bool? _correct;

  int _score = 0;
  int _lives = _startingLives;
  int _streak = 0;
  int _correctCount = 0;
  int _wrongCount = 0;

  late final AnimationController _idle =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 2600))
        ..repeat(reverse: true);
  late final AnimationController _react =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1400));

  QuizQuestion get _q => widget.questions[_round];

  @override
  void initState() {
    super.initState();
    _beginRound(0);
  }

  @override
  void dispose() {
    for (final t in _timers) {
      t.cancel();
    }
    _idle.dispose();
    _react.dispose();
    super.dispose();
  }

  void _later(Duration d, VoidCallback fn) {
    late Timer t;
    t = Timer(d, () {
      _timers.remove(t);
      if (mounted) fn();
    });
    _timers.add(t);
  }

  void _beginRound(int index) {
    for (final t in _timers) {
      t.cancel();
    }
    _timers.clear();
    setState(() {
      _round = index;
      _picked = null;
      _correct = null;
      _phase = _Phase.roundIntro;
    });
    _later(const Duration(milliseconds: 1100), () {
      setState(() => _phase = _Phase.question);
    });
  }

  void _pick(int index) {
    if (_phase != _Phase.question) return;
    final correct = index == _q.correctIndex;
    setState(() {
      _picked = index;
      _phase = _Phase.pouring;
    });

    
    
    _later(const Duration(milliseconds: 1200), () {
      setState(() {
        _correct = correct;
        _phase = _Phase.reacting;
        if (correct) {
          _streak++;
          final combo = 1 + (_streak ~/ 3) * 0.5;
          _score += (_pointsPerCorrect * combo).round();
          _correctCount++;
        } else {
          _streak = 0;
          _wrongCount++;
          _lives--;
        }
      });
      _react.forward(from: 0);

      _later(const Duration(milliseconds: 1700), () {
        if (correct) {
          _next();
        } else {
          setState(() => _phase = _Phase.explaining);
        }
      });
    });
  }

  void _next() {
    if (_lives <= 0 || _round + 1 >= widget.questions.length) {
      setState(() => _phase = _Phase.result);
      return;
    }
    _beginRound(_round + 1);
  }

  void _restart() {
    setState(() {
      _score = 0;
      _lives = _startingLives;
      _streak = 0;
      _correctCount = 0;
      _wrongCount = 0;
    });
    _beginRound(0);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF070C1A),
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -1),
            radius: 1.3,
            colors: [Color(0xFF1E3A5F), Color(0xFF12203C), Color(0xFF070C1A)],
          ),
        ),
        child: _phase == _Phase.result
            ? GameResultScreen(
                accent: _accent,
                score: _score,
                correct: _correctCount,
                wrong: _wrongCount,
                total: _correctCount + _wrongCount,
                outOfLives: _lives <= 0,
                onReplay: _restart,
                onExit: widget.onExit,
              )
            : SafeArea(
                child: Stack(
                  children: [
                    Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
                          child: GameHud(
                            round: _round,
                            totalRounds: widget.questions.length,
                            score: _score,
                            lives: _lives,
                            startingLives: _startingLives,
                            accent: _accent,
                          ),
                        ),
                        Expanded(child: _buildStage()),
                      ],
                    ),
                    Positioned(
                      left: 4,
                      top: 4,
                      child: IconButton(
                        icon: const Icon(Icons.close_rounded, color: Colors.white70),
                        onPressed: widget.onExit,
                      ),
                    ),
                    if (_phase == _Phase.explaining)
                      Positioned.fill(
                        child: ExplanationCard(
                          question: _q,
                          picked: _picked,
                          accent: _accent,
                          onContinue: _next,
                        ),
                      ),
                  ],
                ),
              ),
      ),
    );
  }

  Widget _buildStage() {
    if (_phase == _Phase.roundIntro) {
      return Center(
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.8, end: 1),
          duration: const Duration(milliseconds: 500),
          curve: Curves.easeOutBack,
          builder: (_, v, child) => Transform.scale(scale: v, child: child),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.45),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: _accent.withValues(alpha: 0.5)),
            ),
            child: Text(AppLocalizations.of(context).gameNewExperiment,
                style: TextStyle(
                    color: Color(0xFFBAE6FD), fontSize: 22, fontWeight: FontWeight.w900)),
          ),
        ),
      );
    }

    return Column(
      children: [
        
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 6, 14, 0),
          child: Container(
            width: double.infinity,
            constraints: const BoxConstraints(maxHeight: 150),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
            ),
            child: SingleChildScrollView(
              child: Column(
                children: [
                  Text(AppLocalizations.of(context).gameQuestion,
                      style: TextStyle(
                          fontSize: 9,
                          letterSpacing: 2,
                          fontWeight: FontWeight.w900,
                          color: _accent.withValues(alpha: 0.85))),
                  const SizedBox(height: 5),
                  Text(_q.question,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14.5,
                          fontWeight: FontWeight.w900,
                          height: 1.3)),
                ],
              ),
            ),
          ),
        ),

        
        Expanded(
          child: Center(
            child: AnimatedBuilder(
              animation: _react,
              builder: (_, __) => _Flask(
                reacting: _phase == _Phase.reacting || _phase == _Phase.explaining,
                success: _correct == true,
                progress: _react.value,
                tint: _picked == null
                    ? _accent
                    : _liquids[_picked! % _liquids.length].liquid,
              ),
            ),
          ),
        ),

        if (_phase == _Phase.question)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text(AppLocalizations.of(context).gamePickReagent,
                style: const TextStyle(
                    color: Color(0xFFBAE6FD),
                    fontSize: 12,
                    letterSpacing: 1.4,
                    fontWeight: FontWeight.w900)),
          ),

        if (_phase == _Phase.reacting && _correct == true)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text(AppLocalizations.of(context).gameCorrectCheer,
                style: const TextStyle(
                    color: Color(0xFF6EE7B7), fontSize: 15, fontWeight: FontWeight.w900)),
          ),

        
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 0, 8, 14),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              for (var i = 0; i < _q.options.length; i++)
                Flexible(
                  child: _Bottle(
                    index: i,
                    label: _q.options[i],
                    idle: _idle,
                    interactive: _phase == _Phase.question,
                    flying: _picked == i && _phase == _Phase.pouring,
                    dimmed: _picked != null && _picked != i && _phase != _Phase.question,
                    reveal: (_phase == _Phase.reacting || _phase == _Phase.explaining)
                        ? (i == _q.correctIndex
                            ? _Reveal.correct
                            : (_picked == i ? _Reveal.wrong : _Reveal.none))
                        : _Reveal.none,
                    onTap: () => _pick(i),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

enum _Reveal { none, correct, wrong }



class _Bottle extends StatelessWidget {
  const _Bottle({
    required this.index,
    required this.label,
    required this.idle,
    required this.interactive,
    required this.flying,
    required this.dimmed,
    required this.reveal,
    required this.onTap,
  });

  final int index;
  final String label;
  final AnimationController idle;
  final bool interactive;
  final bool flying;
  final bool dimmed;
  final _Reveal reveal;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = _liquids[index % _liquids.length];
    final glow = switch (reveal) {
      _Reveal.correct => const Color(0xFF34D399),
      _Reveal.wrong => const Color(0xFFF87171),
      _Reveal.none => c.liquid,
    };

    return GestureDetector(
      onTap: interactive ? onTap : null,
      child: AnimatedOpacity(
        opacity: dimmed ? 0.3 : 1,
        duration: const Duration(milliseconds: 350),
        child: AnimatedSlide(
          
          offset: flying ? const Offset(0, -1.6) : Offset.zero,
          duration: const Duration(milliseconds: 1100),
          curve: Curves.easeInOutCubic,
          child: AnimatedRotation(
            turns: flying ? -0.3 : 0,
            duration: const Duration(milliseconds: 1100),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 3),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  AnimatedBuilder(
                    animation: idle,
                    builder: (_, child) => Transform.translate(
                      offset: Offset(0, -sin(idle.value * pi) * 4),
                      child: child,
                    ),
                    child: Container(
                      width: 46,
                      height: 62,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.16),
                        borderRadius: const BorderRadius.vertical(
                          top: Radius.circular(6),
                          bottom: Radius.circular(14),
                        ),
                        border: Border.all(color: Colors.white70, width: 1.5),
                        boxShadow: [
                          BoxShadow(color: glow.withValues(alpha: 0.75), blurRadius: 16),
                        ],
                      ),
                      child: Stack(
                        alignment: Alignment.bottomCenter,
                        children: [
                          
                          Container(
                            height: 38,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                                colors: [c.liquid, c.deep],
                              ),
                              borderRadius:
                                  const BorderRadius.vertical(bottom: Radius.circular(12)),
                            ),
                          ),
                          
                          Positioned(
                            top: 4,
                            right: 3,
                            child: Container(
                              width: 18,
                              height: 18,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                color: c.deep,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: Colors.white54),
                              ),
                              child: Text(_letters[index],
                                  style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 10,
                                      fontWeight: FontWeight.w900)),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  
                  
                  SizedBox(
                    height: 46,
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 3),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: switch (reveal) {
                          _Reveal.correct => const Color(0x4034D399),
                          _Reveal.wrong => const Color(0x40F87171),
                          _Reveal.none => Colors.white.withValues(alpha: 0.1),
                        },
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: switch (reveal) {
                            _Reveal.correct => const Color(0xFF6EE7B7),
                            _Reveal.wrong => const Color(0xFFFCA5A5),
                            _Reveal.none => Colors.white24,
                          },
                        ),
                      ),
                      child: Text(
                        label,
                        textAlign: TextAlign.center,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 9.5,
                            height: 1.2,
                            fontWeight: FontWeight.w800),
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




class _Flask extends StatelessWidget {
  const _Flask({
    required this.reacting,
    required this.success,
    required this.progress,
    required this.tint,
  });

  final bool reacting;
  final bool success;
  final double progress;
  final Color tint;

  @override
  Widget build(BuildContext context) {
    final glowStrength = reacting ? (success ? 0.9 : 0.35) : 0.35;
    final scale = reacting && success ? 1 + sin(progress * pi) * 0.08 : 1.0;
    final shake = reacting && !success ? sin(progress * pi * 6) * 5 : 0.0;

    return Transform.translate(
      offset: Offset(shake, 0),
      child: Transform.scale(
        scale: scale,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            
            Container(width: 20, height: 18, color: Colors.white.withValues(alpha: 0.16)),
            
            ClipPath(
              clipper: _ConeClipper(),
              child: Container(
                width: 118,
                height: 100,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.14),
                  boxShadow: [
                    BoxShadow(
                        color: (success ? const Color(0xFF34D399) : tint)
                            .withValues(alpha: glowStrength),
                        blurRadius: 40,
                        spreadRadius: 6),
                  ],
                ),
                child: Stack(
                  alignment: Alignment.bottomCenter,
                  children: [
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 700),
                      height: reacting ? 62 : 30,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [tint, tint.withValues(alpha: 0.5)],
                        ),
                      ),
                    ),
                    if (reacting && success)
                      for (var i = 0; i < 6; i++)
                        Positioned(
                          bottom: 10 + ((progress * 60 + i * 12) % 60),
                          left: 24.0 + i * 12,
                          child: Opacity(
                            opacity: (1 - progress).clamp(0.0, 1.0),
                            child: Container(
                              width: 5,
                              height: 5,
                              decoration: const BoxDecoration(
                                  color: Colors.white70, shape: BoxShape.circle),
                            ),
                          ),
                        ),
                  ],
                ),
              ),
            ),
            Container(
              width: 90,
              height: 6,
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(4),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ConeClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) => Path()
    ..moveTo(size.width * 0.38, 0)
    ..lineTo(size.width * 0.62, 0)
    ..lineTo(size.width, size.height)
    ..lineTo(0, size.height)
    ..close();

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}
