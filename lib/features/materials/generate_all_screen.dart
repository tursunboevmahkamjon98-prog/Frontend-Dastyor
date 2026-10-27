import 'package:flutter/material.dart' hide MaterialType;
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/constants/subjects.dart';
import '../../core/localization/value_labels.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/error_translator.dart';
import '../../core/routing/routes.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../models/material_type.dart';
import '../../providers/auth_provider.dart';
import '../../services/materials_service.dart';

const _kLevels = ['Лёгкий', 'Средний', 'Сложный'];
const _kLanguages = ['Русский', 'Таджикский', 'Английский'];



const _kTestTypes = [
  'mixed',
  'multiple_choice',
  'true_false',
  'multiple_select',
  'open_ended',
];

enum _Step { form, loading, error, insufficientBalance, result }


















class GenerateAllScreen extends StatefulWidget {
  const GenerateAllScreen({super.key, this.selectAll = false});

  
  
  
  final bool selectAll;

  @override
  State<GenerateAllScreen> createState() => _GenerateAllScreenState();
}

class _GenerateAllScreenState extends State<GenerateAllScreen> {
  final _materialsService = MaterialsService();
  final _formKey = GlobalKey<FormState>();
  final _topicCtrl = TextEditingController();
  String _subject = kSubjects.first.value;
  String _grade = kGrades[6];
  String _language = _kLanguages[0];
  
  
  
  
  
  
  
  static const _creatable = [
    MaterialType.konspekt,
    MaterialType.lektsiya,
    MaterialType.test,
    MaterialType.prezentatsiya,
    MaterialType.amaliy,
  ];
  final _selected = <MaterialType>{MaterialType.konspekt};
  int _slideCount = 10;
  int _questionCount = 10;
  String _testType = _kTestTypes.first;

  _Step _step = _Step.form;
  String? _error;
  GenerateAllResult? _result;

  @override
  void initState() {
    super.initState();
    if (widget.selectAll) _selected.addAll(_creatable);
  }

