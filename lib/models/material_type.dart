import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';








enum MaterialType { konspekt, test, prezentatsiya, lektsiya, amaliy }

extension MaterialTypeX on MaterialType {
  
  String get apiSegment => switch (this) {
        MaterialType.konspekt => 'konspekts',
        MaterialType.test => 'tests',
        MaterialType.prezentatsiya => 'presentations',
        MaterialType.lektsiya => 'lectures',
        MaterialType.amaliy => 'practical-tasks',
      };

  
  
  
  String get apiMaterialType => switch (this) {
        MaterialType.konspekt => 'konspekt',
        MaterialType.test => 'test',
        MaterialType.prezentatsiya => 'prezentatsiya',
        MaterialType.lektsiya => 'lektsiya',
        MaterialType.amaliy => 'amaliy',
      };

  
  
  
  static MaterialType fromApiValue(String value) => switch (value) {
        'test' => MaterialType.test,
        'prezentatsiya' => MaterialType.prezentatsiya,
        'lektsiya' => MaterialType.lektsiya,
        'amaliy' => MaterialType.amaliy,
        _ => MaterialType.konspekt,
      };

  
  
  String get contentField => switch (this) {
        MaterialType.konspekt => 'content',
        MaterialType.test => 'questions_json',
        MaterialType.prezentatsiya => 'slides_json',
        MaterialType.lektsiya => 'content',
        
        
        MaterialType.amaliy => 'tasks_json',
      };

  
  
  
  
  
  Color get color => switch (this) {
        MaterialType.konspekt => AppColors.konspekt,
        MaterialType.test => AppColors.test,
        MaterialType.prezentatsiya => AppColors.prezentatsiya,
        MaterialType.lektsiya => AppColors.lektsiya,
        MaterialType.amaliy => AppColors.amaliy,
      };

  
  
  
  Color get background => switch (this) {
        MaterialType.konspekt => AppColors.konspektBg,
        MaterialType.test => AppColors.testBg,
        MaterialType.prezentatsiya => AppColors.prezentatsiyaBg,
        MaterialType.lektsiya => AppColors.lektsiyaBg,
        MaterialType.amaliy => AppColors.amaliyBg,
      };

  
  
  IconData get icon => switch (this) {
        MaterialType.konspekt => Icons.menu_book_rounded,
        MaterialType.test => Icons.fact_check_rounded,
        MaterialType.prezentatsiya => Icons.slideshow_rounded,
        MaterialType.lektsiya => Icons.lightbulb_rounded,
        MaterialType.amaliy => Icons.assignment_rounded,
      };
}
