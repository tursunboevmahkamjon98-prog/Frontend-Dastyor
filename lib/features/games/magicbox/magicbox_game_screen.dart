import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import '../../../l10n/gen/app_localizations.dart';
import '../../../models/quiz_question.dart';
import '../widgets/game_hud.dart';
import '../widgets/game_result_screen.dart';
import 'magicbox_logic.dart';

const _accent = Color(0xFFA855F7);





enum _Phase { reveal, inserting, countdown, shuffling, choosing, opening, question, feedback, result }







class MagicBoxGameScreen extends StatefulWidget {
  const MagicBoxGameScreen({super.key, required this.questions, required this.onExit});

  final List<QuizQuestion> questions;
  final VoidCallback onExit;

  @override
  State<MagicBoxGameScreen> createState() => _MagicBoxGameScreenState();
}

class _MagicBoxGameScreenState extends State<MagicBoxGameScreen> with TickerProviderStateMixin {
  final _rng = Random();
  final _timers = <Timer>[];

  late int _totalRounds;
  int _round = 0;
  _Phase _phase = _Phase.reveal;

  List<BoxState> _boxes = [];
  List<QuizQuestion> _roundQuestions = [];
  int _countdown = 3;
  int? _pickedBoxId;
  int? _pickedAnswer;
  int _swapMs = 640;

  int _score = 0;
  int _lives = kStartingLives;
  int _streak = 0;
  int _correct = 0;
  int _wrong = 0;

  late final AnimationController _idle =
      AnimationController(vsync: this, duration: const Duration(seconds: 3))..repeat(reverse: true);

  @override
  void initState() {
    super.initState();
    _totalRounds = widget.questions.length ~/ kBoxCount;
    if (_totalRounds < 1) _totalRounds = 1;
    _beginRound(0);
  }