  @override
  void dispose() {
    _topicCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _step = _Step.loading);
    try {
      final result = await _materialsService.generateAll(
        topic: _topicCtrl.text.trim(),
        subject: _subject,
        grade: _grade,
        
        
        
        level: _kLevels[1],
        language: _language,
        types: _selected.toList(),
        slideCount: _slideCount,
        questionCount: _questionCount,
        testType: _testType,
      );
      if (mounted) await context.read<AuthProvider>().refreshUser();
      if (mounted) {
        setState(() {
          _result = result;
          _step = _Step.result;
        });
      }
    } on ApiException catch (e) {
      if (mounted) {
        setState(() {
          _error = messageFor(context, e);
          _step = e.statusCode == 402 ? _Step.insufficientBalance : _Step.error;
        });
      }
    }
  }

  
  
  
  
  
  
  
  
  
  
  
  
  
  void _closeOrReset() {
    if (context.canPop()) {
      context.pop();
      return;
    }
    setState(() {
      _step = _Step.form;
      _result = null;
      _error = null;
      _topicCtrl.clear();
      _selected
        ..clear()
        ..add(MaterialType.konspekt);
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(t.createMaterialTitle)),
      body: SafeArea(
        child: switch (_step) {
          _Step.form => _buildForm(t),
          _Step.loading => _buildLoading(t),
          _Step.error => _buildError(t),
          _Step.insufficientBalance => _buildInsufficientBalance(t),
          _Step.result => _buildResult(t),
        },
      ),
    );
  }

  Widget _buildForm(AppLocalizations t) => Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            TextFormField(
              controller: _topicCtrl,
              decoration: InputDecoration(
                  labelText: t.topicLabel, hintText: t.topicHint),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? t.errorRequired : null,
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _subject,
              decoration: InputDecoration(labelText: t.subjectLabel),
              items: [
                for (final s in kSubjects)
                  DropdownMenuItem(
                      value: s.value, child: Text(subjectLabel(t, s.value)))
              ],
              onChanged: (v) => setState(() => _subject = v!),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _grade,
              decoration: InputDecoration(labelText: t.gradeLabel),
              items: [
                for (final g in kGrades)
                  DropdownMenuItem(value: g, child: Text(g))
              ],
              onChanged: (v) => setState(() => _grade = v!),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _language,
              decoration: InputDecoration(labelText: t.materialLanguageLabel),
              items: [
                for (final l in _kLanguages)
                  DropdownMenuItem(value: l, child: Text(languageLabel(t, l)))
              ],
              onChanged: (v) => setState(() => _language = v!),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: Text(t.stepTypeTitle,
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                ),
                TextButton(
                  onPressed: () => setState(() {
                    if (_selected.length == _creatable.length) {
                      _selected.clear();
                    } else {
                      _selected
                        ..clear()
                        ..addAll(_creatable);
                    }
                  }),
                  child: Text(_selected.length == _creatable.length
                      ? t.cancel
                      : t.typeGenerateAll),
                ),
              ],
            ),
            const SizedBox(height: 8),
            
            
            
            
            
            
            
            
            LayoutBuilder(
              builder: (context, constraints) {
                const gap = 10.0;
                final cellWidth = (constraints.maxWidth - gap) / 2;
                return Wrap(
                  spacing: gap,
                  runSpacing: gap,
                  children: [
                    for (final type in _creatable)
                      SizedBox(
                        width: cellWidth,
                        child: _TypeCard(
                          type: type,
                          label: _typeLabel(t, type),
                          selected: _selected.contains(type),
                          onTap: () => setState(() {
                            if (!_selected.remove(type)) _selected.add(type);
                          }),
                        ),
                      ),
                  ],
                );
              },
            ),
            
            
            if (_selected.contains(MaterialType.prezentatsiya)) ...[
              const SizedBox(height: 20),
              _CountPicker(
                label: t.slideCountLabel,
                value: _slideCount,
                onChanged: (n) => setState(() => _slideCount = n),
              ),
            ],
            if (_selected.contains(MaterialType.test)) ...[
              const SizedBox(height: 20),
              _CountPicker(
                label: t.questionCountLabel,
                value: _questionCount,
                onChanged: (n) => setState(() => _questionCount = n),
              ),
              const SizedBox(height: 20),
              Text(t.testTypeLabel,
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final tt in _kTestTypes)
                    ChoiceChip(
                      label: Text(_testTypeLabel(t, tt)),
                      selected: _testType == tt,
                      selectedColor: AppColors.brand,
                      labelStyle: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: _testType == tt ? AppColors.white : AppColors.ink,
                      ),
                      onSelected: (_) => setState(() => _testType = tt),
                    ),
                ],
              ),
            ],
            const SizedBox(height: 28),
            ElevatedButton(
              onPressed: _selected.isEmpty ? null : _submit,
              child: Text(t.generateButton),
            ),
          ],
        ),
      );

  Widget _buildLoading(AppLocalizations t) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(color: AppColors.brand),
              const SizedBox(height: 24),
              Text(t.generatingTitle,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 17)),
              const SizedBox(height: 8),
              Text(t.generateAllLoadingDesc,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppColors.inkSoft)),
            ],
          ),
        ),
      );

  Widget _buildError(AppLocalizations t) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline_rounded,
                  size: 48, color: AppColors.danger),
              const SizedBox(height: 16),
              Text(t.generationFailed,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 16)),
              const SizedBox(height: 6),
              Text(_error ?? '',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppColors.inkSoft)),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  OutlinedButton(
                      onPressed: _closeOrReset, child: Text(t.cancel)),
                  const SizedBox(width: 12),
                  ElevatedButton(
                      onPressed: () => setState(() => _step = _Step.form),
                      child: Text(t.retry)),
                ],
              ),
            ],
          ),
        ),
      );

  Widget _buildInsufficientBalance(AppLocalizations t) => Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.account_balance_wallet_outlined,
                  size: 48, color: AppColors.warning),
              const SizedBox(height: 16),
              Text(t.freeLimitReachedTitle,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 16)),
              const SizedBox(height: 6),
              Text(t.insufficientBalanceDesc,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppColors.inkSoft)),
              const SizedBox(height: 20),
              OutlinedButton(
                  onPressed: _closeOrReset, child: Text(t.cancel)),
            ],
          ),
        ),
      );

  Widget _buildResult(AppLocalizations t) {
    final result = _result!;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Row(
          children: [
            const Icon(Icons.check_circle_rounded, color: AppColors.success),
            const SizedBox(width: 8),
            Expanded(
                child: Text(t.generateAllResultTitle(result.items.length),
                    style: const TextStyle(
                        fontWeight: FontWeight.w700, fontSize: 16))),
          ],
        ),
        const SizedBox(height: 16),
        for (final type in MaterialType.values)
          if (result.items[type] case final item?) ...[
            _ResultTile(
              type: type,
              title: item.title,
              onTap: () => context.push(
                  Routes.materialDetailPath(type.apiMaterialType, item.id),
                  extra: item),
            ),
            const SizedBox(height: 10),
          ],
        if (result.skipped.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
              t.generateAllSkippedNote(
                  result.skipped.map((s) => _typeLabel(t, s)).join(', ')),
              style: const TextStyle(color: AppColors.inkSoft, fontSize: 12)),
        ],
        const SizedBox(height: 20),
        OutlinedButton(onPressed: _closeOrReset, child: Text(t.close)),
      ],
    );
  }

  String _testTypeLabel(AppLocalizations t, String value) => switch (value) {
        'multiple_choice' => t.testTypeMultipleChoice,
        'true_false' => t.testTypeTrueFalse,
        'multiple_select' => t.testTypeMultipleSelect,
        'open_ended' => t.testTypeOpenEnded,
        _ => t.testTypeMixed,
      };

  String _typeLabel(AppLocalizations t, MaterialType type) => switch (type) {
        MaterialType.konspekt => t.typeKonspekt,
        MaterialType.test => t.typeTest,
        MaterialType.prezentatsiya => t.typePrezentatsiya,
        MaterialType.lektsiya => t.typeLektsiya,
        MaterialType.amaliy => t.typeAmaliy,
      };
}







