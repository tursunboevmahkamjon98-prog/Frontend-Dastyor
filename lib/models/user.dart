class DastyorUser {
  final String id;
  final String fullName;
  final String? email;
  final String? phone;
  final bool phoneVerified;
  final String? avatarUrl;
  final String language;
  final String role;
  final bool isPremium;
  final double balanceSomoni;
  final DateTime createdAt;
  
  
  
  
  final String? shortId;

  const DastyorUser({
    required this.id,
    required this.fullName,
    this.email,
    this.phone,
    this.phoneVerified = false,
    this.avatarUrl,
    this.language = 'Русский',
    this.role = 'user',
    this.isPremium = false,
    this.balanceSomoni = 0,
    required this.createdAt,
    this.shortId,
  });

  factory DastyorUser.fromJson(Map<String, dynamic> json) => DastyorUser(
        id: json['id'] as String,
        fullName: json['full_name'] as String? ?? '',
        email: json['email'] as String?,
        phone: json['phone'] as String?,
        phoneVerified: json['phone_verified'] as bool? ?? false,
        avatarUrl: json['avatar_url'] as String?,
        language: json['language'] as String? ?? 'Русский',
        role: json['role'] as String? ?? 'user',
        isPremium: json['is_premium'] as bool? ?? false,
        
        
        balanceSomoni: (json['balance_somoni'] as num?)?.toDouble() ?? 0,
        createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
        shortId: json['short_id'] as String?,
      );

  DastyorUser copyWith({
    String? fullName,
    String? avatarUrl,
    String? language,
    bool? isPremium,
    double? balanceSomoni,
  }) =>
      DastyorUser(
        id: id,
        fullName: fullName ?? this.fullName,
        email: email,
        phone: phone,
        phoneVerified: phoneVerified,
        avatarUrl: avatarUrl ?? this.avatarUrl,
        language: language ?? this.language,
        role: role,
        isPremium: isPremium ?? this.isPremium,
        balanceSomoni: balanceSomoni ?? this.balanceSomoni,
        createdAt: createdAt,
        shortId: shortId,
      );
}
