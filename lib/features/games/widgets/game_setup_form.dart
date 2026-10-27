import 'package:flutter/material.dart';
import '../../../l10n/gen/app_localizations.dart';
import '../../../models/quiz_question.dart';
import '../../../services/games_service.dart';

const kSubjects = [
  'Математика',
  'Химия',
  'Физика',
  'Биология',
  'География',
  'Таърих',
  'Информатика',
  'Забони тоҷикӣ',
  'Забони англисӣ',
];

const kGrades = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'];





const kLevels = ['Лёгкий', 'Средний', 'Сложный'];










class GameSetupForm extends StatefulWidget {
  const GameSetupForm({
    super.key,
    required this.title,
    required this.subtitle,
    required this.startLabel,
    required this.accent,
    required this.onReady,
    this.questionsPerRound = 1,
    this.roundChoices = const [5, 10, 15],
    this.defaultSubject,
    this.roundsLabel,
  });

  final String title;
  final String subtitle;
  final String startLabel;
  final Color accent;
  final int questionsPerRound;
  final List<int> roundChoices;
  final String? defaultSubject;
  
  
  final String? roundsLabel;

  
  final void Function(List<QuizQuestion> questions) onReady;

  @override
  State<GameSetupForm> createState() => _GameSetupFormState();
}

class _GameSetupFormState extends State<GameSetupForm> {
  final _service = GamesService();
  late String _subject = widget.defaultSubject ?? kSubjects.first;
  final _topic = TextEditingController();
  String _grade = '8';
  String _level = 'Средний';
  late int _rounds = widget.roundChoices[widget.roundChoices.length ~/ 2];
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _topic.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    final topic = _topic.text.trim();
    if (topic.isEmpty || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final questions = await _service.generateQuizSet(
        topic: topic,
        subject: _subject,
        grade: _grade,
        level: _level,
        count: _rounds * widget.questionsPerRound,
      );
      if (!mounted) return;
      if (questions.isEmpty) {
        setState(() {
          _busy = false;
          _error = AppLocalizations.of(context).gameNoQuestions;
        });
        return;
      }
      widget.onReady(questions);
      if (mounted) setState(() => _busy = false);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = AppLocalizations.of(context).errorGeneric;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    if (_busy && _error == null) {
      return _BrewingView(accent: widget.accent);
    }

    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: [
          Text(
            widget.title,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 26,
              fontWeight: FontWeight.w900,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            widget.subtitle,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: widget.accent),
          ),
          const SizedBox(height: 18),
          _GlassPanel(
            children: [
              _label(t.subjectLabel),
              _Dropdown(
                value: _subject,
                items: kSubjects,
                onChanged: (v) => setState(() => _subject = v),
              ),
              const SizedBox(height: 12),
              _label(t.topicLabel),
              TextField(
                controller: _topic,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                decoration: _fieldDecoration(t.gameTopicHint),
              ),
              const SizedBox(height: 12),
              _label(t.gradeLabel),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final g in kGrades)
                    _Pill(
                      label: g,
                      active: _grade == g,
                      accent: widget.accent,
                      square: true,
                      onTap: () => setState(() => _grade = g),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              _label(t.levelLabel),
              Row(
                children: [
                  for (final l in kLevels) ...[
                    Expanded(
                      child: _Pill(
                        label: _levelLabel(t, l),
                        active: _level == l,
                        accent: widget.accent,
                        onTap: () => setState(() => _level = l),
                      ),
                    ),
                    if (l != kLevels.last) const SizedBox(width: 8),
                  ],
                ],
              ),
              const SizedBox(height: 12),
              _label(widget.roundsLabel ?? t.questionCountLabel),
              Row(
                children: [
                  for (final n in widget.roundChoices) ...[
                    Expanded(
                      child: _Pill(
                        label: '$n',
                        active: _rounds == n,
                        accent: widget.accent,
                        onTap: () => setState(() => _rounds = n),
                      ),
                    ),
                    if (n != widget.roundChoices.last) const SizedBox(width: 8),
                  ],
                ],
              ),
              if (widget.questionsPerRound > 1) ...[
                const SizedBox(height: 8),
                Text(
                  t.gameQuestionsPerRound(widget.questionsPerRound,
                      _rounds * widget.questionsPerRound),
                  style: TextStyle(fontSize: 11, color: widget.accent, fontWeight: FontWeight.w600),
                ),
              ],
              if (_error != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.red.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.red.withValues(alpha: 0.4)),
                  ),
                  child: Text(_error!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                          color: Color(0xFFFECACA), fontSize: 12, fontWeight: FontWeight.w700)),
                ),
              ],
            ],
          ),
          const SizedBox(height: 16),
          _BigButton(
            label: widget.startLabel,
            accent: widget.accent,
            enabled: !_busy,
            onTap: _start,
          ),
        ],
      ),
    );
  }

  Widget _label(String text) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text(
          text.toUpperCase(),
          style: TextStyle(
            fontSize: 10,
            letterSpacing: 1.2,
            fontWeight: FontWeight.w900,
            color: widget.accent,
          ),
        ),
      );

  InputDecoration _fieldDecoration(String hint) => InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.35)),
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.08),
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: widget.accent, width: 2),
        ),
      );
}



