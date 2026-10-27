import 'dart:math';








class QuizQuestion {
  final String question;
  final List<String> options;
  final int correctIndex;
  final String explanation;

  const QuizQuestion({
    required this.question,
    required this.options,
    required this.correctIndex,
    required this.explanation,
  });

  factory QuizQuestion.fromJson(Map<String, dynamic> json) => QuizQuestion(
        question: (json['question'] ?? '') as String,
        options: ((json['options'] ?? []) as List).map((e) => e.toString()).toList(),
        correctIndex: (json['correct_index'] ?? 0) as int,
        explanation: (json['explanation'] ?? '') as String,
      );

  
  
  
  
  
  
  
  
  QuizQuestion shuffled([Random? random]) {
    final rnd = random ?? Random();
    
    
    
    final order = List<int>.generate(options.length, (i) => i)..shuffle(rnd);
    return QuizQuestion(
      question: question,
      options: [for (final i in order) options[i]],
      correctIndex: order.indexOf(correctIndex),
      explanation: explanation,
    );
  }

  
  
  
  
  bool get isValid =>
      question.trim().isNotEmpty &&
      options.length >= 2 &&
      correctIndex >= 0 &&
      correctIndex < options.length;
}
