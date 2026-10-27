










class ApiException implements Exception {
  final String messageKey;
  final String? serverMessage;
  final int? statusCode;
  final bool isNetworkError;

  const ApiException(
    this.messageKey, {
    this.serverMessage,
    this.statusCode,
    this.isNetworkError = false,
  });

  factory ApiException.network() => const ApiException('errorNetwork', isNetworkError: true);

  factory ApiException.generic([String? serverMessage]) =>
      ApiException('errorGeneric', serverMessage: serverMessage);

  @override
  String toString() => serverMessage ?? messageKey;
}
