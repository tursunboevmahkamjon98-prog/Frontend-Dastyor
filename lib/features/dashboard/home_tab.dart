import 'package:flutter/material.dart' hide MaterialType;
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/error_translator.dart';
import '../../core/routing/routes.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../models/material_item.dart';
import '../../models/material_type.dart';
import '../../providers/auth_provider.dart';
import '../../services/materials_service.dart';
import '../../widgets/motion.dart';
import '../../widgets/ui/ui.dart';
import '../../widgets/brand/dastyor_logo.dart';

const _kRecentLimit = 3;





class HomeTab extends StatefulWidget {
  const HomeTab({super.key});

  @override
  State<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<HomeTab> {
  final _materialsService = MaterialsService();
  late Future<List<MaterialItem>> _recentFuture;
  String? _openingId;

  @override
  void initState() {
    super.initState();
    _recentFuture = _materialsService.search();
  }

  Future<void> _openRecent(MaterialItem summary) async {
    setState(() => _openingId = summary.id);
    try {
      final full = await _materialsService.getOne(summary.type, summary.id);
      if (mounted) {
        context.push(
            Routes.materialDetailPath(full.type.apiMaterialType, full.id),
            extra: full);
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    } finally {
      if (mounted) setState(() => _openingId = null);
    }
  }

  void _createType(MaterialType type) =>
      context.push(Routes.createDetails, extra: type);

  String _greeting(AppLocalizations t, String name) {
    final hour = DateTime.now().hour;
    if (hour < 12) return t.dashboardGreetingMorning(name);
    if (hour < 18) return t.dashboardGreetingDay(name);
    return t.dashboardGreetingEvening(name);
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final user = context.watch<AuthProvider>().user;
    final firstName = (user?.fullName ?? '').split(' ').first;
    final initial =
        (user?.fullName.isNotEmpty == true ? user!.fullName[0] : '?')
            .toUpperCase();

    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          color: AppColors.brand,
          onRefresh: () async => setState(() {
            _recentFuture = _materialsService.search();
          }),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(Ui.s4, Ui.s4, Ui.s4, Ui.s6),
            children: [
              _HomeHeader(appName: t.appName, avatarInitial: initial),
              const SizedBox(height: Ui.s6),
              _Greeting(
                greeting: _greeting(t, firstName),
                prompt: t.dashboardSubtitle,
              ),
              const SizedBox(height: Ui.s7),
              UiPrimaryBanner(
                icon: Icons.layers_rounded,
                title: t.typeGenerateAll,
                subtitle: t.typeGenerateAllDesc,
                onTap: () => context.push(Routes.generateAllForm),
              ),
              const SizedBox(height: Ui.s8),
              UiSectionLabel(t.quickCreate),
              const SizedBox(height: Ui.s3),
              StaggerIn(
                delayMs: 60,
                child: _CreateGrid(
                  items: [
                    (MaterialType.konspekt, t.typeKonspekt, t.typeKonspektDesc),
                    (MaterialType.test, t.typeTest, t.typeTestDesc),
                    (MaterialType.prezentatsiya, t.typePrezentatsiya,
                        t.typePrezentatsiyaDesc),
                    (MaterialType.lektsiya, t.typeLektsiya, t.typeLektsiyaDesc),
                    (MaterialType.amaliy, t.typeAmaliy, t.typeAmaliyDesc),
                  ],
                  onTap: _createType,
                ),
              ),
              const SizedBox(height: Ui.s8),
              UiSectionLabel(
                t.recentMaterials,
                icon: Icons.schedule_rounded,
                trailing: GestureDetector(
                  onTap: () => context.go(Routes.materials),
                  child: Text(
                    t.viewAll,
                    style: Ui.caption.copyWith(
                      color: AppColors.brand,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: Ui.s3),
              _RecentList(
                future: _recentFuture,
                openingId: _openingId,
                onOpen: _openRecent,
                typeLabel: (type) => switch (type) {
                  MaterialType.konspekt => t.typeKonspekt,
                  MaterialType.test => t.typeTest,
                  MaterialType.prezentatsiya => t.typePrezentatsiya,
                  MaterialType.lektsiya => t.typeLektsiya,
                  MaterialType.amaliy => t.typeAmaliy,
                },
                emptyTitle: t.emptyMaterialsTitle,
                emptySubtitle: t.emptyMaterialsSubtitle,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HomeHeader extends StatelessWidget {
  const _HomeHeader({required this.appName, required this.avatarInitial});

  final String appName;
  final String avatarInitial;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const DastyorMark(height: 22, plate: true),
        const SizedBox(width: 8),
        Text(appName,
            style: const TextStyle(
                fontSize: 17, fontWeight: FontWeight.w800, color: AppColors.ink)),
        const Spacer(),
        const Icon(Icons.notifications_none_rounded,
            color: AppColors.ink, size: 24),
        const SizedBox(width: 14),
        CircleAvatar(
          radius: 18,
          backgroundColor: AppColors.brandSoft,
          child: Text(avatarInitial,
              style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: AppColors.brand)),
        ),
      ],
    );
  }
}



class _Greeting extends StatelessWidget {
  const _Greeting({required this.greeting, required this.prompt});

  final String greeting;
  final String prompt;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '$greeting \u{1F44B}',
          style: Ui.h1.copyWith(color: AppColors.ink),
        ),
        const SizedBox(height: 2),
        Text(prompt, style: Ui.body.copyWith(color: AppColors.inkSoft)),
      ],
    );
  }
}

class _RecentList extends StatelessWidget {
  const _RecentList({
    required this.future,
    required this.openingId,
    required this.onOpen,
    required this.typeLabel,
    required this.emptyTitle,
    required this.emptySubtitle,
  });

