


class Validators {
  Validators._();

  static final _nonPhoneChars = RegExp(r'[^\d+]');

  
  
  static String normalizePhone(String raw) {
    final cleaned = raw.trim().replaceAll(_nonPhoneChars, '');
    return cleaned.startsWith('+') ? cleaned : '+$cleaned';
  }

  static bool isValidPhone(String raw) => RegExp(r'^\+\d{9,15}$').hasMatch(normalizePhone(raw));

  static bool isValidPassword(String value) => value.length >= 6;

  static bool isValidName(String value) => value.trim().length >= 2;
}
