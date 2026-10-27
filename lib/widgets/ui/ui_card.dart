import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/ui_tokens.dart';








class UiCard extends StatelessWidget {
  const UiCard({
    super.key,
    required this.child,
    this.onTap,
    this.fill,
    this.border,
    this.radius = Ui.r2xl,
    this.padding = const EdgeInsets.all(Ui.s4),
    this.shadow,
  });

  final Widget child;
  final VoidCallback? onTap;
  final Color? fill;
  final Color? border;
  final double radius;
  final EdgeInsetsGeometry padding;
  final List<BoxShadow>? shadow;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final radii = BorderRadius.circular(radius);

    return DecoratedBox(
      decoration: BoxDecoration(
        color: fill ?? (dark ? AppColors.darkSurface : AppColors.white),
        borderRadius: radii,
        border: border != null ? Border.all(color: border!) : null,
        boxShadow: shadow ?? (dark ? null : Ui.sm),
      ),
      child: Material(
        
        
        
        color: Colors.transparent,
        borderRadius: radii,
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          borderRadius: radii,
          child: Padding(padding: padding, child: child),
        ),
      ),
    );
  }
}




class UiIconChip extends StatelessWidget {
  const UiIconChip({
    super.key,
    required this.icon,
    required this.color,
    required this.background,
    this.size = 36,
    this.radius = Ui.rLg,
  });

  final IconData icon;
  final Color color;
  final Color background;
  final double size;
  final double radius;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(radius),
      ),
      child: Icon(icon, size: size * 0.45, color: color),
    );
  }
}




class UiSectionLabel extends StatelessWidget {
  const UiSectionLabel(this.label, {super.key, this.icon, this.trailing});

  final String label;
  final IconData? icon;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        if (icon != null) ...[
          Icon(icon, size: 14, color: AppColors.inkFaint),
          const SizedBox(width: 6),
        ],
        Expanded(
          child: Text(
            label.toUpperCase(),
            style: Ui.eyebrow.copyWith(color: AppColors.inkFaint),
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}
