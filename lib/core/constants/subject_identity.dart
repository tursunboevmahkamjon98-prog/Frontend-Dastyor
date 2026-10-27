import 'package:flutter/material.dart';



class SubjectIdentity {
  final String id;
  final String name;
  final String description;
  final Color primaryColor;
  final Color secondaryColor;
  final Color accentColor;
  final Gradient backgroundGradient;
  final IconData icon;
  final List<String> illustrationKeywords;
  final List<String> visualMetaphors;
  final String shapeLanguage; 
  final FontWeight titleWeight;
  final double borderRadius;
  final BoxShadow cardShadow;
  final List<Color> palette;

  const SubjectIdentity({
    required this.id,
    required this.name,
    required this.description,
    required this.primaryColor,
    required this.secondaryColor,
    required this.accentColor,
    required this.backgroundGradient,
    required this.icon,
    required this.illustrationKeywords,
    required this.visualMetaphors,
    required this.shapeLanguage,
    required this.titleWeight,
    required this.borderRadius,
    required this.cardShadow,
    required this.palette,
  });

  
  Color get lightBackground => primaryColor.withValues(alpha: 0.08);

  
  Color get mediumBorder => primaryColor.withValues(alpha: 0.25);

  
  Color get strongBorder => primaryColor.withValues(alpha: 0.6);
}


class SubjectIdentities {
  static const List<SubjectIdentity> all = [
    _biology,
    _chemistry,
    _physics,
    _mathematics,
    _algebra,
    _geometry,
    _history,
    _worldHistory,
    _geography,
    _tajikLanguage,
    _tajikLiterature,
    _russianLanguage,
    _englishLanguage,
    _informatics,
    _primarySchool,
  ];

