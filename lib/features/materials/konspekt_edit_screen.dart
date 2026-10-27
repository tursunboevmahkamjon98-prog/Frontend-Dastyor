import 'package:flutter/material.dart' hide MaterialType;
import '../../core/network/api_exception.dart';
import '../../core/network/error_translator.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../models/material_item.dart';
import '../../services/materials_service.dart';

enum _FieldKind { text, paragraph, list }








class _FieldSpec {
  const _FieldSpec(this.key, this.labels, this.kind);
  final String key;
  final Map<String, String> labels;
  final _FieldKind kind;

  String label(String localeCode) => labels[localeCode] ?? labels['ru']!;
}





const _kFields = <_FieldSpec>[
  _FieldSpec('title', {'ru': 'Название', 'tg': 'Сарлавҳа', 'en': 'Title'},
      _FieldKind.text),
  _FieldSpec(
      'subtitle',
      {'ru': 'Подзаголовок', 'tg': 'Зерсарлавҳа', 'en': 'Subtitle'},
      _FieldKind.text),
  _FieldSpec(
      'duration',
      {'ru': 'Длительность', 'tg': 'Давомнокӣ', 'en': 'Duration'},
      _FieldKind.text),
  _FieldSpec(
      'objectives',
      {'ru': 'Цели урока', 'tg': 'Мақсадҳои дарс', 'en': 'Objectives'},
      _FieldKind.list),
  _FieldSpec(
      'competencies',
      {'ru': 'Компетенции', 'tg': 'Салоҳиятҳо', 'en': 'Competencies'},
      _FieldKind.list),
  _FieldSpec(
      'key_concepts',
      {
        'ru': 'Ключевые понятия',
        'tg': 'Мафҳумҳои калидӣ',
        'en': 'Key concepts'
      },
      _FieldKind.list),
  _FieldSpec(
      'key_terms',
      {
        'ru': 'Ключевые термины',
        'tg': 'Истилоҳоти калидӣ',
        'en': 'Key terms'
      },
      _FieldKind.list),
  _FieldSpec('tools', {'ru': 'Инструменты', 'tg': 'Асбобҳо', 'en': 'Tools'},
      _FieldKind.list),
  _FieldSpec(
      'lesson_program',
      {'ru': 'Ход урока', 'tg': 'Раванди дарс', 'en': 'Lesson flow'},
      _FieldKind.paragraph),
  _FieldSpec(
      'main_content',
      {
        'ru': 'Основной материал',
        'tg': 'Мазмуни асосӣ',
        'en': 'Main content'
      },
      _FieldKind.paragraph),
  _FieldSpec(
      'real_life_examples',
      {
        'ru': 'Примеры из жизни',
        'tg': 'Мисолҳои ҳаётӣ',
        'en': 'Real-life examples'
      },
      _FieldKind.list),
  _FieldSpec(
      'pair_work',
      {'ru': 'Работа в парах', 'tg': 'Кори ҷуфтӣ', 'en': 'Pair work'},
      _FieldKind.paragraph),
  _FieldSpec(
      'group_work',
      {'ru': 'Групповая работа', 'tg': 'Кори гурӯҳӣ', 'en': 'Group work'},
      _FieldKind.list),
  _FieldSpec(
      'consolidation',
      {'ru': 'Закрепление', 'tg': 'Мустаҳкамкунӣ', 'en': 'Consolidation'},
      _FieldKind.paragraph),
  _FieldSpec(
      'homework',
      {
        'ru': 'Домашнее задание',
        'tg': 'Вазифаи хонагӣ',
        'en': 'Homework'
      },
      _FieldKind.list),
  _FieldSpec(
      'assessment',
      {
        'ru': 'Критерии оценивания',
        'tg': 'Меъёрҳои баҳогузорӣ',
        'en': 'Assessment'
      },
      _FieldKind.paragraph),
  _FieldSpec(
      'important_notes',
      {'ru': 'Важные заметки', 'tg': 'Эслатҳои муҳим', 'en': 'Important notes'},
      _FieldKind.list),
  _FieldSpec('summary', {'ru': 'Итог', 'tg': 'Хулоса', 'en': 'Summary'},
      _FieldKind.paragraph),
];












class KonspektEditScreen extends StatefulWidget {
  const KonspektEditScreen({super.key, required this.item});

  final MaterialItem item;

  @override
  State<KonspektEditScreen> createState() => _KonspektEditScreenState();
}