  @override
  void dispose() {
    
    
    
    for (final t in _timers) {
      t.cancel();
    }
    _idle.dispose();
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

  void _clearTimers() {
    for (final t in _timers) {
      t.cancel();
    }
    _timers.clear();
  }

  void _beginRound(int index) {
    _clearTimers();
    final cfg = roundConfig(index);
    _swapMs = cfg.swapMs;

    
    
    
    final slice = widget.questions.sublist(
      index * kBoxCount,
      min((index + 1) * kBoxCount, widget.questions.length),
    );
    final order = randomOrder(kBoxCount, _rng);

    setState(() {
      _round = index;
      _roundQuestions = slice;
      _boxes = [
        for (var i = 0; i < kBoxCount; i++)
          BoxState(id: i, position: i, questionIndex: order[i]),
      ];
      _pickedBoxId = null;
      _pickedAnswer = null;
      _phase = _Phase.reveal;
    });

    
    _later(const Duration(milliseconds: 2600), () {
      setState(() => _phase = _Phase.inserting);

      
      _later(const Duration(milliseconds: 1500), () {
        setState(() {
          _phase = _Phase.countdown;
          _countdown = 3;
        });

        for (var i = 1; i <= 2; i++) {
          _later(Duration(milliseconds: 620 * i), () => setState(() => _countdown = 3 - i));
        }

        
        
        _later(const Duration(milliseconds: 1860), () {
          setState(() {
            _countdown = 0;
            _phase = _Phase.shuffling;
          });
          final plan = planShuffle(cfg.swaps, _rng);
          for (var i = 0; i < plan.length; i++) {
            _later(Duration(milliseconds: cfg.swapMs * i), () {
              setState(() => applySwap(_boxes, plan[i]));
            });
          }
          _later(Duration(milliseconds: cfg.swapMs * plan.length + 160), () {
            setState(() => _phase = _Phase.choosing);
          });
        });
      });
    });
  }

  void _pickBox(int boxId) {
    if (_phase != _Phase.choosing) return;
    setState(() {
      _pickedBoxId = boxId;
      _phase = _Phase.opening;
    });
    _later(const Duration(milliseconds: 900), () {
      setState(() => _phase = _Phase.question);
    });
  }

  QuizQuestion? get _activeQuestion {
    if (_pickedBoxId == null) return null;
    final box = _boxes.firstWhere((b) => b.id == _pickedBoxId);
    if (box.questionIndex >= _roundQuestions.length) return null;
    return _roundQuestions[box.questionIndex];
  }

  void _answer(int index) {
    if (_phase != _Phase.question || _pickedAnswer != null) return;
    final q = _activeQuestion;
    if (q == null) return;
    final correct = index == q.correctIndex;

    setState(() {
      _pickedAnswer = index;
      if (correct) {
        _streak++;
        _score += scoreFor(_streak);
        _correct++;
      } else {
        _streak = 0;
        _wrong++;
        _lives--;
      }
    });

    _later(const Duration(milliseconds: 900), () {
      if (correct) {
        _next();
      } else {
        setState(() => _phase = _Phase.feedback);
      }
    });
  }

  void _next() {
    if (_lives <= 0 || _round + 1 >= _totalRounds) {
      setState(() => _phase = _Phase.result);
      return;
    }
    _beginRound(_round + 1);
  }

  void _restart() {
    setState(() {
      _score = 0;
      _lives = kStartingLives;
      _streak = 0;
      _correct = 0;
      _wrong = 0;
    });
    _beginRound(0);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1B0F3A),
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -0.7),
            radius: 1.4,
            colors: [Color(0xFF4C1D95), Color(0xFF2E1065), Color(0xFF1B0F3A)],
          ),
        ),
        child: _phase == _Phase.result
            ? GameResultScreen(
                accent: _accent,
                score: _score,
                correct: _correct,
                wrong: _wrong,
                total: _correct + _wrong,
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
                            totalRounds: _totalRounds,
                            score: _score,
                            lives: _lives,
                            startingLives: kStartingLives,
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
                    if (_phase == _Phase.feedback && _activeQuestion != null)
                      Positioned.fill(
                        child: ExplanationCard(
                          question: _activeQuestion!,
                          picked: _pickedAnswer,
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
    
    
    if (_phase == _Phase.reveal) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(AppLocalizations.of(context).gameMemorize,
                textAlign: TextAlign.center,
                style: TextStyle(
                    color: Color(0xFFFCD34D), fontSize: 16, fontWeight: FontWeight.w900)),
            const SizedBox(height: 16),
            for (var i = 0; i < _roundQuestions.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.95),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: const Color(0xFFFCD34D), width: 2),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(AppLocalizations.of(context).gameQuestionLetter(String.fromCharCode(65 + i)),
                          style: const TextStyle(
                              fontSize: 9,
                              letterSpacing: 1.4,
                              fontWeight: FontWeight.w900,
                              color: Color(0xFFC026D3))),
                      const SizedBox(height: 4),
                      Text(_roundQuestions[i].question,
                          style: const TextStyle(
                              fontSize: 13.5,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF3B0764),
                              height: 1.3)),
                    ],
                  ),
                ),
              ),
          ],
        ),
      );
    }

    final showAnswers = _phase == _Phase.question && _activeQuestion != null;

    return Column(
      children: [
        
        SizedBox(
          height: 46,
          child: Center(
            child: _banner(),
          ),
        ),
        
        
        
        if (showAnswers) ...[
          SizedBox(height: 168, child: _buildBoxRow()),
          Expanded(child: _buildAnswers(_activeQuestion!)),
        ] else
          Expanded(child: Center(child: SizedBox(height: 168, child: _buildBoxRow()))),
      ],
    );
  }

  Widget _banner() {
    switch (_phase) {
      case _Phase.inserting:
        return _bannerChip(AppLocalizations.of(context).gamePlacingQuestions);
      case _Phase.countdown:
        
        
        return Row(mainAxisSize: MainAxisSize.min, children: [
          _bannerChip(AppLocalizations.of(context).gameAttention),
          const SizedBox(width: 10),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 250),
            transitionBuilder: (child, anim) =>
                ScaleTransition(scale: anim, child: FadeTransition(opacity: anim, child: child)),
            child: Text(
              _countdown > 0 ? '$_countdown' : AppLocalizations.of(context).gameGo,
              key: ValueKey(_countdown),
              style: const TextStyle(
                  color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900),
            ),
          ),
        ]);
      case _Phase.shuffling:
        return _bannerChip(AppLocalizations.of(context).gameShuffling);
      case _Phase.choosing:
        return _bannerChip(AppLocalizations.of(context).gamePickBox);
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _bannerChip(String text) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.4),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: _accent.withValues(alpha: 0.4)),
        ),
        child: Text(text,
            style: const TextStyle(
                color: Color(0xFFFCD34D), fontSize: 13, fontWeight: FontWeight.w900)),
      );

  Widget _buildBoxRow() {
    return LayoutBuilder(builder: (context, c) {
      const boxW = 84.0;
      final slotW = ((c.maxWidth - 24) / kBoxCount).clamp(90.0, 130.0);
      final rowW = slotW * kBoxCount;
      final left0 = (c.maxWidth - rowW) / 2 + (slotW - boxW) / 2;

      return Stack(
        children: [
          for (final box in _boxes)
            AnimatedPositioned(
              key: ValueKey(box.id),
              duration: Duration(milliseconds: _phase == _Phase.shuffling ? _swapMs : 300),
              curve: Curves.easeInOutCubic,
              left: left0 + box.position * slotW,
              bottom: 6,
              child: _MagicBoxWidget(
                width: boxW,
                idle: _idle,
                dimmed: _pickedBoxId != null && _pickedBoxId != box.id,
                opened: _pickedBoxId == box.id &&
                    (_phase == _Phase.opening ||
                        _phase == _Phase.question ||
                        _phase == _Phase.feedback),
                lidUp: _phase == _Phase.inserting,
                clickable: _phase == _Phase.choosing,
                label: AppLocalizations.of(context).gameBoxNumber(box.position + 1),
                onTap: () => _pickBox(box.id),
              ),
            ),
        ],
      );
    });
  }

  Widget _buildAnswers(QuizQuestion q) {
    const letters = ['A', 'B', 'C', 'D'];
    final revealed = _pickedAnswer != null;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(14, 6, 14, 18),
      child: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.96),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0xFFFCD34D), width: 2),
            ),
            child: Text(q.question,
                textAlign: TextAlign.center,
                style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                    color: Color(0xFF3B0764),
                    height: 1.3)),
          ),
          const SizedBox(height: 12),
          for (var i = 0; i < q.options.length; i++)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: _AnswerButton(
                letter: letters[i],
                text: q.options[i],
                state: !revealed
                    ? _AnswerVisual.idle
                    : i == q.correctIndex
                        ? _AnswerVisual.correct
                        : (_pickedAnswer == i ? _AnswerVisual.wrong : _AnswerVisual.faded),
                onTap: revealed ? null : () => _answer(i),
              ),
            ),
        ],
      ),
    );
  }
}

