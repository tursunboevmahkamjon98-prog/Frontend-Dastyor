import 'dart:convert';
import 'material_type.dart';





class MaterialItem {
  final MaterialType type;
  final String id;
  final String title;
  final String subject;
  final String grade;
  final String? rawContent;
  final bool isFavorite;
  final bool hasUndo;
  final DateTime createdAt;
  final DateTime? updatedAt;

  const MaterialItem({
    required this.type,
    required this.id,
    required this.title,
    required this.subject,
    required this.grade,
    this.rawContent,
    this.isFavorite = false,
    this.hasUndo = false,
    required this.createdAt,
    this.updatedAt,
  });

  factory MaterialItem.fromJson(MaterialType type, Map<String, dynamic> json) => MaterialItem(
        type: type,
        id: json['id'] as String,
        title: json['title'] as String? ?? '',
        subject: json['subject'] as String? ?? '',
        grade: json['grade']?.toString() ?? '',
        rawContent: json[type.contentField] as String?,
        isFavorite: json['is_favorite'] as bool? ?? false,
        hasUndo: json['has_undo'] as bool? ?? false,
        createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
        updatedAt:
            json['updated_at'] != null ? DateTime.tryParse(json['updated_at'].toString()) : null,
      );

  
  
  
  
  dynamic get decodedContent {
    if (rawContent == null || rawContent!.trim().isEmpty) return null;
    try {
      return jsonDecode(rawContent!);
    } catch (_) {
      return null;
    }
  }

  MaterialItem copyWith({String? rawContent, bool? isFavorite, bool? hasUndo}) => MaterialItem(
        type: type,
        id: id,
        title: title,
        subject: subject,
        grade: grade,
        rawContent: rawContent ?? this.rawContent,
        isFavorite: isFavorite ?? this.isFavorite,
        hasUndo: hasUndo ?? this.hasUndo,
        createdAt: createdAt,
        updatedAt: updatedAt,
      );
}

class DashboardStats {
  final int konspektCount;
  final int testCount;
  final int presentationCount;
  final int lectureCount;
  final int practicalCount;

  const DashboardStats({
    this.konspektCount = 0,
    this.testCount = 0,
    this.presentationCount = 0,
    this.lectureCount = 0,
    this.practicalCount = 0,
  });

  factory DashboardStats.fromJson(Map<String, dynamic> json) => DashboardStats(
        konspektCount: json['konspekt_count'] as int? ?? 0,
        testCount: json['test_count'] as int? ?? 0,
        presentationCount: json['presentation_count'] as int? ?? 0,
        lectureCount: json['lecture_count'] as int? ?? 0,
        
        
        
        practicalCount: json['practical_count'] as int? ?? 0,
      );

  int get total =>
      konspektCount + testCount + presentationCount + lectureCount + practicalCount;
}
