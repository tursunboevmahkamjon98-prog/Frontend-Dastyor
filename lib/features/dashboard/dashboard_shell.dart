import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../widgets/ui/ui.dart';
import '../../widgets/brand/dastyor_logo.dart';











class DashboardShell extends StatelessWidget {
  const DashboardShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  void _goBranch(int index) => navigationShell.goBranch(
        index,
        initialLocation: index == navigationShell.currentIndex,
      );

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    if (kIsWeb) {
      return _WebShell(navigationShell: navigationShell, onSelect: _goBranch, t: t);
    }
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: UiBottomNav(
        currentIndex: navigationShell.currentIndex,
        onTap: _goBranch,
        
        
        items: [
          UiNavItem(icon: Icons.home_rounded, label: t.navHome),
          UiNavItem(icon: Icons.layers_rounded, label: t.navMaterials),
          UiNavItem(icon: Icons.add_circle_outline_rounded, label: t.navCreate),
          UiNavItem(icon: Icons.person_outline_rounded, label: t.navProfile),
        ],
      ),
    );
  }
}




class _WebShell extends StatelessWidget {
  const _WebShell({required this.navigationShell, required this.onSelect, required this.t});

  final StatefulNavigationShell navigationShell;
  final ValueChanged<int> onSelect;
  final AppLocalizations t;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Row(
        children: [
          Container(
            width: 232,
            color: AppColors.white,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 28, 24, 20),
                  child: Row(
                    children: [
                      const DastyorMark(height: 28),
                      const SizedBox(width: 10),
                      Text(t.appName,
                          style: const TextStyle(
                              fontSize: 18, fontWeight: FontWeight.w800, color: AppColors.ink)),
                    ],
                  ),
                ),
                _RailItem(
                  icon: Icons.home_rounded,
                  label: t.navHome,
                  selected: navigationShell.currentIndex == 0,
                  onTap: () => onSelect(0),
                ),
                _RailItem(
                  icon: Icons.folder_rounded,
                  label: t.navMaterials,
                  selected: navigationShell.currentIndex == 1,
                  onTap: () => onSelect(1),
                ),
                _RailItem(
                  icon: Icons.add_circle_rounded,
                  label: t.navCreate,
                  selected: navigationShell.currentIndex == 2,
                  onTap: () => onSelect(2),
                ),
                _RailItem(
                  icon: Icons.person_rounded,
                  label: t.navProfile,
                  selected: navigationShell.currentIndex == 3,
                  onTap: () => onSelect(3),
                ),
              ],
            ),
          ),
          Expanded(
            child: Center(
              child: ConstrainedBox(
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                constraints: const BoxConstraints(maxWidth: 1240),
                child: Container(
                  margin: const EdgeInsets.fromLTRB(0, 24, 24, 24),
                  decoration: BoxDecoration(
                    color: AppColors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppColors.border),
                    boxShadow: [
                      BoxShadow(
                          color: Colors.black.withValues(alpha: 0.04),
                          blurRadius: 24,
                          offset: const Offset(0, 8)),
                    ],
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: navigationShell,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RailItem extends StatelessWidget {
  const _RailItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
      child: Material(
        color: selected ? AppColors.brandLight : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(10),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            child: Row(
              children: [
                Icon(icon, size: 20, color: selected ? AppColors.brand : AppColors.inkSoft),
                const SizedBox(width: 12),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    color: selected ? AppColors.brand : AppColors.inkSoft,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