class _BrewingView extends StatefulWidget {
  const _BrewingView({required this.accent});
  final Color accent;

  @override
  State<_BrewingView> createState() => _BrewingViewState();
}

class _BrewingViewState extends State<_BrewingView> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(seconds: 2))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 140,
            height: 140,
            child: AnimatedBuilder(
              animation: _c,
              builder: (_, __) => Stack(
                alignment: Alignment.center,
                children: [
                  for (var i = 0; i < 3; i++)
                    Transform.rotate(
                      angle: (_c.value * 2 * 3.14159) + i * 2.09,
                      child: Transform.translate(
                        offset: const Offset(48, 0),
                        child: Container(
                          width: 12,
                          height: 12,
                          decoration: BoxDecoration(
                            color: [
                              const Color(0xFF38BDF8),
                              const Color(0xFFA855F7),
                              const Color(0xFF34D399),
                            ][i],
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                  color: [
                                    const Color(0xFF38BDF8),
                                    const Color(0xFFA855F7),
                                    const Color(0xFF34D399),
                                  ][i],
                                  blurRadius: 12)
                            ],
                          ),
                        ),
                      ),
                    ),
                  Icon(Icons.science_rounded, size: 54, color: widget.accent),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          Text(AppLocalizations.of(context).gamePreparingQuestions,
              style: const TextStyle(
                  color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
          const SizedBox(height: 4),
          Text(AppLocalizations.of(context).gamePreparingGame,
              style: TextStyle(color: widget.accent, fontSize: 12, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

class _GlassPanel extends StatelessWidget {
  const _GlassPanel({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
        boxShadow: const [BoxShadow(color: Colors.black45, blurRadius: 30, offset: Offset(0, 12))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
    );
  }
}

class _Dropdown extends StatelessWidget {
  const _Dropdown({required this.value, required this.items, required this.onChanged});
  final String value;
  final List<String> items;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          isExpanded: true,
          dropdownColor: const Color(0xFF14203A),
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 14),
          icon: const Icon(Icons.expand_more_rounded, color: Colors.white70),
          items: [for (final s in items) DropdownMenuItem(value: s, child: Text(s))],
          onChanged: (v) => v == null ? null : onChanged(v),
        ),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({
    required this.label,
    required this.active,
    required this.accent,
    required this.onTap,
    this.square = false,
  });

  final String label;
  final bool active;
  final Color accent;
  final VoidCallback onTap;
  final bool square;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        width: square ? 36 : null,
        height: 38,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: active ? accent.withValues(alpha: 0.25) : Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: active ? accent : Colors.white.withValues(alpha: 0.2),
            width: active ? 2 : 1,
          ),
          boxShadow: active
              ? [BoxShadow(color: accent.withValues(alpha: 0.45), blurRadius: 14)]
              : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active ? Colors.white : Colors.white70,
            fontWeight: FontWeight.w800,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
}

class _BigButton extends StatelessWidget {
  const _BigButton({
    required this.label,
    required this.accent,
    required this.enabled,
    required this.onTap,
  });

  final String label;
  final Color accent;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: enabled ? 1 : 0.45,
      child: GestureDetector(
        onTap: enabled ? onTap : null,
        child: Container(
          height: 56,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [accent, Color.lerp(accent, Colors.black, 0.35)!],
            ),
            borderRadius: BorderRadius.circular(18),
            boxShadow: [BoxShadow(color: accent.withValues(alpha: 0.45), blurRadius: 22)],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.play_arrow_rounded, color: Colors.white, size: 24),
              const SizedBox(width: 6),
              Text(label,
                  style: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
            ],
          ),
        ),
      ),
    );
  }
}


String _levelLabel(AppLocalizations t, String value) => switch (value) {
      'Лёгкий' => t.levelEasy,
      'Сложный' => t.levelHard,
      _ => t.levelMedium,
    };
