import 'package:flutter/widgets.dart';
import '../../l10n/gen/app_localizations.dart';
import 'api_exception.dart';




String messageFor(BuildContext context, ApiException e) {
  final t = AppLocalizations.of(context);
  switch (e.messageKey) {
    case 'errorNetwork':
      return t.errorNetwork;
    case 'errorPhoneInvalid':
      return t.errorPhoneInvalid;
    case 'errorPhoneTaken':
      return t.errorPhoneTaken;
    case 'errorInvalidCredentials':
      return t.errorInvalidCredentials;
    case 'errorTooManyAttempts':
      return t.errorTooManyAttempts;
    case 'errorSessionExpired':
      return t.errorSessionExpired;
    case 'otpInvalid':
      return t.otpInvalid;
    case 'freeLimitReachedDesc':
      return t.freeLimitReachedDesc;
    case 'errorInsufficientBalance':
      return t.errorInsufficientBalance;
    case 'errorGeneric':
    default:
      return e.serverMessage?.trim().isNotEmpty == true ? e.serverMessage! : t.errorGeneric;
  }
}
