import 'package:flutter/material.dart' hide MaterialType;
import 'package:go_router/go_router.dart';
import '../../core/constants/subjects.dart';
import '../../core/localization/value_labels.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/error_translator.dart';
import '../../core/routing/routes.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../models/material_item.dart';
import '../../models/material_type.dart';
import '../../services/materials_service.dart';
import '../../widgets/ui/ui.dart';
import '../../widgets/motion.dart';

const _kAllLabel = {'ru': 'Все', 'en': 'All', 'tg': 'Ҳама'};



class _ListData {
  const _ListData({required this.items});
  final List<MaterialItem> items;
}



class MaterialsListScreen extends StatefulWidget {
  const MaterialsListScreen({super.key});

  @override
  State<MaterialsListScreen> createState() => _MaterialsListScreenState();
}

class _MaterialsListScreenState extends State<MaterialsListScreen> {
  final _materialsService = MaterialsService();
  final _searchCtrl = TextEditingController();
  late Future<_ListData> _dataFuture;
  String? _openingId;
  String? _busyId;
  String? _subjectFilter;
  String? _gradeFilter;

  @override
  void initState() {
    super.initState();
    _dataFuture = _fetchAll();
  }

  Future<_ListData> _fetchAll() async {
    final items = await _materialsService.search(
        query: _searchCtrl.text, subject: _subjectFilter, grade: _gradeFilter);
    return _ListData(items: items);
  }

  void _refetch() {
    
    
    
    setState(() {
      _dataFuture = _fetchAll();
    });
  }



  Future<void> _open(MaterialItem summary) async {
    setState(() => _openingId = summary.id);
    try {
      final full = await _materialsService.getOne(summary.type, summary.id);
      if (mounted) {
        context.push(Routes.materialDetailPath(full.type.apiMaterialType, full.id), extra: full);
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    } finally {
      if (mounted) setState(() => _openingId = null);
    }
  }

  Future<void> _toggleFavorite(MaterialItem item) async {
    setState(() => _busyId = item.id);
    try {
      await _materialsService.setFavorite(item.type, item.id, !item.isFavorite);
      if (mounted) _refetch();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  Future<void> _delete(MaterialItem item) async {
    final t = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(t.deleteConfirmTitle),
        content: Text(t.deleteConfirmMessage),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(t.cancel)),
          TextButton(onPressed: () => Navigator.pop(context, true), child: Text(t.delete)),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _busyId = item.id);
    try {
      await _materialsService.delete(item.type, item.id);
      if (mounted) _refetch();
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _busyId = null);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    }
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(t.myMaterialsTitle)),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(Ui.s4, Ui.s2, Ui.s4, 0),
          child: Column(
            children: [
              TextField(
                controller: _searchCtrl,
                decoration: InputDecoration(
                    hintText: t.searchHint, prefixIcon: const Icon(Icons.search_rounded)),
                onSubmitted: (_) => _refetch(),
              ),
              const SizedBox(height: 12),
              _FilterRow(
                subject: _subjectFilter,
                grade: _gradeFilter,
                onChanged: (subject, grade) {
                  setState(() {
                    _subjectFilter = subject;
                    _gradeFilter = grade;
                  });
                  _refetch();
                },
              ),
              const SizedBox(height: 12),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: () async {
                    final future = _fetchAll();
                    setState(() {
                      _dataFuture = future;
                    });
                    await future;
                  },
                  child: FutureBuilder<_ListData>(
                    future: _dataFuture,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting &&
                          !snapshot.hasData) {
                        
                        
                        
                        
                        return ListView.separated(
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: 6,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: Ui.s2),
                          itemBuilder: (_, __) => ShimmerBox(
                              height: 66,
                              borderRadius: BorderRadius.circular(Ui.r2xl)),
                        );
                      }
                      if (snapshot.hasError) {
                        return _CenteredScrollable(
                          children: [
                            Text(t.generationFailed),
                            const SizedBox(height: 12),
                            TextButton(onPressed: _refetch, child: Text(t.retry)),
                          ],
                        );
                      }
                      final items = snapshot.data?.items ?? const [];
                      if (items.isEmpty) {
                        return _CenteredScrollable(
                          children: [
                            const Icon(Icons.inbox_rounded,
                                size: 40, color: AppColors.inkFaint),
                            const SizedBox(height: Ui.s4),
                            Text(t.emptyMaterialsTitle,
                                textAlign: TextAlign.center,
                                style: Ui.title.copyWith(color: AppColors.ink)),
                            const SizedBox(height: Ui.s1),
                            Text(t.emptyMaterialsSubtitle,
                                textAlign: TextAlign.center,
                                style: Ui.body
                                    .copyWith(color: AppColors.inkSoft)),
                          ],
                        );
                      }
                      
                      
                      
                      
                      return ListView.separated(
                        physics: const AlwaysScrollableScrollPhysics(),
                        itemCount: items.length,
                        separatorBuilder: (_, __) =>
                            const SizedBox(height: Ui.s2),
                        itemBuilder: (context, i) {
                          
                          
                          
                          final delayMs = i * 30 > 240 ? 240 : i * 30;
                          final item = items[i];
                          return StaggerIn(
                            delayMs: delayMs,
                            child: _MaterialTile(
                              item: item,
                              loading: _openingId == item.id,
                              busy: _busyId == item.id,
                              onTap: () => _open(item),
                              onFavoriteToggle: () => _toggleFavorite(item),
                              onDelete: () => _delete(item),
                            ),
                          );
                        },
                      );
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}




class _CenteredScrollable extends StatelessWidget {
  const _CenteredScrollable({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) => SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: children),
            ),
          ),
        ),
      );
}





