import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../models/material_item.dart';
import '../models/material_type.dart';


class MaterialsService {
  static const String _generateAllStream =
      '${ApiConstants.apiPrefix}/materials/generate-all-stream';

  final Dio _dio = ApiClient.instance.dio;

  Future<DashboardStats> getStats() async {
    try {
      final resp = await _dio.get(ApiConstants.stats);
      return DashboardStats.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw toApiException(e);
    }
  }

  
  
  
  
  
  Future<MaterialItem> generate({
    required MaterialType type,
    required String topic,
    required String subject,
    required String grade,
    required String level,
    required String language,
    int? slideCount,
    int? questionCount,
    String? testType,
    bool includeHomework = true,
    bool includeFunFacts = true,
    bool includeAssessment = true,
    String? sourceText,
    
    
    
    String? template,
  }) async {
    try {
      final resp = await _dio.post(
        ApiConstants.generate,
        data: {
          'material_type': type.apiMaterialType,
          'topic': topic,
          'subject': subject,
          'grade': grade,
          'level': level,
          'language': language,
          if (slideCount != null) 'slide_count': slideCount,
          if (questionCount != null) 'question_count': questionCount,
          if (testType != null) 'test_type': testType,
          'include_homework': includeHomework,
          'include_fun_facts': includeFunFacts,
          'include_assessment': includeAssessment,
          
          
          
          
          if (sourceText != null) 'source_text': sourceText,
          if (template != null) 'template': template,
        },
        options: Options(sendTimeout: ApiConstants.generateTimeout, receiveTimeout: ApiConstants.generateTimeout),
      );
      final data = resp.data as Map<String, dynamic>;
      final content = data['content'] as Map<String, dynamic>;
      return MaterialItem(
        type: type,
        id: data['id'] as String,
        title: (content['title'] as String?) ?? topic,
        subject: subject,
        grade: grade,
        
        
        
        
        rawContent: jsonEncode(content),
        createdAt: DateTime.now(),
      );
    } catch (e) {
      throw toApiException(e, context: 'generate');
    }
  }

  
  
  
  
  
  
  
  
  
  
  
  
  Future<Map<String, dynamic>> _readGenerateStream(ResponseBody body) async {
    final buffer = StringBuffer();
    Map<String, dynamic>? complete;
    String? failure;

    await for (final text in body.stream.cast<List<int>>().transform(utf8.decoder)) {
      buffer.write(text);
      var pending = buffer.toString();
      var index = pending.indexOf('\n\n');
      while (index != -1) {
        final frame = pending.substring(0, index);
        pending = pending.substring(index + 2);
        final line = frame
            .split('\n')
            .firstWhere((l) => l.startsWith('data:'), orElse: () => '');
        if (line.isNotEmpty) {
          final raw = line.substring('data:'.length).trim();
          if (raw.isNotEmpty) {
            final event = jsonDecode(raw) as Map<String, dynamic>;
            if (event['type'] == 'error') {
              failure = event['message'] as String?;
            } else if (event['type'] == 'complete') {
              complete = event;
            }
          }
        }
        index = pending.indexOf('\n\n');
      }
      buffer
        ..clear()
        ..write(pending);
    }

    if (failure != null) throw ApiException.generic(failure);
    if (complete == null) throw ApiException.network();
    return complete;
  }

