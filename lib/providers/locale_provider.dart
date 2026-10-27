import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';





class LocaleProvider extends ChangeNotifier {
  static const _kLocale = 'dastyor_locale';
  static const supported = [Locale('ru'), Locale('en'), Locale('tg')];

  Locale? _locale;
  Locale? get locale => _locale;
  bool get hasChosen => _locale != null;

  
  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final code = prefs.getString(_kLocale);
    if (code != null) _locale = Locale(code);
  }

  Future<void> setLocale(Locale locale) async {
    _locale = locale;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kLocale, locale.languageCode);
  }
}
