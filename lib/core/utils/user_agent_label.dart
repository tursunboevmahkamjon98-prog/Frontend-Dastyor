






String userAgentLabel(String? userAgent) {
  if (userAgent == null || userAgent.isEmpty) return 'Noma\'lum brauzer';
  final ua = userAgent;

  final String browser;
  if (ua.contains('Edg/') || ua.contains('EdgA/')) {
    browser = 'Edge';
  } else if (ua.contains('OPR/') || ua.contains('Opera')) {
    browser = 'Opera';
  } else if (ua.contains('YaBrowser')) {
    browser = 'Yandex Browser';
  } else if (ua.contains('Firefox')) {
    browser = 'Firefox';
  } else if (ua.contains('Chrome')) {
    browser = 'Chrome';
  } else if (ua.contains('Safari')) {
    browser = 'Safari';
  } else {
    browser = 'Brauzer';
  }

  final String os;
  if (ua.contains('Windows')) {
    os = 'Windows';
  } else if (ua.contains('Mac OS')) {
    os = 'macOS';
  } else if (ua.contains('Android')) {
    os = 'Android';
  } else if (ua.contains('iPhone') || ua.contains('iPad')) {
    os = 'iOS';
  } else if (ua.contains('Linux')) {
    os = 'Linux';
  } else {
    os = '';
  }

  return os.isEmpty ? browser : '$browser — $os';
}