  Future<GenerateAllResult> generateAll({
    required String topic,
    required String subject,
    required String grade,
    required String level,
    required String language,
    List<MaterialType>? types,
    int? slideCount,
    int? questionCount,
    String? testType,
  }) async {
    try {
      final resp = await _dio.post<ResponseBody>(
        _generateAllStream,
        data: {
          'topic': topic,
          'subject': subject,
          'language': language,
          'level': level,
          'grade': grade,
          if (slideCount != null) 'slide_count': slideCount,
          if (questionCount != null) 'question_count': questionCount,
          if (testType != null) 'test_type': testType,
          if (types != null && types.isNotEmpty)
            'types': types.map((t) => t.apiMaterialType).toList(),
        },
        options: Options(
          responseType: ResponseType.stream,
          sendTimeout: ApiConstants.generateTimeout,
          receiveTimeout: ApiConstants.generateTimeout,
        ),
      );
      final data = await _readGenerateStream(resp.data!);
      final ids = data['ids'] as Map<String, dynamic>? ?? {};
      final content = data['content'] as Map<String, dynamic>? ?? {};
      final items = <MaterialType, MaterialItem>{};
      for (final type in MaterialType.values) {
        final id = ids[type.apiMaterialType] as String?;
        final body = content[type.apiMaterialType] as Map<String, dynamic>?;
        if (id == null || body == null) continue;
        items[type] = MaterialItem(
          type: type,
          id: id,
          title: (body['title'] as String?) ?? topic,
          subject: subject,
          grade: grade,
          rawContent: jsonEncode(body),
          createdAt: DateTime.now(),
        );
      }
      final skipped = (data['skipped'] as List<dynamic>?)
              ?.map((s) => MaterialTypeX.fromApiValue(s as String))
              .toList() ??
          const <MaterialType>[];
      return GenerateAllResult(items: items, skipped: skipped);
    } catch (e) {
      throw toApiException(e, context: 'generate-all');
    }
  }

  
  
  
  
  
  Future<List<MaterialItem>> search({String query = '', String? subject, String? grade}) async {
    try {
      final resp = await _dio.get(ApiConstants.search, queryParameters: {
        'q': query,
        if (subject != null) 'subject': subject,
        if (grade != null) 'grade': grade,
      });
      final items = resp.data as List<dynamic>;
      return items
          .map((raw) {
            final json = raw as Map<String, dynamic>;
            return MaterialItem.fromJson(
              MaterialTypeX.fromApiValue(json['type'] as String),
              json,
            );
          })
          .toList();
    } catch (e) {
      throw toApiException(e);
    }
  }

  
  
  
  
  Future<MaterialItem> getOne(MaterialType type, String id) async {
    try {
      final resp =
          await _dio.get('${ApiConstants.apiPrefix}/materials/${type.apiSegment}/$id');
      return MaterialItem.fromJson(type, resp.data as Map<String, dynamic>);
    } catch (e) {
      throw toApiException(e);
    }
  }

  
  
  
  Future<void> setFavorite(MaterialType type, String id, bool value) async {
    try {
      await _dio.put(
        '${ApiConstants.apiPrefix}/materials/${type.apiSegment}/$id',
        data: {'is_favorite': value},
      );
    } catch (e) {
      throw toApiException(e);
    }
  }

  
  
  
  
  
  
  Future<void> updateContent(
      MaterialType type, String id, Map<String, dynamic> content) async {
    try {
      await _dio.put(
        '${ApiConstants.apiPrefix}/materials/${type.apiSegment}/$id',
        data: {'content': jsonEncode(content)},
      );
    } catch (e) {
      throw toApiException(e);
    }
  }

  
  Future<void> delete(MaterialType type, String id) async {
    try {
      await _dio.delete('${ApiConstants.apiPrefix}/materials/${type.apiSegment}/$id');
    } catch (e) {
      throw toApiException(e);
    }
  }

  
  
  
  
  
  Future<String> uploadSource({required String fileName, required Uint8List bytes}) async {
    try {
      final resp = await _dio.post(
        ApiConstants.uploadSource,
        data: FormData.fromMap({'file': MultipartFile.fromBytes(bytes, filename: fileName)}),
      );
      return resp.data['text'] as String;
    } catch (e) {
      throw toApiException(e, context: 'upload-source');
    }
  }

  Future<Uint8List> downloadDocx(MaterialItem item) => _download(ApiConstants.downloadDocx, item);

  Future<Uint8List> downloadPdf(MaterialItem item) => _download(ApiConstants.downloadPdf, item);

  
  
  Future<Uint8List> downloadPptx(MaterialItem item) => _download(ApiConstants.downloadPptx, item);

  
  
  
  
  Future<Uint8List> _download(String path, MaterialItem item) async {
    try {
      final content = item.decodedContent as Map<String, dynamic>?;
      if (content == null) throw ApiException.generic();
      final resp = await _dio.post<List<int>>(
        path,
        data: {
          'material_type': item.type.apiMaterialType,
          'content': content,
          'language': content['language'] as String? ?? 'Русский',
        },
        options: Options(responseType: ResponseType.bytes),
      );
      return Uint8List.fromList(resp.data!);
    } catch (e) {
      throw toApiException(e);
    }
  }
}





class GenerateAllResult {
  const GenerateAllResult({required this.items, required this.skipped});

  final Map<MaterialType, MaterialItem> items;
  final List<MaterialType> skipped;
}
