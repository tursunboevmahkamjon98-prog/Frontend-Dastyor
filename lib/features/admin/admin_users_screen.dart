import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/network/api_exception.dart';
import '../../core/network/error_translator.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../models/admin_user.dart';
import '../../providers/auth_provider.dart';
import '../../services/admin_service.dart';
import '../../widgets/loading_button.dart';






class AdminUsersScreen extends StatefulWidget {
  const AdminUsersScreen({super.key});

  @override
  State<AdminUsersScreen> createState() => _AdminUsersScreenState();
}

class _AdminUsersScreenState extends State<AdminUsersScreen> {
  final _adminService = AdminService();
  final _searchCtrl = TextEditingController();
  late Future<List<AdminUserSummary>> _usersFuture;
  String? _busyId;

  @override
  void initState() {
    super.initState();
    _usersFuture = _adminService.listUsers();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  void _refetch() {
    setState(() {
      _usersFuture = _adminService.listUsers(query: _searchCtrl.text.trim());
    });
  }

  Future<void> _runAction(String userId, Future<void> Function() action) async {
    setState(() => _busyId = userId);
    try {
      await action();
      _refetch();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(messageFor(context, e))));
      }
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  Future<void> _toggleRole(AdminUserSummary u) => _runAction(
        u.id,
        () => _adminService.setRole(u.id, u.isAdmin ? 'user' : 'admin'),
      );

  Future<void> _togglePremium(AdminUserSummary u) =>
      _runAction(u.id, () => _adminService.setPremium(u.id, !u.isPremium));

  Future<void> _topUp(AdminUserSummary u) async {
    final t = AppLocalizations.of(context);
    final amount = await showDialog<double>(
      context: context,
      builder: (_) => _TopUpDialog(user: u),
    );
    if (amount == null || !mounted) return;
    await _runAction(u.id, () => _adminService.addBalance(u.id, amount));
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(t.adminBalanceUpdated)));
    }
  }

  Future<void> _confirmDelete(AdminUserSummary u) async {
    final t = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(t.deleteConfirmTitle),
        content: Text('${u.fullName}${u.phone != null ? ' (${u.phone})' : ''}\n${t.deleteConfirmMessage}'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(t.cancel)),
          TextButton(onPressed: () => Navigator.pop(context, true), child: Text(t.delete)),
        ],
      ),
    );
    if (confirmed != true) return;
    await _runAction(u.id, () => _adminService.deleteUser(u.id));
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final myId = context.watch<AuthProvider>().user?.id;
    return Scaffold(
      appBar: AppBar(title: Text(t.adminUsersTitle)),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: TextField(
                controller: _searchCtrl,
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _refetch(),
                decoration: InputDecoration(
                  hintText: t.adminSearchHint,
                  prefixIcon: const Icon(Icons.search_rounded),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.arrow_forward_rounded),
                    onPressed: _refetch,
                  ),
                ),
              ),
            ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: () async => _refetch(),
                child: FutureBuilder<List<AdminUserSummary>>(
                  future: _usersFuture,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator(color: AppColors.brand));
                    }
                    if (snapshot.hasError) {
                      return _CenteredScrollable(child: Text(t.errorGeneric));
                    }
                    final users = snapshot.data ?? [];
                    if (users.isEmpty) {
                      return _CenteredScrollable(child: Text(t.adminNoUsers));
                    }
                    return ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                      itemCount: users.length,
                      itemBuilder: (context, i) {
                        final u = users[i];
                        return _AdminUserCard(
                          user: u,
                          isSelf: u.id == myId,
                          busy: _busyId == u.id,
                          onToggleRole: () => _toggleRole(u),
                          onTogglePremium: () => _togglePremium(u),
                          onTopUp: () => _topUp(u),
                          onDelete: () => _confirmDelete(u),
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
    );
  }
}