class _TypeCard extends StatelessWidget {
  const _TypeCard({
    required this.type,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final MaterialType type;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          curve: Curves.easeOut,
          decoration: BoxDecoration(
            color: selected ? AppColors.brandSoft : AppColors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: selected ? AppColors.brand : AppColors.border,
            ),
            
            
            boxShadow: selected
                ? const [
                    BoxShadow(
                      color: Color(0x14000000),
                      blurRadius: 4,
                      offset: Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: Stack(
            children: [
              Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      height: 40,
                      width: 40,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: type.background,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(type.icon, size: 20, color: type.color),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      label,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.ink,
                      ),
                    ),
                  ],
                ),
              ),
              if (selected)
                Positioned(
                  right: 12,
                  top: 12,
                  child: Container(
                    height: 20,
                    width: 20,
                    alignment: Alignment.center,
                    decoration: const BoxDecoration(
                      color: AppColors.brand,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.check_rounded,
                        size: 12, color: AppColors.white),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}




class _CountPicker extends StatelessWidget {
  const _CountPicker({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final int value;
  final ValueChanged<int> onChanged;

  static const _presets = [5, 10, 15];

  @override
  Widget build(BuildContext context) {
    final custom = !_presets.contains(value);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            for (final n in _presets)
              ChoiceChip(
                label: Text('$n'),
                selected: value == n,
                onSelected: (_) => onChanged(n),
              ),
            SizedBox(
              width: 88,
              child: TextFormField(
                key: ValueKey('count-$label'),
                initialValue: custom ? '$value' : null,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  isDense: true,
                  hintText: '…',
                  contentPadding:
                      EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
                onChanged: (raw) {
                  final n = int.tryParse(raw);
                  
                  
                  
                  if (n != null && n > 0) onChanged(n > 60 ? 60 : n);
                },
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ResultTile extends StatelessWidget {
  const _ResultTile(
      {required this.type, required this.title, required this.onTap});

  final MaterialType type;
  final String title;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                  color: type.color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12)),
              child: Icon(type.icon, color: type.color, size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
                child:
                    Text(title, maxLines: 1, overflow: TextOverflow.ellipsis)),
            const Icon(Icons.chevron_right_rounded, color: AppColors.inkFaint),
          ],
        ),
      ),
    );
  }
}
