import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';
import '../l10n/gen/app_localizations.dart';
import 'brand/dastyor_logo.dart';








class AuthSidePanel extends StatelessWidget {
  const AuthSidePanel({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: AppColors.heroGradient,
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Stack(
        children: [
          
          
          Positioned(
              top: -70,
              left: -70,
              child: _blob(240, Colors.white.withValues(alpha: 0.10))),
          Positioned(
              bottom: -100,
              right: -60,
              child: _blob(320, Colors.white.withValues(alpha: 0.08))),
          Positioned(
              top: 220,
              right: -40,
              child: _blob(160, Colors.white.withValues(alpha: 0.08))),
          Padding(
            padding: const EdgeInsets.all(56),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 72,
                      height: 72,
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppColors.white,
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: [
                          BoxShadow(
                              color: Colors.black.withValues(alpha: 0.15),
                              blurRadius: 20,
                              offset: const Offset(0, 8)),
                        ],
                      ),
                      child: const DastyorMark(height: 44),
                    ),
                    const SizedBox(height: 32),
                    const Text('Dastyor',
                        style: TextStyle(
                            color: AppColors.white,
                            fontSize: 34,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 40),
                    _Bullet(icon: Icons.auto_awesome_rounded, text: t.authSideBullet2),
                    const SizedBox(height: 18),
                    _Bullet(icon: Icons.print_rounded, text: t.authSideBullet3),
                    const SizedBox(height: 18),
                    _Bullet(icon: Icons.school_rounded, text: t.appTagline),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _blob(double size, Color color) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      );
}

class _Bullet extends StatelessWidget {
  const _Bullet({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 32,
          height: 32,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.16),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: AppColors.white, size: 17),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(text,
                style: TextStyle(
                    color: AppColors.white.withValues(alpha: 0.92),
                    fontSize: 15,
                    height: 1.35)),
          ),
        ),
      ],
    );
  }
}