class _KonspektEditScreenState extends State<KonspektEditScreen> {
  final _materialsService = MaterialsService();
  late final Map<String, dynamic> _content;
  final _textControllers = <String, TextEditingController>{};
  final _listControllers = <String, List<TextEditingController>>{};
  bool _dirty = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final decoded = widget.item.decodedContent as Map<String, dynamic>?;
    _content = decoded == null ? {} : Map<String, dynamic>.from(decoded);
    for (final spec in _kFields) {
      final raw = _content[spec.key];
      if (spec.kind == _FieldKind.list) {
        final items = (raw is List)
            ? raw.map((e) => e.toString()).toList()
            : <String>[];
        if (items.isEmpty) items.add('');
        _listControllers[spec.key] =
            items.map((v) => _watched(TextEditingController(text: v))).toList();
      } else {
        _textControllers[spec.key] =
            _watched(TextEditingController(text: raw?.toString() ?? ''));
      }
    }
  }

  TextEditingController _watched(TextEditingController c) {
    c.addListener(() {
      if (!_dirty) setState(() => _dirty = true);
    });
    return c;
  }

  @override
  void dispose() {
    for (final c in _textControllers.values) {
      c.dispose();
    }
    for (final list in _listControllers.values) {
      for (final c in list) {
        c.dispose();
      }
    }
    super.dispose();
  }

  void _addListItem(String key) {
    setState(() {
      _listControllers[key]!.add(_watched(TextEditingController()));
      _dirty = true;
    });
  }

  void _removeListItem(String key, int index) {
    setState(() {
      final list = _listControllers[key]!;
      list.removeAt(index).dispose();
      if (list.isEmpty) list.add(_watched(TextEditingController()));
      _dirty = true;
    });
  }

  Future<bool> _confirmDiscard() async {
    if (!_dirty) return true;
    final t = AppLocalizations.of(context);
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(t.unsavedChangesTitle),
        content: Text(t.unsavedChangesMessage),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(t.cancel)),
          TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(t.discard)),
        ],
      ),
    );
    return result ?? false;
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final updated = Map<String, dynamic>.from(_content);
    for (final spec in _kFields) {
      if (spec.kind == _FieldKind.list) {
        final values = _listControllers[spec.key]!
            .map((c) => c.text.trim())
            .where((v) => v.isNotEmpty)
            .toList();
        updated[spec.key] = values;
      } else {
        updated[spec.key] = _textControllers[spec.key]!.text.trim();
      }
    }
    try {
      await _materialsService.updateContent(widget.item.type, widget.item.id, updated);
      
      
      
      
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final localeCode = Localizations.localeOf(context).languageCode;
    return PopScope(
      canPop: !_dirty,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final navigator = Navigator.of(context);
        final shouldPop = await _confirmDiscard();
        if (shouldPop) navigator.pop();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(t.konspektEditTitle),
          actions: [
            if (_saving)
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16),
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2.4, color: AppColors.white),
                ),
              )
            else
              TextButton(
                onPressed: _save,
                child: Text(t.save,
                    style: const TextStyle(
                        color: AppColors.white, fontWeight: FontWeight.w700)),
              ),
          ],
        ),
        body: SafeArea(
          child: ListView.separated(
            padding: const EdgeInsets.all(20),
            itemCount: _kFields.length,
            separatorBuilder: (_, __) => const SizedBox(height: 16),
            itemBuilder: (context, i) {
              final spec = _kFields[i];
              return _FieldCard(
                spec: spec,
                localeCode: localeCode,
                textController: _textControllers[spec.key],
                listControllers: _listControllers[spec.key],
                onAddItem: () => _addListItem(spec.key),
                onRemoveItem: (index) => _removeListItem(spec.key, index),
                addLabel: t.addItem,
              );
            },
          ),
        ),
      ),
    );
  }
}

class _FieldCard extends StatelessWidget {
  const _FieldCard({
    required this.spec,
    required this.localeCode,
    required this.textController,
    required this.listControllers,
    required this.onAddItem,
    required this.onRemoveItem,
    required this.addLabel,
  });

  final _FieldSpec spec;
  final String localeCode;
  final TextEditingController? textController;
  final List<TextEditingController>? listControllers;
  final VoidCallback onAddItem;
  final ValueChanged<int> onRemoveItem;
  final String addLabel;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(spec.label(localeCode),
              style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                  color: AppColors.inkSoft)),
          const SizedBox(height: 8),
          if (spec.kind == _FieldKind.list)
            _ListEditor(
              controllers: listControllers!,
              onAdd: onAddItem,
              onRemove: onRemoveItem,
              addLabel: addLabel,
            )
          else
            TextField(
              controller: textController,
              maxLines: spec.kind == _FieldKind.paragraph ? null : 1,
              minLines: spec.kind == _FieldKind.paragraph ? 3 : 1,
              decoration: const InputDecoration(
                isDense: true,
                filled: true,
                fillColor: AppColors.white,
                border: OutlineInputBorder(),
              ),
            ),
        ],
      ),
    );
  }
}

class _ListEditor extends StatelessWidget {
  const _ListEditor({
    required this.controllers,
    required this.onAdd,
    required this.onRemove,
    required this.addLabel,
  });

  final List<TextEditingController> controllers;
  final VoidCallback onAdd;
  final ValueChanged<int> onRemove;
  final String addLabel;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < controllers.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: TextField(
                    controller: controllers[i],
                    maxLines: null,
                    minLines: 1,
                    decoration: const InputDecoration(
                      isDense: true,
                      filled: true,
                      fillColor: AppColors.white,
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                IconButton(
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.close_rounded,
                      size: 18, color: AppColors.inkFaint),
                  onPressed: () => onRemove(i),
                ),
              ],
            ),
          ),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: onAdd,
            icon: const Icon(Icons.add_rounded, size: 18),
            label: Text(addLabel),
          ),
        ),
      ],
    );
  }
}