enum _AnswerVisual { idle, correct, wrong, faded }

class _AnswerButton extends StatelessWidget {
  const _AnswerButton({
    required this.letter,
    required this.text,
    required this.state,
    required this.onTap,
  });

  final String letter;
  final String text;
  final _AnswerVisual state;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final (bg, border, fg) = switch (state) {
      _AnswerVisual.correct => (const Color(0xFFD1FAE5), const Color(0xFF10B981), const Color(0xFF065F46)),
      _AnswerVisual.wrong => (const Color(0xFFFEE2E2), const Color(0xFFEF4444), const Color(0xFF991B1B)),
      _AnswerVisual.faded => (Colors.white70, const Color(0xFFE9D5FF), const Color(0xFF6B21A8)),
      _AnswerVisual.idle => (Colors.white, const Color(0xFFC4B5FD), const Color(0xFF3B0764)),
    };

    return Opacity(
      opacity: state == _AnswerVisual.faded ? 0.6 : 1,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: border, width: 2),
          ),
          child: Row(
            children: [
              Container(
                width: 30,
                height: 30,
                alignment: Alignment.center,
                decoration: BoxDecoration(color: border, borderRadius: BorderRadius.circular(9)),
                child: Text(letter,
                    style: const TextStyle(
                        color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13)),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(text,
                    style: TextStyle(
                        color: fg, fontWeight: FontWeight.w700, fontSize: 13.5, height: 1.25)),
              ),
              
              
              if (state == _AnswerVisual.correct)
                const Icon(Icons.check_rounded, color: Color(0xFF059669), size: 20),
              if (state == _AnswerVisual.wrong)
                const Icon(Icons.close_rounded, color: Color(0xFFDC2626), size: 20),
            ],
          ),
        ),
      ),
    );
  }
}