class _FilterRow extends StatelessWidget {
  const _FilterRow({required this.subject, required this.grade, required this.onChanged});

  final String? subject;
  final String? grade;
  final void Function(String? subject, String? grade) onChanged;

  String _allLabel(BuildContext context) =>
      _kAllLabel[Localizations.localeOf(context).languageCode] ?? _kAllLabel['ru']!;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final allLabel = _allLabel(context);
    return Row(
      children: [
        Expanded(
          child: DropdownButtonFormField<String?>(
            initialValue: subject,
            isExpanded: true,
            decoration: InputDecoration(labelText: t.subjectLabel, isDense: true),
            items: [
              DropdownMenuItem(value: null, child: Text(allLabel)),
              for (final s in kSubjects)
                DropdownMenuItem(
                    value: s.value, child: Text(subjectLabel(t, s.value))),
            ],
            onChanged: (v) => onChanged(v, grade),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: DropdownButtonFormField<String?>(
            initialValue: grade,
            isExpanded: true,
            decoration: InputDecoration(labelText: t.gradeLabel, isDense: true),
            items: [
              DropdownMenuItem(value: null, child: Text(allLabel)),
              for (final g in kGrades) DropdownMenuItem(value: g, child: Text(g)),
            ],
            onChanged: (v) => onChanged(subject, v),
          ),
        ),
      ],
    );
  }
}

class _MaterialTile extends StatelessWidget {
  const _MaterialTile({
    required this.item,
    required this.loading,
    required this.busy,
    required this.onTap,
    required this.onFavoriteToggle,
    required this.onDelete,
  });

  final MaterialItem item;
  final bool loading;
  final bool busy;
  final VoidCallback onTap;
  final VoidCallback onFavoriteToggle;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    
    
    
    return UiCard(
      onTap: loading ? null : onTap,
      padding: const EdgeInsets.all(14),
      child: Row(
          children: [
            UiIconChip(
              icon: item.type.icon,
              color: item.type.color,
              background: item.type.background,
              size: 40,
              radius: Ui.rXl,
            ),
            const SizedBox(width: Ui.s3),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(item.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Ui.bodyMedium.copyWith(color: AppColors.ink)),
                  const SizedBox(height: 2),
                  Text('${item.subject} • ${item.grade}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Ui.caption.copyWith(color: AppColors.inkSoft)),
                ],
              ),
            ),
            if (loading || busy)
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 8),
                child: SizedBox(
                    width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
              )
            else ...[
              PressableScaleWrap(
                enabled: true,
                child: IconButton(
                  visualDensity: VisualDensity.compact,
                  
                  
                  
                  icon: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 200),
                    transitionBuilder: (child, anim) =>
                        ScaleTransition(scale: anim, child: child),
                    child: Icon(
                      item.isFavorite ? Icons.star_rounded : Icons.star_outline_rounded,
                      key: ValueKey(item.isFavorite),
                      color: item.isFavorite ? AppColors.warning : AppColors.inkFaint,
                    ),
                  ),
                  onPressed: onFavoriteToggle,
                ),
              ),
              IconButton(
                visualDensity: VisualDensity.compact,
                icon: const Icon(Icons.delete_outline_rounded, color: AppColors.inkFaint),
                onPressed: onDelete,
              ),
            ],
          ],
        ),
    );
  }
}
