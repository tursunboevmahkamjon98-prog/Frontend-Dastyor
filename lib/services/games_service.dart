import 'package:dio/dio.dart';
import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../models/quiz_question.dart';





class GamesService {
  final Dio _dio = ApiClient.instance.dio;

  
  
  
  
  
  
  Future<List<QuizQuestion>> generateQuizSet({
    required String topic,
    required String subject,
    required String grade,
    required String level,
    required int count,
    
    
    String language = 'Таджикский',
  }) async {
    try {
      final resp = await _dio.post(
        ApiConstants.quizSet,
        data: {
          'topic': topic,
          'subject': subject,
          'grade': grade,
          'level': level,
          'language': language,
          'count': count,
        },
        options: Options(receiveTimeout: ApiConstants.generateTimeout),
      );
      final raw = (resp.data as Map<String, dynamic>)['questions'] as List? ?? [];
      return raw
          .map((e) => QuizQuestion.fromJson(e as Map<String, dynamic>))
          .where((q) => q.isValid)
          
          
          
          
          .map((q) => q.shuffled())
          .toList();
    } catch (e) {
      throw toApiException(e);
    }
  }
}
