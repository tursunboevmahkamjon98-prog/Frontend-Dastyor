import 'package:dio/dio.dart';
import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../models/admin_stats.dart';
import '../models/admin_user.dart';





class AdminService {
  final Dio _dio = ApiClient.instance.dio;

  Future<AdminStats> getStats() async {
    try {
      final resp = await _dio.get(ApiConstants.adminStats);
      return AdminStats.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw toApiException(e);
    }
  }

  Future<List<AdminUserSummary>> listUsers({String query = ''}) async {
    try {
      final resp = await _dio.get(
        ApiConstants.adminUsers,
        queryParameters: query.isEmpty ? null : {'q': query},
      );
      final items = resp.data as List<dynamic>;
      return items
          .map((raw) => AdminUserSummary.fromJson(raw as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw toApiException(e);
    }
  }

  Future<AdminUserSummary> setRole(String userId, String role) async {
    try {
      final resp = await _dio.put(ApiConstants.adminUserRole(userId), data: {'role': role});
      return AdminUserSummary.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw toApiException(e);
    }
  }

  Future<AdminUserSummary> setPremium(String userId, bool isPremium) async {
    try {
      final resp =
          await _dio.put(ApiConstants.adminUserPremium(userId), data: {'is_premium': isPremium});
      return AdminUserSummary.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw toApiException(e);
    }
  }

  Future<AdminUserSummary> addBalance(String userId, double amountSomoni) async {
    try {
      final resp = await _dio
          .put(ApiConstants.adminUserBalance(userId), data: {'amount_somoni': amountSomoni});
      return AdminUserSummary.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw toApiException(e);
    }
  }

  Future<void> deleteUser(String userId) async {
    try {
      await _dio.delete(ApiConstants.adminUserDelete(userId));
    } catch (e) {
      throw toApiException(e);
    }
  }
}
