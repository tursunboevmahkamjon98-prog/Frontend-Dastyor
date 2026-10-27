import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';




class OnboardingProvider extends ChangeNotifier {
  static const _kSeen = 'dastyor_onboarding_seen';

  bool _seen = false;
  bool get seen => _seen;

  
  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _seen = prefs.getBool(_kSeen) ?? false;
  }

  Future<void> markSeen() async {
    _seen = true;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kSeen, true);
  }
}
