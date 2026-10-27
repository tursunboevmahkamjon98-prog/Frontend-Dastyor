import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../models/admin_stats.dart';
import '../../providers/auth_provider.dart';
import '../../services/admin_service.dart';
import '../../widgets/ui/ui.dart';





class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  final _adminService = AdminService();
  late Future<AdminStats> _statsFuture;

  @override
  void initState() {
    super.initState();
    _statsFuture = _adminService.getStats();
  }

  void _refetch() {
    setState(() => _statsFuture = _adminService.getStats());
  }

  Future<void> _confirmLogout(BuildContext context) async {
    final t = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(t.logoutConfirmTitle),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(t.cancel)),
          TextButton(onPressed: () => Navigator.pop(context, true), child: Text(t.logout)),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      await context.read<AuthProvider>().logout();
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final user = context.watch<AuthProvider>().user;
    return Scaffold(
      appBar: AppBar(
        title: Text(t.adminPanel),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout_rounded),
            tooltip: t.logout,
            onPressed: () => _confirmLogout(context),
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            final future = _adminService.getStats();
            setState(() => _statsFuture = future);
            await future;
          },
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(
                '${t.profileTitle}: ${user?.fullName ?? ''}',
                style: const TextStyle(color: AppColors.inkSoft, fontSize: 13),
              ),
              const SizedBox(height: 16),
              FutureBuilder<AdminStats>(
                future: _statsFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Padding(
                      padding: EdgeInsets.only(top: 60),
                      child: Center(child: CircularProgressIndicator(color: AppColors.brand)),
                    );
                  }
                  if (snapshot.hasError) {
                    return _CenteredError(onRetry: _refetch, message: t.errorGeneric);
                  }
                  final s = snapshot.data!;
                  return GridView.count(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisCount: 2,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                    childAspectRatio: 1.35,
                    children: [
                      _StatCard(
                          icon: Icons.people_alt_rounded,
                          label: t.adminTotalUsers,
                          value: s.totalUsers,
                          color: AppColors.brand),
                      _StatCard(
                          icon: Icons.description_outlined,
                          label: t.adminTotalMaterials,
                          value: s.totalMaterials,
                          color: AppColors.konspekt),
                      _StatCard(
                          icon: Icons.fact_check_outlined,
                          label: t.statTests,
                          value: s.totalTests,
                          color: AppColors.test),
                      _StatCard(
                          icon: Icons.slideshow_outlined,
                          label: t.statPresentations,
                          value: s.totalPresentations,
                          color: AppColors.prezentatsiya),
                      _StatCard(
                          icon: Icons.menu_book_outlined,
                          label: t.statConspekts,
                          value: s.totalKonspekts,
                          color: AppColors.lektsiya),
                    ],
                  );
                },
              ),
            ],
          ),
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
    required this.color,
  });

  final IconData icon;
  final String label;
  final int value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    
    
    
    
    return UiStatTile(
      value: '$value',
      label: label,
      accent: color,
      background: color.withValues(alpha: 0.12),
      icon: icon,
    );
  }
}

class _CenteredError extends StatelessWidget {
  const _CenteredError({required this.onRetry, required this.message});
  final VoidCallback onRetry;
  final String message;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.only(top: 60),
      child: Column(
        children: [
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 12),
          TextButton(onPressed: onRetry, child: Text(t.retry)),
        ],
      ),
    );
  }
}