  final Future<List<MaterialItem>> future;
  final String? openingId;
  final void Function(MaterialItem) onOpen;

  
  
  
  final String Function(MaterialType) typeLabel;

  final String emptyTitle;
  final String emptySubtitle;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<MaterialItem>>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting &&
            !snapshot.hasData) {
          return Column(
            children: [
              for (var i = 0; i < _kRecentLimit; i++) ...[
                ShimmerBox(
                    height: 62, borderRadius: BorderRadius.circular(Ui.r2xl)),
                const SizedBox(height: Ui.s2),
              ],
            ],
          );
        }

        final items = snapshot.data;
        if (items == null || items.isEmpty) {
          return UiCard(
            padding: const EdgeInsets.symmetric(
                vertical: Ui.s7, horizontal: Ui.s5),
            child: Column(
              children: [
                const Icon(Icons.inbox_rounded,
                    size: 34, color: AppColors.inkFaint),
                const SizedBox(height: Ui.s3),
                Text(emptyTitle,
                    textAlign: TextAlign.center,
                    style: Ui.title.copyWith(color: AppColors.ink)),
                const SizedBox(height: Ui.s1),
                Text(
                  emptySubtitle,
                  textAlign: TextAlign.center,
                  style: Ui.caption.copyWith(color: AppColors.inkSoft),
                ),
              ],
            ),
          );
        }

        return Column(
          children: [
            for (final item in items.take(_kRecentLimit)) ...[
              UiListRow(
                icon: item.type.icon,
                accent: item.type.color,
                background: item.type.background,
                title: item.title,
                
                subtitle: '${typeLabel(item.type)} • ${item.subject}',
                onTap: openingId == item.id ? null : () => onOpen(item),
                trailing: openingId == item.id
                    ? const [
                        SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      ]
                    : null,
              ),
              const SizedBox(height: Ui.s2),
            ],
          ],
        );
      },
    );
  }
}


class _CreateGrid extends StatelessWidget {
  const _CreateGrid({required this.items, required this.onTap});

  final List<(MaterialType, String, String)> items;
  final void Function(MaterialType) onTap;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 640 ? 4 : 2;
        return GridView.count(
          crossAxisCount: columns,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: Ui.s3,
          crossAxisSpacing: Ui.s3,
          childAspectRatio: 1.25,
          children: [
            for (final (type, label, desc) in items) _tile(type, label, desc),
          ],
        );
      },
    );
  }

  Widget _tile(MaterialType type, String label, String desc) => UiCreateTile(
        icon: type.icon,
        accent: type.color,
        background: type.background,
        label: label,
        subtitle: desc,
        onTap: () => onTap(type),
      );
}
