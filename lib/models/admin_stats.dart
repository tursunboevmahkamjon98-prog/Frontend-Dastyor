
class AdminStats {
  final int totalUsers;
  final int totalKonspekts;
  final int totalTests;
  final int totalPresentations;
  final int totalMaterials;

  const AdminStats({
    required this.totalUsers,
    required this.totalKonspekts,
    required this.totalTests,
    required this.totalPresentations,
    required this.totalMaterials,
  });

  factory AdminStats.fromJson(Map<String, dynamic> json) => AdminStats(
        totalUsers: json['total_users'] as int? ?? 0,
        totalKonspekts: json['total_konspekts'] as int? ?? 0,
        totalTests: json['total_tests'] as int? ?? 0,
        totalPresentations: json['total_presentations'] as int? ?? 0,
        totalMaterials: json['total_materials'] as int? ?? 0,
      );
}
