import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/ui_tokens.dart';
import 'ui_card.dart';








class UiStatTile extends StatelessWidget {
  const UiStatTile({
    super.key,
    required this.icon,
    required this.accent,
    required this.background,
    required this.label,
    this.value,
    this.valueWidget,
    this.onTap,
  });

  final IconData icon;
  final Color accent;
  final Color background;
  final String label;

  
  final String? value;

  
  final Widget? valueWidget;

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    assert((value == null) != (valueWidget == null),
        'UiStatTile needs exactly one of value / valueWidget');

    return UiCard(
      onTap: onTap,
      fill: background,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          
          
          
          Container(
            width: 36,
            height: 36,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.white.withValues(alpha: 0.7),
              borderRadius: BorderRadius.circular(Ui.rLg),
            ),
            child: Icon(icon, size: 17, color: accent),
          ),
          const SizedBox(height: Ui.s3),
          
          
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: valueWidget ??
                Text(value!, style: Ui.stat.copyWith(color: AppColors.ink)),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Ui.caption.copyWith(
              color: AppColors.inkSoft,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}




class UiPrimaryBanner extends StatelessWidget {
  const UiPrimaryBanner({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final radii = BorderRadius.circular(Ui.r2xl);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.brand,
        borderRadius: radii,
        boxShadow: Ui.primaryMd,
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: radii,
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          borderRadius: radii,
          child: Stack(
            children: [
              Positioned(
                right: -14,
                bottom: -14,
                child: Icon(
                  Icons.smart_toy_rounded,
                  size: 88,
                  color: AppColors.white.withValues(alpha: 0.12),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(Ui.s5),
                child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: AppColors.white.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(Ui.rXl),
                  ),
                  child: Icon(icon, size: 20, color: AppColors.white),
                ),
                const SizedBox(width: Ui.s4),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Ui.title.copyWith(color: AppColors.white)),
                      const SizedBox(height: 2),
                      Text(subtitle,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: Ui.body.copyWith(
                              color: AppColors.white.withValues(alpha: 0.8))),
                    ],
                  ),
                ),
                const SizedBox(width: Ui.s2),
                Icon(Icons.chevron_right_rounded,
                    size: 22, color: AppColors.white.withValues(alpha: 0.7)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
