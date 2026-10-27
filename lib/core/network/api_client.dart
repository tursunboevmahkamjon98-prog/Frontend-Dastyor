import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import '../constants/api_constants.dart';
import 'api_exception.dart';
import 'token_storage.dart';










class ApiClient {
  ApiClient._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConstants.baseUrl,
      connectTimeout: ApiConstants.connectTimeout,
      receiveTimeout: ApiConstants.receiveTimeout,
      
      
      
      headers: {
        'Content-Type': 'application/json',
        'X-Client-Platform': kIsWeb ? 'web' : 'mobile',
      },
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (!options.extra.containsKey('noAuth')) {
          final token = await TokenStorage.instance.accessToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final isAuthCall = error.requestOptions.path.contains('/auth/login') ||
            error.requestOptions.path.contains('/auth/register') ||
            error.requestOptions.path.contains('/auth/refresh');
        if (error.response?.statusCode == 401 && !isAuthCall) {
          final refreshed = await _tryRefresh();
          if (refreshed) {
            try {
              final cloned = await _retry(error.requestOptions);
              return handler.resolve(cloned);
            } catch (_) {
              
            }
          }
          await TokenStorage.instance.clear();
          onSessionExpired?.call();
        }
        handler.next(error);
      },
    ));
  }

  static final ApiClient instance = ApiClient._internal();
  late final Dio _dio;
  Dio get dio => _dio;

  
  
  
  void Function()? onSessionExpired;

  bool _refreshing = false;
  Future<bool>? _refreshFuture;

  Future<bool> _tryRefresh() {
    
    
    
    
    if (_refreshing) return _refreshFuture!;
    _refreshing = true;
    _refreshFuture = _doRefresh().whenComplete(() => _refreshing = false);
    return _refreshFuture!;
  }

  Future<bool> _doRefresh() async {
    final refreshToken = await TokenStorage.instance.refreshToken;
    if (refreshToken == null) return false;
    try {
      final resp = await _dio.post(
        ApiConstants.refresh,
        data: {'refresh_token': refreshToken},
        options: Options(extra: {'noAuth': true}),
      );
      final newAccess = resp.data['access_token'] as String;
      final newRefresh = resp.data['refresh_token'] as String;
      await TokenStorage.instance.saveTokens(accessToken: newAccess, refreshToken: newRefresh);
      return true;
    } catch (_) {
      final current = await TokenStorage.instance.refreshToken;
      return current != null && current != refreshToken;
    }
  }

  Future<Response> _retry(RequestOptions requestOptions) async {
    final token = await TokenStorage.instance.accessToken;
    final options = Options(method: requestOptions.method, headers: {
      ...requestOptions.headers,
      'Authorization': 'Bearer $token',
    });
    return _dio.request(
      requestOptions.path,
      data: requestOptions.data,
      queryParameters: requestOptions.queryParameters,
      options: options,
    );
  }
}




ApiException toApiException(Object error, {String context = ''}) {
  if (error is ApiException) return error;
  if (error is! DioException) return ApiException.generic();

  if (error.type == DioExceptionType.connectionError ||
      error.type == DioExceptionType.connectionTimeout ||
      error.type == DioExceptionType.receiveTimeout ||
      error.type == DioExceptionType.sendTimeout) {
    return ApiException.network();
  }

  final status = error.response?.statusCode;
  final detail = _extractDetail(error.response?.data);

  if (status == 429) {
    return ApiException('errorTooManyAttempts', serverMessage: detail, statusCode: status);
  }
  if (status == 401) {
    if (context == 'login') {
      return ApiException('errorInvalidCredentials', serverMessage: detail, statusCode: status);
    }
    return ApiException('errorSessionExpired', serverMessage: detail, statusCode: status);
  }
  if (status == 400 && context == 'register-phone') {
    return ApiException('errorPhoneTaken', serverMessage: detail, statusCode: status);
  }
  if (status == 400 && context == 'otp') {
    return ApiException('otpInvalid', serverMessage: detail, statusCode: status);
  }
  if (status == 402) {
    
    
    
    
    return ApiException('errorInsufficientBalance', serverMessage: detail, statusCode: status);
  }
  return ApiException.generic(detail);
}

String? _extractDetail(dynamic data) {
  if (data is Map && data['detail'] is String) return data['detail'] as String;
  return null;
}