class _CenteredScrollable extends StatelessWidget {
  const _CenteredScrollable({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) => SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Center(child: Padding(padding: const EdgeInsets.all(32), child: child)),
          ),
        ),
      );
}

class _AdminUserCard extends StatelessWidget {
  const _AdminUserCard({
    required this.user,
    required this.isSelf,
    required this.busy,
    required this.onToggleRole,
    required this.onTogglePremium,
    required this.onTopUp,
    required this.onDelete,
  });

  final AdminUserSummary user;
  final bool isSelf;
  final bool busy;
  final VoidCallback onToggleRole;
  final VoidCallback onTogglePremium;
  final VoidCallback onTopUp;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 6,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(user.fullName,
                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                          if (user.isAdmin) const _Badge(label: 'ADMIN', color: AppColors.brand),
                          if (user.isPremium)
                            const _Badge(label: 'PREMIUM', color: AppColors.warning),
                          if (isSelf)
                            _Badge(label: t.adminYouBadge, color: AppColors.inkFaint),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(user.phone ?? user.email ?? '—',
                          style: const TextStyle(color: AppColors.inkSoft, fontSize: 12)),
                      if (user.shortId != null)
                        Text('ID: ${user.shortId}',
                            style: const TextStyle(
                                color: AppColors.brand, fontWeight: FontWeight.w700, fontSize: 12)),
                    ],
                  ),
                ),
                if (busy)
                  const Padding(
                    padding: EdgeInsets.all(8),
                    child: SizedBox(
                        width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.2)),
                  )
                else
                  PopupMenuButton<String>(
                    icon: const Icon(Icons.more_vert_rounded),
                    onSelected: (v) {
                      switch (v) {
                        case 'topup':
                          onTopUp();
                        case 'premium':
                          onTogglePremium();
                        case 'role':
                          onToggleRole();
                        case 'delete':
                          onDelete();
                      }
                    },
                    itemBuilder: (context) => [
                      PopupMenuItem(value: 'topup', child: Text(t.adminTopUpAction)),
                      PopupMenuItem(
                          value: 'premium',
                          child: Text(user.isPremium ? t.adminRemovePremium : t.adminGivePremium)),
                      PopupMenuItem(
                        value: 'role',
                        enabled: !isSelf,
                        child: Text(user.isAdmin ? t.adminRemoveAdmin : t.adminMakeAdmin),
                      ),
                      PopupMenuItem(
                        value: 'delete',
                        enabled: !isSelf,
                        child: Text(t.delete, style: const TextStyle(color: AppColors.danger)),
                      ),
                    ],
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _StatChip(
                    icon: Icons.account_balance_wallet_outlined,
                    label: '${user.balanceSomoni.toStringAsFixed(0)} c.'),
                _StatChip(icon: Icons.description_outlined, label: '${user.totalMaterials}'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(label,
            style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.w800)),
      );
}

class _StatChip extends StatelessWidget {
  const _StatChip({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: AppColors.inkSoft),
            const SizedBox(width: 4),
            Text(label, style: const TextStyle(fontSize: 12, color: AppColors.inkSoft)),
          ],
        ),
      );
}

class _TopUpDialog extends StatefulWidget {
  const _TopUpDialog({required this.user});
  final AdminUserSummary user;

  @override
  State<_TopUpDialog> createState() => _TopUpDialogState();
}

class _TopUpDialogState extends State<_TopUpDialog> {
  final _ctrl = TextEditingController();

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final amount = double.tryParse(_ctrl.text.trim());
    return AlertDialog(
      title: Text(t.adminTopUpAction),
      content: TextField(
        controller: _ctrl,
        autofocus: true,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: t.adminAmountSomoni),
        onChanged: (_) => setState(() {}),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(t.cancel)),
        LoadingButton(
          label: t.save,
          loading: false,
          onPressed: (amount != null && amount > 0) ? () => Navigator.pop(context, amount) : null,
        ),
      ],
    );
  }
}