  static const _biology = SubjectIdentity(
    id: 'biology',
    name: 'Biology',
    description: 'Life & Nature',
    primaryColor: Color(0xFF059669), 
    secondaryColor: Color(0xFF34D399),
    accentColor: Color(0xFF10B981),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFECFDF5), Color(0xFFD1FAE5)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.biotech_rounded,
    illustrationKeywords: ['cell', 'dna', 'plant', 'microscope', 'anatomy', 'ecosystem', 'organism', 'photosynthesis'],
    visualMetaphors: ['microscope view', 'cell structure', 'dna helix', 'leaf veins', 'food web', 'evolution tree'],
    shapeLanguage: 'organic',
    titleWeight: FontWeight.w700,
    borderRadius: 20,
    cardShadow: BoxShadow(
      color: Color(0xFF059669),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF064E3B), 
      Color(0xFF059669), 
      Color(0xFF10B981), 
      Color(0xFF34D399), 
      Color(0xFF6EE7B7), 
      Color(0xFFA7F3D0), 
      Color(0xFFD1FAE5), 
      Color(0xFFECFDF5), 
    ],
  );

  static const _chemistry = SubjectIdentity(
    id: 'chemistry',
    name: 'Chemistry',
    description: 'Matter & Reactions',
    primaryColor: Color(0xFF7C3AED), 
    secondaryColor: Color(0xFFA78BFA),
    accentColor: Color(0xFF8B5CF6),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFF5F3FF), Color(0xFFEDE9FE)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.science_rounded,
    illustrationKeywords: ['molecule', 'atom', 'laboratory', 'test tube', 'reaction', 'periodic table', 'bond', 'compound'],
    visualMetaphors: ['molecular structure', 'periodic table', 'reaction arrow', 'electron orbitals', 'beaker', 'crystal lattice'],
    shapeLanguage: 'geometric',
    titleWeight: FontWeight.w700,
    borderRadius: 18,
    cardShadow: BoxShadow(
      color: Color(0xFF7C3AED),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF4C1D95), 
      Color(0xFF7C3AED), 
      Color(0xFF8B5CF6), 
      Color(0xFFA78BFA), 
      Color(0xFFC4B5FD), 
      Color(0xFFDDD6FE), 
      Color(0xFFEDE9FE), 
      Color(0xFFF5F3FF), 
    ],
  );

  static const _physics = SubjectIdentity(
    id: 'physics',
    name: 'Physics',
    description: 'Energy & Motion',
    primaryColor: Color(0xFFEA580C), 
    secondaryColor: Color(0xFFF97316),
    accentColor: Color(0xFFF97316),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFFFF7ED), Color(0xFFFFEDD5)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.flash_on_rounded,
    illustrationKeywords: ['energy', 'electricity', 'motion', 'vector', 'graph', 'experiment', 'formula', 'wave'],
    visualMetaphors: ['lightning', 'wave form', 'vector field', 'circuit diagram', 'pendulum', 'ray diagram', 'force arrows'],
    shapeLanguage: 'technical',
    titleWeight: FontWeight.w800,
    borderRadius: 16,
    cardShadow: BoxShadow(
      color: Color(0xFFEA580C),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF9A3412), 
      Color(0xFFEA580C), 
      Color(0xFFF97316), 
      Color(0xFFFB923C), 
      Color(0xFFFDBA74), 
      Color(0xFFFFEDD5), 
      Color(0xFFFFF7ED), 
      Color(0xFFFFF1E6), 
    ],
  );

  static const _mathematics = SubjectIdentity(
    id: 'mathematics',
    name: 'Mathematics',
    description: 'Numbers & Patterns',
    primaryColor: Color(0xFF2563EB), 
    secondaryColor: Color(0xFF3B82F6),
    accentColor: Color(0xFF3B82F6),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFEFF6FF), Color(0xFFDBEAFE)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.calculate_rounded,
    illustrationKeywords: ['grid', 'numbers', 'equations', 'geometric shapes', 'graph', 'function', 'proof', 'theorem'],
    visualMetaphors: ['coordinate grid', 'geometric proof', 'number spiral', 'fractal', 'golden ratio', 'function plot'],
    shapeLanguage: 'geometric',
    titleWeight: FontWeight.w700,
    borderRadius: 16,
    cardShadow: BoxShadow(
      color: Color(0xFF2563EB),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF1E3A8A), 
      Color(0xFF2563EB), 
      Color(0xFF3B82F6), 
      Color(0xFF60A5FA), 
      Color(0xFF93C5FD), 
      Color(0xFFBFDBFE), 
      Color(0xFFDBEAFE), 
      Color(0xFFEFF6FF), 
    ],
  );

  static const _algebra = SubjectIdentity(
    id: 'algebra',
    name: 'Algebra',
    description: 'Equations & Variables',
    primaryColor: Color(0xFF1D4ED8), 
    secondaryColor: Color(0xFF3B82F6),
    accentColor: Color(0xFF3B82F6),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFEEF2FF), Color(0xFFE0E7FF)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.functions_rounded,
    illustrationKeywords: ['equation', 'variable', 'polynomial', 'graph', 'function', 'unknown', 'solve', 'formula'],
    visualMetaphors: ['balance scale', 'x-y axis', 'parabola', 'algebra tiles', 'equation steps'],
    shapeLanguage: 'geometric',
    titleWeight: FontWeight.w700,
    borderRadius: 16,
    cardShadow: BoxShadow(
      color: Color(0xFF1D4ED8),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF1E3A8A),
      Color(0xFF1D4ED8),
      Color(0xFF3B82F6),
      Color(0xFF60A5FA),
      Color(0xFF93C5FD),
      Color(0xFFC7D2FE),
      Color(0xFFE0E7FF),
      Color(0xFFEEF2FF),
    ],
  );

  static const _geometry = SubjectIdentity(
    id: 'geometry',
    name: 'Geometry',
    description: 'Shapes & Space',
    primaryColor: Color(0xFF0891B2), 
    secondaryColor: Color(0xFF06B6D4),
    accentColor: Color(0xFF06B6D4),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFECFEFF), Color(0xFFCFFAFE)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.crop_free_rounded,
    illustrationKeywords: ['triangle', 'circle', 'polygon', 'angle', 'proof', 'construction', '3d shape', 'transformation'],
    visualMetaphors: ['compass construction', 'geometric proof', 'platonic solids', 'tessellation', 'symmetry', 'transformation'],
    shapeLanguage: 'geometric',
    titleWeight: FontWeight.w700,
    borderRadius: 20,
    cardShadow: BoxShadow(
      color: Color(0xFF0891B2),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF164E63),
      Color(0xFF0891B2),
      Color(0xFF06B6D4),
      Color(0xFF22D3EE),
      Color(0xFF67E8F9),
      Color(0xFFA5F3FC),
      Color(0xFFCFFAFE),
      Color(0xFFECFEFF),
    ],
  );

  static const _history = SubjectIdentity(
    id: 'history_tajikistan',
    name: 'History of Tajikistan',
    description: 'Heritage & Civilization',
    primaryColor: Color(0xFFB45309), 
    secondaryColor: Color(0xFFD97706),
    accentColor: Color(0xFFF59E0B),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFFFFBEB), Color(0xFFFEF3C7)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.museum_rounded,
    illustrationKeywords: ['timeline', 'map', 'artifact', 'civilization', 'dynasty', 'monument', 'manuscript', 'ancient'],
    visualMetaphors: ['ancient scroll', 'timeline', 'map routes', 'archaeological layers', 'coin', 'architecture silhouette'],
    shapeLanguage: 'hand-drawn',
    titleWeight: FontWeight.w600,
    borderRadius: 22,
    cardShadow: BoxShadow(
      color: Color(0xFFB45309),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF78350F),
      Color(0xFFB45309),
      Color(0xFFD97706),
      Color(0xFFF59E0B),
      Color(0xFFFBBF24),
      Color(0xFFFDE68A),
      Color(0xFFFEF3C7),
      Color(0xFFFFFBEB),
    ],
  );

  static const _worldHistory = SubjectIdentity(
    id: 'world_history',
    name: 'World History',
    description: 'Global Civilizations',
    primaryColor: Color(0xFF92400E), 
    secondaryColor: Color(0xFFB45309),
    accentColor: Color(0xFFD97706),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFFDF8F0), Color(0xFFFAF0E0)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.public_rounded,
    illustrationKeywords: ['empire', 'revolution', 'trade route', 'war', 'treaty', 'civilization', 'era', 'monument'],
    visualMetaphors: ['world map', 'timeline', 'historical document', 'artifact', 'monument silhouette', 'era marker'],
    shapeLanguage: 'documentary',
    titleWeight: FontWeight.w600,
    borderRadius: 22,
    cardShadow: BoxShadow(
      color: Color(0xFF92400E),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF78350F),
      Color(0xFF92400E),
      Color(0xFFB45309),
      Color(0xFFD97706),
      Color(0xFFF59E0B),
      Color(0xFFFDE68A),
      Color(0xFFFEF3C7),
      Color(0xFFFFFBEB),
    ],
  );

  static const _geography = SubjectIdentity(
    id: 'geography',
    name: 'Geography',
    description: 'Earth & Places',
    primaryColor: Color(0xFF166534), 
    secondaryColor: Color(0xFF15803D),
    accentColor: Color(0xFF22C55E),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFF0FDF4), Color(0xFFDCFCE7)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.map_rounded,
    illustrationKeywords: ['map', 'globe', 'terrain', 'climate', 'country', 'river', 'mountain', 'population'],
    visualMetaphors: ['topographic map', 'globe', 'contour lines', 'climate zones', 'river system', 'compass rose'],
    shapeLanguage: 'organic',
    titleWeight: FontWeight.w700,
    borderRadius: 18,
    cardShadow: BoxShadow(
      color: Color(0xFF166534),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF14532D),
      Color(0xFF166534),
      Color(0xFF15803D),
      Color(0xFF22C55E),
      Color(0xFF4ADE80),
      Color(0xFF86EFAC),
      Color(0xFFBBF7D0),
      Color(0xFFDCFCE7),
    ],
  );

  static const _tajikLanguage = SubjectIdentity(
    id: 'tajik_language',
    name: 'Tajik Language',
    description: 'Grammar & Expression',
    primaryColor: Color(0xFFBE185D), 
    secondaryColor: Color(0xFFE11D48),
    accentColor: Color(0xFFF43F5E),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFFFF1F2), Color(0xFFFFE4E6)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.translate_rounded,
    illustrationKeywords: ['word', 'sentence', 'grammar', 'phonetics', 'morphology', 'text', 'reading', 'writing'],
    visualMetaphors: ['manuscript', 'letter forms', 'sentence diagram', 'word tree', 'calligraphy stroke', 'phonetic symbol'],
    shapeLanguage: 'hand-drawn',
    titleWeight: FontWeight.w600,
    borderRadius: 20,
    cardShadow: BoxShadow(
      color: Color(0xFFBE185D),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF881337),
      Color(0xFFBE185D),
      Color(0xFFE11D48),
      Color(0xFFF43F5E),
      Color(0xFFFB7185),
      Color(0xFFFDA4AF),
      Color(0xFFFECACA),
      Color(0xFFFFF1F2),
    ],
  );

  static const _tajikLiterature = SubjectIdentity(
    id: 'tajik_literature',
    name: 'Tajik Literature',
    description: 'Poetry & Prose',
    primaryColor: Color(0xFF701A75), 
    secondaryColor: Color(0xFF86198F),
    accentColor: Color(0xFFA21CAF),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFFAF5FF), Color(0xFFF3E8FF)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.menu_book_rounded,
    illustrationKeywords: ['poem', 'book', 'character', 'story', 'metaphor', 'verse', 'author', 'classic'],
    visualMetaphors: ['open book', 'quill', 'poetry lines', 'literary ornament', 'character portrait', 'story arc'],
    shapeLanguage: 'hand-drawn',
    titleWeight: FontWeight.w600,
    borderRadius: 22,
    cardShadow: BoxShadow(
      color: Color(0xFF701A75),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF581C87),
      Color(0xFF701A75),
      Color(0xFF86198F),
      Color(0xFFA21CAF),
      Color(0xFFD946EF),
      Color(0xFFE879F9),
      Color(0xFFF0ABFC),
      Color(0xFFF5D0FE),
    ],
  );

  static const _russianLanguage = SubjectIdentity(
    id: 'russian_language',
    name: 'Russian Language',
    description: 'Grammar & Speech',
    primaryColor: Color(0xFFDC2626), 
    secondaryColor: Color(0xFFEF4444),
    accentColor: Color(0xFFF87171),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFFEF2F2), Color(0xFFFEDEDE)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.text_fields_rounded,
    illustrationKeywords: ['word', 'sentence', 'grammar', 'case', 'verb', 'spelling', 'punctuation', 'text'],
    visualMetaphors: ['sentence diagram', 'grammar tree', 'word root', 'case table', 'punctuation marks', 'dictation'],
    shapeLanguage: 'technical',
    titleWeight: FontWeight.w700,
    borderRadius: 18,
    cardShadow: BoxShadow(
      color: Color(0xFFDC2626),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF7F1D1D),
      Color(0xFFDC2626),
      Color(0xFFEF4444),
      Color(0xFFF87171),
      Color(0xFFFCA5A5),
      Color(0xFFFECACA),
      Color(0xFFFEE2E2),
      Color(0xFFFEF2F2),
    ],
  );

  static const _englishLanguage = SubjectIdentity(
    id: 'english_language',
    name: 'English Language',
    description: 'Communication & Culture',
    primaryColor: Color(0xFF1D4ED8), 
    secondaryColor: Color(0xFF3B82F6),
    accentColor: Color(0xFF60A5FA),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFEFF6FF), Color(0xFFDBEAFE)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.language_rounded,
    illustrationKeywords: ['word', 'phrase', 'idiom', 'grammar', 'vocabulary', 'conversation', 'culture', 'media'],
    visualMetaphors: ['speech bubble', 'word cloud', 'dialogue', 'movie quote', 'song lyric', 'dictionary entry'],
    shapeLanguage: 'organic',
    titleWeight: FontWeight.w600,
    borderRadius: 20,
    cardShadow: BoxShadow(
      color: Color(0xFF1D4ED8),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF1E3A8A),
      Color(0xFF1D4ED8),
      Color(0xFF3B82F6),
      Color(0xFF60A5FA),
      Color(0xFF93C5FD),
      Color(0xFFBFDBFE),
      Color(0xFFDBEAFE),
      Color(0xFFEFF6FF),
    ],
  );

  static const _informatics = SubjectIdentity(
    id: 'informatics',
    name: 'Computer Science',
    description: 'Code & Logic',
    primaryColor: Color(0xFF0F172A), 
    secondaryColor: Color(0xFF1E293B),
    accentColor: Color(0xFF22D3EE), 
    backgroundGradient: LinearGradient(
      colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.computer_rounded,
    illustrationKeywords: ['algorithm', 'code', 'network', 'flowchart', 'data', 'binary', 'logic', 'program'],
    visualMetaphors: ['code snippet', 'flowchart', 'binary tree', 'network graph', 'terminal', 'circuit board', 'data flow'],
    shapeLanguage: 'technical',
    titleWeight: FontWeight.w700,
    borderRadius: 12,
    cardShadow: BoxShadow(
      color: Color(0xFF22D3EE),
      blurRadius: 20,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF020617),
      Color(0xFF0F172A),
      Color(0xFF1E293B),
      Color(0xFF22D3EE),
      Color(0xFF67E8F9),
      Color(0xFFA5F3FC),
      Color(0xFFE0F2FE),
      Color(0xFFF0F9FF),
    ],
  );

  static const _primarySchool = SubjectIdentity(
    id: 'primary_school',
    name: 'Primary School',
    description: 'Fun Learning',
    primaryColor: Color(0xFFEAB308), 
    secondaryColor: Color(0xFFFACC15),
    accentColor: Color(0xFFFDE047),
    backgroundGradient: LinearGradient(
      colors: [Color(0xFFFFFEF0), Color(0xFFFFFDDB)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    ),
    icon: Icons.child_friendly_rounded,
    illustrationKeywords: ['character', 'sticker', 'badge', 'animal', 'friend', 'game', 'story', 'discovery'],
    visualMetaphors: ['friendly character', 'sticker sheet', 'badge collection', 'storybook', 'playground', 'rainbow'],
    shapeLanguage: 'organic',
    titleWeight: FontWeight.w700,
    borderRadius: 24,
    cardShadow: BoxShadow(
      color: Color(0xFFEAB308),
      blurRadius: 24,
      offset: Offset(0, 10),
      spreadRadius: -4,
    ),
    palette: [
      Color(0xFF854D0E),
      Color(0xFFEAB308),
      Color(0xFFFACC15),
      Color(0xFFFDE047),
      Color(0xFFFEF08A),
      Color(0xFFFEF9C3),
      Color(0xFFFFFDDB),
      Color(0xFFFFFEF0),
    ],
  );

  
  static SubjectIdentity? getById(String id) {
    try {
      return all.firstWhere((s) => s.id == id);
    } catch (_) {
      return null;
    }
  }

  
  static SubjectIdentity? getByName(String name) {
    try {
      return all.firstWhere((s) => s.name.toLowerCase() == name.toLowerCase());
    } catch (_) {
      return null;
    }
  }

  
  static SubjectIdentity? fromBackendSubject(String backendSubject) {
    final normalized = backendSubject.toLowerCase().trim();
    for (final subject in all) {
      if (subject.name.toLowerCase() == normalized ||
          subject.id == normalized ||
          _aliases.containsKey(normalized) && _aliases[normalized] == subject.id) {
        return subject;
      }
    }
    
    for (final subject in all) {
      if (normalized.contains(subject.id) || subject.id.contains(normalized)) {
        return subject;
      }
    }
    return _mathematics; 
  }

  static const Map<String, String> _aliases = {
    'математика': 'mathematics',
    'алгебра': 'algebra',
    'геометрия': 'geometry',
    'физика': 'physics',
    'химия': 'chemistry',
    'биология': 'biology',
    'география': 'geography',
    'история таджикистана': 'history_tajikistan',
    'всемирная история': 'world_history',
    'таджикский язык': 'tajik_language',
    'таджикская литература': 'tajik_literature',
    'русский язык': 'russian_language',
    'английский язык': 'english_language',
    'информатика': 'informatics',
    'начальная школа': 'primary_school',
  };
}


extension SubjectIdentityExtension on String {
  SubjectIdentity get subjectIdentity => SubjectIdentities.fromBackendSubject(this) ?? SubjectIdentities._mathematics;
}