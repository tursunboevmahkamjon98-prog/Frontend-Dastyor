import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/ui_tokens.dart';
import 'ui_card.dart';








class UiListRow extends StatelessWidget {
  const UiListRow({
    super.key,
    required this.icon,
    required this.accent,
    required this.background,
    required this.title,
    this.subtitle,
    this.onTap,
    this.trailing,
    this.fill,
  });

  final IconData icon;
  final Color accent;
  final Color background;
  final String title;
  final String? subtitle;
  final VoidCallback? onTap;
  final List<Widget>? trailing;
  final Color? fill;

  @override
  Widget build(BuildContext context) {
    return UiCard(
      onTap: onTap,
      fill: fill,
      padding: const EdgeInsets.all(Ui.s3),
      child: Row(
        children: [
          UiIconChip(icon: icon, color: accent, background: background),
          const SizedBox(width: Ui.s3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Ui.bodyMedium.copyWith(color: AppColors.ink),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Ui.caption.copyWith(color: AppColors.inkFaint),
                  ),
                ],
              ],
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: Ui.s2),
            ...trailing!,
          ],
        ],
      ),
    );
  }
}




class UiCreateTile extends StatelessWidget {
  const UiCreateTile({
    super.key,
    required this.icon,
    required this.accent,
    required this.background,
    required this.label,
    this.subtitle,
    this.onTap,
  });

  final IconData icon;
  final Color accent;
  final Color background;
  final String label;
  final String? subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return UiCard(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          UiIconChip(
            icon: icon,
            color: accent,
            background: background,
            size: 40,
            radius: Ui.rXl,
          ),
          const SizedBox(height: Ui.s3),
          Text(
            label,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Ui.title.copyWith(color: AppColors.ink),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 2),
            Text(
              subtitle!,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Ui.caption.copyWith(color: AppColors.inkSoft),
            ),
          ],
        ],
      ),
    );
  }
}
