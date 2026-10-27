import 'package:flutter/material.dart';
import 'app_colors.dart';









class Ui {
  Ui._();

  
  static const double rLg = 8; 
  static const double rXl = 12; 
  static const double r2xl = 16; 
  static const double r3xl = 24; 
  static const double rFull = 999; 

  
  static const double s1 = 4;
  static const double s2 = 8;
  static const double s3 = 12;
  static const double s4 = 16;
  static const double s5 = 20;
  static const double s6 = 24;
  static const double s7 = 28;
  static const double s8 = 32;

  
  
  static List<BoxShadow> get sm => const [
        BoxShadow(
          color: Color(0x0D000000),
          blurRadius: 2,
          offset: Offset(0, 1),
        ),
      ];

  
  static List<BoxShadow> get md => const [
        BoxShadow(
          color: Color(0x1A000000),
          blurRadius: 6,
          spreadRadius: -1,
          offset: Offset(0, 4),
        ),
        BoxShadow(
          color: Color(0x1A000000),
          blurRadius: 4,
          spreadRadius: -2,
          offset: Offset(0, 2),
        ),
      ];

  
  
  static List<BoxShadow> get primaryMd => [
        BoxShadow(
          color: AppColors.brand.withValues(alpha: 0.20),
          blurRadius: 12,
          spreadRadius: -1,
          offset: const Offset(0, 5),
        ),
      ];

  
  
  static const TextStyle h1 = TextStyle(
    fontSize: 22,
    fontWeight: FontWeight.w700,
    height: 1.25,
  );

  
  static const TextStyle h2 = TextStyle(
    fontSize: 19,
    fontWeight: FontWeight.w700,
    height: 1.3,
  );

  
  static const TextStyle title = TextStyle(
    fontSize: 15,
    fontWeight: FontWeight.w600,
    height: 1.35,
  );

  
  static const TextStyle body = TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.w400,
    height: 1.45,
  );

  
  static const TextStyle bodyMedium = TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.w500,
    height: 1.4,
  );

  
  static const TextStyle caption = TextStyle(
    fontSize: 12,
    fontWeight: FontWeight.w400,
    height: 1.35,
  );

  
  
  static const TextStyle eyebrow = TextStyle(
    fontSize: 11.5,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.6,
    height: 1.3,
  );

  
  static const TextStyle stat = TextStyle(
    fontSize: 24,
    fontWeight: FontWeight.w700,
    height: 1.15,
  );
}
