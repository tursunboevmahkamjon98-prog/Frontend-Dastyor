import 'package:dio/dio.dart';
import '../core/network/api_client.dart';
import '../core/constants/api_constants.dart';
import '../core/network/token_storage.dart';
import '../models/user.dart';






class AuthService {
  final Dio _dio = ApiClient.instance.dio;

  Future<void> sendRegisterCode(String phone) async {
    try {
      await _dio.post(
        ApiConstants.registerSendCode,
        data: {'phone': phone},
        options: Options(extra: {'noAuth': true}),
      );
    } catch (e) {
      throw toApiException(e, context: 'register-phone');
    }
  }

  Future<DastyorUser> register({
    required String fullName,
    required String phone,
    required String code,
    required String password,
  }) async {
    try {
      final resp = await _dio.post(
        ApiConstants.register,
        data: {
          'full_name': fullName,
          'phone': phone,
          'code': code,
          'password': password
        },
        options: Options(extra: {'noAuth': true}),
      );
      return _saveAndReturnUser(resp.data);
    } catch (e) {
      throw toApiException(e, context: 'otp');
    }
  }

  
  
  
  
  
  
  
  
  
  
  Future<DastyorUser?> loginSendCode(
      {required String phone, required String password}) async {
    try {
      final resp = await _dio.post(
        ApiConstants.loginSendCode,
        data: {
          'phone': phone,
          'password': password,
          'device_token': await TokenStorage.instance.deviceToken,
        },
        options: Options(extra: {'noAuth': true}),
      );
      final data = resp.data as Map<String, dynamic>;
      if (data['access_token'] == null) return null; 
      return _saveAndReturnUser(data);
    } catch (e) {
      throw toApiException(e, context: 'login');
    }
  }

  
  
  
  
  
  
  
  
  
  
  
  
  
  Future<DastyorUser> login(
      {required String phone, required String password}) async {
    try {
      final resp = await _dio.post(
        ApiConstants.login,
        data: {'phone': phone, 'password': password},
        options: Options(extra: {'noAuth': true}),
      );
      return _saveAndReturnUser(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw toApiException(e, context: 'login');
    }
  }

  
  
  
  Future<DastyorUser> loginVerify(
      {required String phone, required String code}) async {
    try {
      final resp = await _dio.post(
        ApiConstants.loginVerify,
        data: {'phone': phone, 'code': code},
        options: Options(extra: {'noAuth': true}),
      );
      final data = resp.data as Map<String, dynamic>;
      final deviceToken = data['device_token'] as String?;
      if (deviceToken != null) {
        await TokenStorage.instance.saveDeviceToken(deviceToken);
      }
      return _saveAndReturnUser(data);
    } catch (e) {
      throw toApiException(e, context: 'otp');
    }
  }

  Future<void> forgotPassword(String phone) async {
    try {
      await _dio.post(
        ApiConstants.forgotPassword,
        data: {'phone': phone},
        options: Options(extra: {'noAuth': true}),
      );
    } catch (e) {
      throw toApiException(e);
    }
  }

  Future<void> verifyResetCode(
      {required String phone, required String code}) async {
    try {
      await _dio.post(
        ApiConstants.verifyCode,
        data: {'phone': phone, 'code': code},
        options: Options(extra: {'noAuth': true}),
      );
    } catch (e) {
      throw toApiException(e, context: 'otp');
    }
  }

  Future<void> resetPassword({
    required String phone,
    required String code,
    required String newPassword,
  }) async {
    try {
      await _dio.post(
        ApiConstants.resetPassword,
        data: {'phone': phone, 'code': code, 'new_password': newPassword},
        options: Options(extra: {'noAuth': true}),
      );
    } catch (e) {
      throw toApiException(e, context: 'otp');
    }
  }

  Future<DastyorUser?> tryRestoreSession() async {
    final token = await TokenStorage.instance.accessToken;
    if (token == null) return null;
    try {
      final resp = await _dio.get(ApiConstants.me);
      return DastyorUser.fromJson(resp.data as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  
  
  
  
  
  Future<DastyorUser> fetchMe() async {
    try {
      final resp = await _dio.get(ApiConstants.me);
      return DastyorUser.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw toApiException(e);
    }
  }

  
  
  
  Future<DastyorUser> updateProfile({required String fullName}) async {
    try {
      final resp =
          await _dio.put(ApiConstants.me, data: {'full_name': fullName});
      return DastyorUser.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw toApiException(e);
    }
  }

  Future<void> logout() async {
    final refreshToken = await TokenStorage.instance.refreshToken;
    try {
      if (refreshToken != null) {
        await _dio
            .post(ApiConstants.logout, data: {'refresh_token': refreshToken});
      }
    } catch (_) {
      
    } finally {
      await TokenStorage.instance.clear();
    }
  }

  Future<DastyorUser> _saveAndReturnUser(Map<String, dynamic> data) async {
    await TokenStorage.instance.saveTokens(
      accessToken: data['access_token'] as String,
      refreshToken: data['refresh_token'] as String,
    );
    return DastyorUser.fromJson(data['user'] as Map<String, dynamic>);
  }
}
