import 'package:flutter/material.dart';

/// Ported from the web's generated tokens — see
/// frontend/scripts/design_tokens.py, which is the source of truth and
/// contrast-checks every pair. The app is a visual port of the site, so a
/// colour is changed there first and copied here, never the other way.
class AppColors {
  AppColors._();

  static const Color brand = Color(0xFFE11D2E);
  static const Color brandLight = Color(0xFFF04152);
  static const Color brandDark = Color(0xFFB8121F);
  static const Color brandDarker = Color(0xFFA1121F);

  static const Color brandSoft = Color(0xFFFDEAEC);

  static const Color brandWarm = Color(0xFFB45309);

  static const Color surfaceMuted = Color(0xFFF7F4F4);

  static const Color background = Color(0xFFFDFBFB);
  static const Color white = Color(0xFFFFFFFF);

  static const Color surface = surfaceMuted;

  static const Color ink = Color(0xFF1F2937);

  static const Color inkSoft = Color(0xFF4B5563);

  static const Color inkFaint = Color(0xFF66707E);

  static const Color border = Color(0xFFF2F1F2);

  static const Color borderStrong = Color(0xFFE5E7EB);

  static const Color success = Color(0xFF059669);
  static const Color warning = Color(0xFFD97706);
  static const Color danger = Color(0xFFB3261E);

  static const Color konspekt = Color(0xFF3B82F6);
  static const Color konspektBg = Color(0xFFDBEAFE);
  static const Color test = Color(0xFF10B981);
  static const Color testBg = Color(0xFFD1FAE5);
  static const Color prezentatsiya = Color(0xFFEC4899);
  static const Color prezentatsiyaBg = Color(0xFFFCE7F3);
  static const Color lektsiya = Color(0xFFD97706);
  static const Color lektsiyaBg = Color(0xFFFEF3C7);
  static const Color amaliy = Color(0xFF0D9488);
  static const Color amaliyBg = Color(0xFFCCFBF1);
  static const Color igra = Color(0xFF7C3AED);
  static const Color igraBg = Color(0xFFEDE9FE);

  static Color forMaterial(String token) => switch (token) {
        'konspekt' => konspekt,
        'test' => test,
        'prezentatsiya' => prezentatsiya,
        'lektsiya' => lektsiya,
        'amaliy' => amaliy,
        'igra' => igra,
        _ => brand,
      };

  static Color bgForMaterial(String token) => switch (token) {
        'konspekt' => konspektBg,
        'test' => testBg,
        'prezentatsiya' => prezentatsiyaBg,
        'lektsiya' => lektsiyaBg,
        'amaliy' => amaliyBg,
        'igra' => igraBg,
        _ => brandSoft,
      };

  static const List<Color> heroGradient = [brand, brandDark];

  static const Color darkBg = Color(0xFF131112);
  static const Color darkSurface = Color(0xFF1C1A1B);
  static const Color darkBorder = Color(0xFF383334);
}
