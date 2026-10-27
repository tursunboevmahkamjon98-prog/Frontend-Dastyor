



class AdminUserSummary {
  final String id;
  final String fullName;
  final String? email;
  final String? phone;
  final String role;
  final bool isPremium;
  final double balanceSomoni;
  final int konspektCount;
  final int testCount;
  final int presentationCount;
  final DateTime createdAt;
  
  
  
  final String? shortId;

  const AdminUserSummary({
    required this.id,
    required this.fullName,
    this.email,
    this.phone,
    required this.role,
    required this.isPremium,
    required this.balanceSomoni,
    required this.konspektCount,
    required this.testCount,
    required this.presentationCount,
    required this.createdAt,
    this.shortId,
  });

  int get totalMaterials => konspektCount + testCount + presentationCount;
  bool get isAdmin => role == 'admin';

  factory AdminUserSummary.fromJson(Map<String, dynamic> json) => AdminUserSummary(
        id: json['id'] as String,
        fullName: json['full_name'] as String? ?? '',
        email: json['email'] as String?,
        phone: json['phone'] as String?,
        role: json['role'] as String? ?? 'user',
        isPremium: json['is_premium'] as bool? ?? false,
        balanceSomoni: (json['balance_somoni'] as num?)?.toDouble() ?? 0,
        konspektCount: json['konspekt_count'] as int? ?? 0,
        testCount: json['test_count'] as int? ?? 0,
        presentationCount: json['presentation_count'] as int? ?? 0,
        createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
        shortId: json['short_id'] as String?,
      );

  AdminUserSummary copyWith({String? role, bool? isPremium, double? balanceSomoni}) => AdminUserSummary(
        id: id,
        fullName: fullName,
        email: email,
        phone: phone,
        role: role ?? this.role,
        isPremium: isPremium ?? this.isPremium,
        balanceSomoni: balanceSomoni ?? this.balanceSomoni,
        konspektCount: konspektCount,
        testCount: testCount,
        presentationCount: presentationCount,
        createdAt: createdAt,
        shortId: shortId,
      );
}