class _MagicBoxWidget extends StatelessWidget {
  const _MagicBoxWidget({
    required this.width,
    required this.idle,
    required this.dimmed,
    required this.opened,
    required this.lidUp,
    required this.clickable,
    required this.label,
    required this.onTap,
  });

  final double width;
  final AnimationController idle;
  final bool dimmed;
  final bool opened;
  final bool lidUp;
  final bool clickable;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final lidOff = opened || lidUp;

    return GestureDetector(
      onTap: clickable ? onTap : null,
      child: AnimatedOpacity(
        opacity: dimmed ? 0.35 : 1,
        duration: const Duration(milliseconds: 350),
        child: AnimatedBuilder(
          animation: idle,
          builder: (_, __) {
            
            
            
            final bob = sin(idle.value * pi) * 5;
            return Transform.translate(
              offset: Offset(0, -bob),
              child: SizedBox(
                width: width,
                height: 152,
                child: Stack(
                  alignment: Alignment.bottomCenter,
                  children: [
                    
                    Positioned(
                      bottom: 22,
                      child: Container(
                        width: width - 8,
                        height: 88,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(20),
                          boxShadow: [
                            BoxShadow(
                                color: _accent.withValues(alpha: 0.55),
                                blurRadius: 26,
                                spreadRadius: 2),
                          ],
                        ),
                      ),
                    ),
                    
                    Positioned(
                      bottom: 18,
                      child: Container(
                        width: width,
                        height: 84,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [Color(0xFFC084FC), Color(0xFF9333EA), Color(0xFF6B21A8)],
                          ),
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(6),
                            bottom: Radius.circular(16),
                          ),
                          border: Border.all(color: const Color(0xFF4C1D95), width: 2),
                        ),
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            
                            Container(width: 14, color: const Color(0xFFFDE68A)),
                            const Text('?',
                                style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 30,
                                    fontWeight: FontWeight.w900)),
                          ],
                        ),
                      ),
                    ),
                    
                    AnimatedPositioned(
                      duration: const Duration(milliseconds: 450),
                      curve: Curves.easeOutBack,
                      bottom: lidOff ? 114 : 96,
                      child: AnimatedRotation(
                        turns: lidOff ? -0.08 : 0,
                        duration: const Duration(milliseconds: 450),
                        child: Container(
                          width: width + 8,
                          height: 22,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [Color(0xFFD8B4FE), Color(0xFF7E22CE)],
                            ),
                            borderRadius: BorderRadius.circular(7),
                            border: Border.all(color: const Color(0xFF581C87), width: 2),
                          ),
                        ),
                      ),
                    ),
                    
                    
                    
                    
                    if (clickable)
                      Positioned(
                        bottom: 0,
                        child: Text(label,
                            style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 10,
                                fontWeight: FontWeight.w700)),
                      ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
