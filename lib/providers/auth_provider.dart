import 'package:flutter/material.dart';
import '../core/network/api_client.dart';
import '../models/user.dart';
import '../services/auth_service.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }





class AuthProvider extends ChangeNotifier {
  final AuthService _authService = AuthService();

  AuthStatus _status = AuthStatus.unknown;
  DastyorUser? _user;

  AuthStatus get status => _status;
  DastyorUser? get user => _user;

  AuthProvider() {
    
    
    ApiClient.instance.onSessionExpired = _handleSessionExpired;
  }

  
  
  Future<void> initialize() async {
    _user = await _authService.tryRestoreSession();
    _status =
        _user != null ? AuthStatus.authenticated : AuthStatus.unauthenticated;
    notifyListeners();
  }

  Future<void> sendRegisterCode(String phone) =>
      _authService.sendRegisterCode(phone);

  Future<void> register({
    required String fullName,
    required String phone,
    required String code,
    required String password,
  }) async {
    _user = await _authService.register(
      fullName: fullName,
      phone: phone,
      code: code,
      password: password,
    );
    _status = AuthStatus.authenticated;
    notifyListeners();
  }

  
  
  
  Future<void> login({required String phone, required String password}) async {
    _user = await _authService.login(phone: phone, password: password);
    _status = AuthStatus.authenticated;
    notifyListeners();
  }

  
  
  
  
  Future<bool> loginSendCode(
      {required String phone, required String password}) async {
    final user =
        await _authService.loginSendCode(phone: phone, password: password);
    if (user == null) return true;
    _user = user;
    _status = AuthStatus.authenticated;
    notifyListeners();
    return false;
  }

  Future<void> loginVerify(
      {required String phone, required String code}) async {
    _user = await _authService.loginVerify(phone: phone, code: code);
    _status = AuthStatus.authenticated;
    notifyListeners();
  }

  
  
  
  
  
  
  Future<void> forgotPassword(String phone) =>
      _authService.forgotPassword(phone);

  Future<void> verifyResetCode({required String phone, required String code}) =>
      _authService.verifyResetCode(phone: phone, code: code);

  Future<void> resetPassword({
    required String phone,
    required String code,
    required String newPassword,
  }) =>
      _authService.resetPassword(
          phone: phone, code: code, newPassword: newPassword);

  Future<void> updateProfile({required String fullName}) async {
    _user = await _authService.updateProfile(fullName: fullName);
    notifyListeners();
  }

  
  
  
  
  Future<void> refreshUser() async {
    try {
      _user = await _authService.fetchMe();
      notifyListeners();
    } catch (_) {
      
    }
  }

  Future<void> logout() async {
    await _authService.logout();
    _handleSessionExpired();
  }

  void _handleSessionExpired() {
    _user = null;
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}
