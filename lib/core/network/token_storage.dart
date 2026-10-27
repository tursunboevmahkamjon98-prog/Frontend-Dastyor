import 'package:flutter_secure_storage/flutter_secure_storage.dart';






class TokenStorage {
  TokenStorage._();
  static final TokenStorage instance = TokenStorage._();

  final _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static const _kAccess = 'dastyor_access_token';
  static const _kRefresh = 'dastyor_refresh_token';
  static const _kDevice = 'dastyor_device_token';

  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    await _storage.write(key: _kAccess, value: accessToken);
    await _storage.write(key: _kRefresh, value: refreshToken);
  }

  Future<String?> get accessToken => _storage.read(key: _kAccess);
  Future<String?> get refreshToken => _storage.read(key: _kRefresh);

  Future<void> saveAccessToken(String token) => _storage.write(key: _kAccess, value: token);

  
  
  
  
  Future<String?> get deviceToken => _storage.read(key: _kDevice);

  Future<void> saveDeviceToken(String token) => _storage.write(key: _kDevice, value: token);

  
  
  
  
  
  Future<void> clear() async {
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
  }

  
  
  Future<void> forgetDevice() => _storage.delete(key: _kDevice);
}
