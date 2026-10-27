import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ru.dart';
import 'app_localizations_tg.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'gen/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ru'),
    Locale('tg')
  ];

  /// No description provided for @appName.
  ///
  /// In ru, this message translates to:
  /// **'Dastyor'**
  String get appName;

  /// No description provided for @appTagline.
  ///
  /// In ru, this message translates to:
  /// **'Конспект, тест, презентация и лекция — за секунды, с помощью ИИ'**
  String get appTagline;

  /// No description provided for @authSideBullet2.
  ///
  /// In ru, this message translates to:
  /// **'Готово за секунды благодаря ИИ'**
  String get authSideBullet2;

  /// No description provided for @authSideBullet3.
  ///
  /// In ru, this message translates to:
  /// **'Создавайте на телефоне — печатайте с компьютера'**
  String get authSideBullet3;

  /// No description provided for @chooseLanguageTitle.
  ///
  /// In ru, this message translates to:
  /// **'Выберите язык'**
  String get chooseLanguageTitle;

  /// No description provided for @chooseLanguageSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Вы всегда сможете изменить его в настройках'**
  String get chooseLanguageSubtitle;

  /// No description provided for @continueBtn.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить'**
  String get continueBtn;

  /// No description provided for @skip.
  ///
  /// In ru, this message translates to:
  /// **'Пропустить'**
  String get skip;

  /// No description provided for @getStarted.
  ///
  /// In ru, this message translates to:
  /// **'Начать'**
  String get getStarted;

  /// No description provided for @next.
  ///
  /// In ru, this message translates to:
  /// **'Далее'**
  String get next;

  /// No description provided for @back.
  ///
  /// In ru, this message translates to:
  /// **'Назад'**
  String get back;

  /// No description provided for @onboardTitle1.
  ///
  /// In ru, this message translates to:
  /// **'Материалы за секунды'**
  String get onboardTitle1;

  /// No description provided for @onboardDesc1.
  ///
  /// In ru, this message translates to:
  /// **'Конспект, тест, презентация и лекция готовятся за считанные секунды — не часы'**
  String get onboardDesc1;

  /// No description provided for @onboardTitle2.
  ///
  /// In ru, this message translates to:
  /// **'На основе учебника или ИИ'**
  String get onboardTitle2;

  /// No description provided for @onboardDesc2.
  ///
  /// In ru, this message translates to:
  /// **'Каждый материал можно создать по вашему учебнику или с помощью искусственного интеллекта'**
  String get onboardDesc2;

  /// No description provided for @onboardTitle3.
  ///
  /// In ru, this message translates to:
  /// **'На 3 языках'**
  String get onboardTitle3;

  /// No description provided for @onboardDesc3.
  ///
  /// In ru, this message translates to:
  /// **'Приложение и материалы доступны на русском, английском и таджикском'**
  String get onboardDesc3;

  /// No description provided for @qrLoginTitle.
  ///
  /// In ru, this message translates to:
  /// **'Вход через приложение'**
  String get qrLoginTitle;

  /// No description provided for @qrLoginStep1.
  ///
  /// In ru, this message translates to:
  /// **'Откройте приложение Dastyor на телефоне'**
  String get qrLoginStep1;

  /// No description provided for @qrLoginStep2.
  ///
  /// In ru, this message translates to:
  /// **'Перейдите в Профиль → «Вход на компьютере»'**
  String get qrLoginStep2;

  /// No description provided for @qrLoginStep3.
  ///
  /// In ru, this message translates to:
  /// **'Наведите камеру на этот QR-код'**
  String get qrLoginStep3;

  /// No description provided for @qrLoginError.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось создать QR-код'**
  String get qrLoginError;

  /// No description provided for @qrLoginRetry.
  ///
  /// In ru, this message translates to:
  /// **'Обновить код'**
  String get qrLoginRetry;

  /// No description provided for @qrScanTitle.
  ///
  /// In ru, this message translates to:
  /// **'Сканировать QR-код'**
  String get qrScanTitle;

  /// No description provided for @qrScanHint.
  ///
  /// In ru, this message translates to:
  /// **'Наведите камеру на QR-код на экране компьютера'**
  String get qrScanHint;

  /// No description provided for @qrScanConfirmTitle.
  ///
  /// In ru, this message translates to:
  /// **'Войти на компьютере?'**
  String get qrScanConfirmTitle;

  /// No description provided for @qrScanConfirmDesc.
  ///
  /// In ru, this message translates to:
  /// **'Вы подтверждаете вход в свой аккаунт Dastyor на другом устройстве.'**
  String get qrScanConfirmDesc;

  /// No description provided for @qrScanConfirmButton.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердить'**
  String get qrScanConfirmButton;

  /// No description provided for @qrScanSuccess.
  ///
  /// In ru, this message translates to:
  /// **'Вы вошли на компьютере'**
  String get qrScanSuccess;

  /// No description provided for @qrScanInvalid.
  ///
  /// In ru, this message translates to:
  /// **'Это не QR-код для входа Dastyor'**
  String get qrScanInvalid;

  /// No description provided for @profileLoginOnComputer.
  ///
  /// In ru, this message translates to:
  /// **'Вход на компьютере'**
  String get profileLoginOnComputer;

  /// No description provided for @profileLinkedDevices.
  ///
  /// In ru, this message translates to:
  /// **'Связанные устройства'**
  String get profileLinkedDevices;

  /// No description provided for @linkedDevicesTitle.
  ///
  /// In ru, this message translates to:
  /// **'Связанные устройства'**
  String get linkedDevicesTitle;

  /// No description provided for @linkedDevicesEmptyTitle.
  ///
  /// In ru, this message translates to:
  /// **'Нет связанных устройств'**
  String get linkedDevicesEmptyTitle;

  /// No description provided for @linkedDevicesEmptySubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Здесь появятся браузеры, где вы вошли через QR-код или по номеру телефона'**
  String get linkedDevicesEmptySubtitle;

  /// No description provided for @linkedDevicesLoggedInAt.
  ///
  /// In ru, this message translates to:
  /// **'Вход выполнен {date}'**
  String linkedDevicesLoggedInAt(String date);

  /// No description provided for @linkedDevicesLogoutTitle.
  ///
  /// In ru, this message translates to:
  /// **'Выйти на этом устройстве?'**
  String get linkedDevicesLogoutTitle;

  /// No description provided for @welcomeBack.
  ///
  /// In ru, this message translates to:
  /// **'С возвращением'**
  String get welcomeBack;

  /// No description provided for @welcomeBackSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Войдите, чтобы продолжить работу'**
  String get welcomeBackSubtitle;

  /// No description provided for @createAccount.
  ///
  /// In ru, this message translates to:
  /// **'Создать аккаунт'**
  String get createAccount;

  /// No description provided for @createAccountSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Зарегистрируйтесь по номеру телефона'**
  String get createAccountSubtitle;

  /// No description provided for @fullName.
  ///
  /// In ru, this message translates to:
  /// **'Полное имя'**
  String get fullName;

  /// No description provided for @fullNameHint.
  ///
  /// In ru, this message translates to:
  /// **'Например, Азиз Раҳимов'**
  String get fullNameHint;

  /// No description provided for @phoneNumber.
  ///
  /// In ru, this message translates to:
  /// **'Номер телефона'**
  String get phoneNumber;

  /// No description provided for @password.
  ///
  /// In ru, this message translates to:
  /// **'Пароль'**
  String get password;

  /// No description provided for @confirmPassword.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердите пароль'**
  String get confirmPassword;

  /// No description provided for @currentPassword.
  ///
  /// In ru, this message translates to:
  /// **'Текущий пароль'**
  String get currentPassword;

  /// No description provided for @newPassword.
  ///
  /// In ru, this message translates to:
  /// **'Новый пароль'**
  String get newPassword;

  /// No description provided for @confirmNewPassword.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердите новый пароль'**
  String get confirmNewPassword;

  /// No description provided for @login.
  ///
  /// In ru, this message translates to:
  /// **'Войти'**
  String get login;

  /// No description provided for @register.
  ///
  /// In ru, this message translates to:
  /// **'Зарегистрироваться'**
  String get register;

  /// No description provided for @loginWithQrInstead.
  ///
  /// In ru, this message translates to:
  /// **'Войти через QR-код'**
  String get loginWithQrInstead;

  /// No description provided for @qrLoginUsePhoneInstead.
  ///
  /// In ru, this message translates to:
  /// **'Войти по номеру телефона'**
  String get qrLoginUsePhoneInstead;

  /// No description provided for @logout.
  ///
  /// In ru, this message translates to:
  /// **'Выйти'**
  String get logout;

  /// No description provided for @dontHaveAccount.
  ///
  /// In ru, this message translates to:
  /// **'Нет аккаунта?'**
  String get dontHaveAccount;

  /// No description provided for @alreadyHaveAccount.
  ///
  /// In ru, this message translates to:
  /// **'Уже есть аккаунт?'**
  String get alreadyHaveAccount;

  /// No description provided for @forgotPassword.
  ///
  /// In ru, this message translates to:
  /// **'Забыли пароль?'**
  String get forgotPassword;

  /// No description provided for @sendCode.
  ///
  /// In ru, this message translates to:
  /// **'Отправить код'**
  String get sendCode;

  /// No description provided for @otpTitle.
  ///
  /// In ru, this message translates to:
  /// **'Введите код'**
  String get otpTitle;

  /// No description provided for @otpSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Мы отправили 6-значный код на'**
  String get otpSubtitle;

  /// No description provided for @otpResendQuestion.
  ///
  /// In ru, this message translates to:
  /// **'Не пришёл код?'**
  String get otpResendQuestion;

  /// No description provided for @otpResend.
  ///
  /// In ru, this message translates to:
  /// **'Отправить повторно'**
  String get otpResend;

  /// No description provided for @otpResendIn.
  ///
  /// In ru, this message translates to:
  /// **'Повторно через {seconds} с'**
  String otpResendIn(int seconds);

  /// No description provided for @otpVerify.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердить'**
  String get otpVerify;

  /// No description provided for @otpInvalid.
  ///
  /// In ru, this message translates to:
  /// **'Неверный код'**
  String get otpInvalid;

  /// No description provided for @resetPasswordTitle.
  ///
  /// In ru, this message translates to:
  /// **'Новый пароль'**
  String get resetPasswordTitle;

  /// No description provided for @resetPasswordSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Придумайте новый пароль для входа'**
  String get resetPasswordSubtitle;

  /// No description provided for @resetPasswordButton.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить пароль'**
  String get resetPasswordButton;

  /// No description provided for @passwordChangedSuccess.
  ///
  /// In ru, this message translates to:
  /// **'Пароль успешно изменён'**
  String get passwordChangedSuccess;

  /// No description provided for @errorRequired.
  ///
  /// In ru, this message translates to:
  /// **'Обязательное поле'**
  String get errorRequired;

  /// No description provided for @errorPhoneInvalid.
  ///
  /// In ru, this message translates to:
  /// **'Введите номер в формате +992 XX XXX XXXX'**
  String get errorPhoneInvalid;

  /// No description provided for @errorPasswordShort.
  ///
  /// In ru, this message translates to:
  /// **'Минимум 6 символов'**
  String get errorPasswordShort;

  /// No description provided for @errorPasswordMismatch.
  ///
  /// In ru, this message translates to:
  /// **'Пароли не совпадают'**
  String get errorPasswordMismatch;

  /// No description provided for @errorNameShort.
  ///
  /// In ru, this message translates to:
  /// **'Введите имя и фамилию'**
  String get errorNameShort;

  /// No description provided for @errorNetwork.
  ///
  /// In ru, this message translates to:
  /// **'Нет соединения с сервером. Проверьте интернет'**
  String get errorNetwork;

  /// No description provided for @errorGeneric.
  ///
  /// In ru, this message translates to:
  /// **'Что-то пошло не так. Попробуйте снова'**
  String get errorGeneric;

  /// No description provided for @errorPhoneTaken.
  ///
  /// In ru, this message translates to:
  /// **'Этот номер уже зарегистрирован'**
  String get errorPhoneTaken;

  /// No description provided for @errorInvalidCredentials.
  ///
  /// In ru, this message translates to:
  /// **'Неверный номер телефона или пароль'**
  String get errorInvalidCredentials;

  /// No description provided for @errorTooManyAttempts.
  ///
  /// In ru, this message translates to:
  /// **'Слишком много попыток. Подождите немного'**
  String get errorTooManyAttempts;

  /// No description provided for @errorSessionExpired.
  ///
  /// In ru, this message translates to:
  /// **'Сессия истекла. Войдите снова'**
  String get errorSessionExpired;

  /// No description provided for @dashboardGreetingMorning.
  ///
  /// In ru, this message translates to:
  /// **'Доброе утро, {name}!'**
  String dashboardGreetingMorning(String name);

  /// No description provided for @dashboardGreetingDay.
  ///
  /// In ru, this message translates to:
  /// **'Добрый день, {name}!'**
  String dashboardGreetingDay(String name);

  /// No description provided for @dashboardGreetingEvening.
  ///
  /// In ru, this message translates to:
  /// **'Добрый вечер, {name}!'**
  String dashboardGreetingEvening(String name);

  /// No description provided for @dashboardSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Что подготовим сегодня?'**
  String get dashboardSubtitle;

  /// No description provided for @quickCreate.
  ///
  /// In ru, this message translates to:
  /// **'Создать материал'**
  String get quickCreate;

  /// No description provided for @recentMaterials.
  ///
  /// In ru, this message translates to:
  /// **'Недавние материалы'**
  String get recentMaterials;

  /// No description provided for @viewAll.
  ///
  /// In ru, this message translates to:
  /// **'Все'**
  String get viewAll;

  /// No description provided for @emptyMaterialsTitle.
  ///
  /// In ru, this message translates to:
  /// **'Пока нет материалов'**
  String get emptyMaterialsTitle;

  /// No description provided for @emptyMaterialsSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Создайте первый конспект, тест, презентацию или лекцию'**
  String get emptyMaterialsSubtitle;

  /// No description provided for @navHome.
  ///
  /// In ru, this message translates to:
  /// **'Главная'**
  String get navHome;

  /// No description provided for @navMaterials.
  ///
  /// In ru, this message translates to:
  /// **'Материалы'**
  String get navMaterials;

  /// No description provided for @navCreate.
  ///
  /// In ru, this message translates to:
  /// **'Создать'**
  String get navCreate;

  /// No description provided for @navProfile.
  ///
  /// In ru, this message translates to:
  /// **'Профиль'**
  String get navProfile;

  /// No description provided for @typeKonspekt.
  ///
  /// In ru, this message translates to:
  /// **'Конспект'**
  String get typeKonspekt;

  /// No description provided for @typeTest.
  ///
  /// In ru, this message translates to:
  /// **'Тест'**
  String get typeTest;

  /// No description provided for @typePrezentatsiya.
  ///
  /// In ru, this message translates to:
  /// **'Презентация'**
  String get typePrezentatsiya;

  /// No description provided for @typeLektsiya.
  ///
  /// In ru, this message translates to:
  /// **'Лекция'**
  String get typeLektsiya;

  /// No description provided for @typeAmaliy.
  ///
  /// In ru, this message translates to:
  /// **'Практическое задание'**
  String get typeAmaliy;

  /// No description provided for @typeKonspektDesc.
  ///
  /// In ru, this message translates to:
  /// **'План урока с ходом занятия'**
  String get typeKonspektDesc;

  /// No description provided for @typeTestDesc.
  ///
  /// In ru, this message translates to:
  /// **'Вопросы для проверки знаний'**
  String get typeTestDesc;

  /// No description provided for @typePrezentatsiyaDesc.
  ///
  /// In ru, this message translates to:
  /// **'Слайды для урока'**
  String get typePrezentatsiyaDesc;

  /// No description provided for @typeLektsiyaDesc.
  ///
  /// In ru, this message translates to:
  /// **'Развёрнутое объяснение темы'**
  String get typeLektsiyaDesc;

  /// No description provided for @typeAmaliyDesc.
  ///
  /// In ru, this message translates to:
  /// **'Задание для самостоятельной работы'**
  String get typeAmaliyDesc;

  /// No description provided for @createMaterialTitle.
  ///
  /// In ru, this message translates to:
  /// **'Новый материал'**
  String get createMaterialTitle;

  /// No description provided for @stepTypeTitle.
  ///
  /// In ru, this message translates to:
  /// **'Что создаём?'**
  String get stepTypeTitle;

  /// No description provided for @stepDetailsTitle.
  ///
  /// In ru, this message translates to:
  /// **'О материале'**
  String get stepDetailsTitle;

  /// No description provided for @stepSourceTitle.
  ///
  /// In ru, this message translates to:
  /// **'Источник материала'**
  String get stepSourceTitle;

  /// No description provided for @stepOptionsTitle.
  ///
  /// In ru, this message translates to:
  /// **'Параметры'**
  String get stepOptionsTitle;

  /// No description provided for @stepReviewTitle.
  ///
  /// In ru, this message translates to:
  /// **'Готово к созданию'**
  String get stepReviewTitle;

  /// No description provided for @subjectLabel.
  ///
  /// In ru, this message translates to:
  /// **'Предмет'**
  String get subjectLabel;

  /// No description provided for @subjectHint.
  ///
  /// In ru, this message translates to:
  /// **'Например, Математика'**
  String get subjectHint;

  /// No description provided for @gradeLabel.
  ///
  /// In ru, this message translates to:
  /// **'Класс'**
  String get gradeLabel;

  /// No description provided for @gradeHint.
  ///
  /// In ru, this message translates to:
  /// **'Например, 7'**
  String get gradeHint;

  /// No description provided for @topicLabel.
  ///
  /// In ru, this message translates to:
  /// **'Тема урока'**
  String get topicLabel;

  /// No description provided for @topicHint.
  ///
  /// In ru, this message translates to:
  /// **'Например, Теорема Пифагора'**
  String get topicHint;

  /// No description provided for @levelLabel.
  ///
  /// In ru, this message translates to:
  /// **'Уровень сложности'**
  String get levelLabel;

  /// No description provided for @levelEasy.
  ///
  /// In ru, this message translates to:
  /// **'Лёгкий'**
  String get levelEasy;

  /// No description provided for @levelMedium.
  ///
  /// In ru, this message translates to:
  /// **'Средний'**
  String get levelMedium;

  /// No description provided for @levelHard.
  ///
  /// In ru, this message translates to:
  /// **'Сложный'**
  String get levelHard;

  /// No description provided for @materialLanguageLabel.
  ///
  /// In ru, this message translates to:
  /// **'Язык материала'**
  String get materialLanguageLabel;

  /// No description provided for @sourceQuestionTitle.
  ///
  /// In ru, this message translates to:
  /// **'Как подготовить материал?'**
  String get sourceQuestionTitle;

  /// No description provided for @sourceQuestionSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Выберите, на основе чего Dastyor создаст материал'**
  String get sourceQuestionSubtitle;

  /// No description provided for @sourceOptionBookTitle.
  ///
  /// In ru, this message translates to:
  /// **'По вашему учебнику'**
  String get sourceOptionBookTitle;

  /// No description provided for @sourceOptionBookDesc.
  ///
  /// In ru, this message translates to:
  /// **'Загрузите файл учебника или конспекта (PDF, DOCX, TXT) — материал будет основан именно на нём'**
  String get sourceOptionBookDesc;

  /// No description provided for @sourceOptionAiTitle.
  ///
  /// In ru, this message translates to:
  /// **'С помощью ИИ'**
  String get sourceOptionAiTitle;

  /// No description provided for @sourceOptionAiDesc.
  ///
  /// In ru, this message translates to:
  /// **'Искусственный интеллект подготовит материал самостоятельно, по теме и классу'**
  String get sourceOptionAiDesc;

  /// No description provided for @uploadSourceFile.
  ///
  /// In ru, this message translates to:
  /// **'Загрузить файл'**
  String get uploadSourceFile;

  /// No description provided for @uploadSourceHint.
  ///
  /// In ru, this message translates to:
  /// **'PDF, DOCX или TXT, до 15 МБ'**
  String get uploadSourceHint;

  /// No description provided for @uploadSourceChange.
  ///
  /// In ru, this message translates to:
  /// **'Заменить файл'**
  String get uploadSourceChange;

  /// No description provided for @uploadSourceRequired.
  ///
  /// In ru, this message translates to:
  /// **'Загрузите файл, чтобы продолжить'**
  String get uploadSourceRequired;

  /// No description provided for @uploadSourceTooLarge.
  ///
  /// In ru, this message translates to:
  /// **'Файл слишком большой (максимум 15 МБ)'**
  String get uploadSourceTooLarge;

  /// No description provided for @uploadSourceReading.
  ///
  /// In ru, this message translates to:
  /// **'Читаем файл…'**
  String get uploadSourceReading;

  /// No description provided for @questionCountLabel.
  ///
  /// In ru, this message translates to:
  /// **'Количество вопросов'**
  String get questionCountLabel;

  /// No description provided for @slideCountLabel.
  ///
  /// In ru, this message translates to:
  /// **'Количество слайдов'**
  String get slideCountLabel;

  /// No description provided for @testTypeLabel.
  ///
  /// In ru, this message translates to:
  /// **'Тип вопросов'**
  String get testTypeLabel;

  /// No description provided for @testTypeMixed.
  ///
  /// In ru, this message translates to:
  /// **'Смешанный'**
  String get testTypeMixed;

  /// No description provided for @testTypeMultipleChoice.
  ///
  /// In ru, this message translates to:
  /// **'Один правильный ответ'**
  String get testTypeMultipleChoice;

  /// No description provided for @testTypeTrueFalse.
  ///
  /// In ru, this message translates to:
  /// **'Верно / неверно'**
  String get testTypeTrueFalse;

  /// No description provided for @testTypeMultipleSelect.
  ///
  /// In ru, this message translates to:
  /// **'Несколько правильных'**
  String get testTypeMultipleSelect;

  /// No description provided for @testTypeOpenEnded.
  ///
  /// In ru, this message translates to:
  /// **'Открытый вопрос'**
  String get testTypeOpenEnded;

  /// No description provided for @templateLabel.
  ///
  /// In ru, this message translates to:
  /// **'Оформление'**
  String get templateLabel;

  /// No description provided for @includeHomework.
  ///
  /// In ru, this message translates to:
  /// **'Домашнее задание'**
  String get includeHomework;

  /// No description provided for @includeFunFacts.
  ///
  /// In ru, this message translates to:
  /// **'Интересные факты'**
  String get includeFunFacts;

  /// No description provided for @includeAssessment.
  ///
  /// In ru, this message translates to:
  /// **'Критерии оценивания'**
  String get includeAssessment;

  /// No description provided for @generateButton.
  ///
  /// In ru, this message translates to:
  /// **'Создать материал'**
  String get generateButton;

  /// No description provided for @generatingTitle.
  ///
  /// In ru, this message translates to:
  /// **'Dastyor готовит материал'**
  String get generatingTitle;

  /// No description provided for @generatingSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Обычно это занимает несколько секунд…'**
  String get generatingSubtitle;

  /// No description provided for @generationFailed.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось создать материал. Попробуйте ещё раз'**
  String get generationFailed;

  /// No description provided for @freeLimitReachedTitle.
  ///
  /// In ru, this message translates to:
  /// **'Бесплатный лимит исчерпан'**
  String get freeLimitReachedTitle;

  /// No description provided for @freeLimitReachedDesc.
  ///
  /// In ru, this message translates to:
  /// **'Бесплатно доступно по 1 материалу каждого типа. Для новых материалов нужна платная подписка'**
  String get freeLimitReachedDesc;

  /// No description provided for @materialSaved.
  ///
  /// In ru, this message translates to:
  /// **'Материал сохранён'**
  String get materialSaved;

  /// No description provided for @errorInsufficientBalance.
  ///
  /// In ru, this message translates to:
  /// **'Бесплатный (по 1 каждого типа) использован, а баланса не хватает'**
  String get errorInsufficientBalance;

  /// No description provided for @insufficientBalanceDesc.
  ///
  /// In ru, this message translates to:
  /// **'1 конспект, тест, презентация или лекция = 50 дирам. Свяжитесь с нами ниже, оплатите — и мы пополним ваш баланс.'**
  String get insufficientBalanceDesc;

  /// No description provided for @balanceLabel.
  ///
  /// In ru, this message translates to:
  /// **'Баланс'**
  String get balanceLabel;

  /// No description provided for @profileBalanceCta.
  ///
  /// In ru, this message translates to:
  /// **'Подключить Telegram и пополнить баланс'**
  String get profileBalanceCta;

  /// No description provided for @topUpBalance.
  ///
  /// In ru, this message translates to:
  /// **'Пополнить баланс'**
  String get topUpBalance;

  /// No description provided for @contactTelegram.
  ///
  /// In ru, this message translates to:
  /// **'Написать в Telegram'**
  String get contactTelegram;

  /// No description provided for @contactWhatsapp.
  ///
  /// In ru, this message translates to:
  /// **'Написать в WhatsApp'**
  String get contactWhatsapp;

  /// No description provided for @contactPhone.
  ///
  /// In ru, this message translates to:
  /// **'Телефон'**
  String get contactPhone;

  /// No description provided for @myMaterialsTitle.
  ///
  /// In ru, this message translates to:
  /// **'Мои материалы'**
  String get myMaterialsTitle;

  /// No description provided for @searchHint.
  ///
  /// In ru, this message translates to:
  /// **'Поиск по теме или предмету'**
  String get searchHint;

  /// No description provided for @favoriteAdd.
  ///
  /// In ru, this message translates to:
  /// **'В избранное'**
  String get favoriteAdd;

  /// No description provided for @favoriteRemove.
  ///
  /// In ru, this message translates to:
  /// **'Убрать из избранного'**
  String get favoriteRemove;

  /// No description provided for @favoritesOnly.
  ///
  /// In ru, this message translates to:
  /// **'Только избранные'**
  String get favoritesOnly;

  /// No description provided for @deleteConfirmTitle.
  ///
  /// In ru, this message translates to:
  /// **'Удалить материал?'**
  String get deleteConfirmTitle;

  /// No description provided for @deleteConfirmMessage.
  ///
  /// In ru, this message translates to:
  /// **'Это действие нельзя отменить'**
  String get deleteConfirmMessage;

  /// No description provided for @ok.
  ///
  /// In ru, this message translates to:
  /// **'ОК'**
  String get ok;

  /// No description provided for @cancel.
  ///
  /// In ru, this message translates to:
  /// **'Отмена'**
  String get cancel;

  /// No description provided for @save.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить'**
  String get save;

  /// No description provided for @delete.
  ///
  /// In ru, this message translates to:
  /// **'Удалить'**
  String get delete;

  /// No description provided for @edit.
  ///
  /// In ru, this message translates to:
  /// **'Редактировать'**
  String get edit;

  /// No description provided for @konspektEditTitle.
  ///
  /// In ru, this message translates to:
  /// **'Редактировать конспект'**
  String get konspektEditTitle;

  /// No description provided for @addItem.
  ///
  /// In ru, this message translates to:
  /// **'Добавить'**
  String get addItem;

  /// No description provided for @changesSaved.
  ///
  /// In ru, this message translates to:
  /// **'Изменения сохранены'**
  String get changesSaved;

  /// No description provided for @unsavedChangesTitle.
  ///
  /// In ru, this message translates to:
  /// **'Отменить изменения?'**
  String get unsavedChangesTitle;

  /// No description provided for @unsavedChangesMessage.
  ///
  /// In ru, this message translates to:
  /// **'Ваши изменения ещё не сохранены.'**
  String get unsavedChangesMessage;

  /// No description provided for @discard.
  ///
  /// In ru, this message translates to:
  /// **'Отменить'**
  String get discard;

  /// No description provided for @close.
  ///
  /// In ru, this message translates to:
  /// **'Закрыть'**
  String get close;

  /// No description provided for @retry.
  ///
  /// In ru, this message translates to:
  /// **'Повторить'**
  String get retry;

  /// No description provided for @loading.
  ///
  /// In ru, this message translates to:
  /// **'Загрузка…'**
  String get loading;

  /// No description provided for @yes.
  ///
  /// In ru, this message translates to:
  /// **'Да'**
  String get yes;

  /// No description provided for @no.
  ///
  /// In ru, this message translates to:
  /// **'Нет'**
  String get no;

  /// No description provided for @download.
  ///
  /// In ru, this message translates to:
  /// **'Скачать'**
  String get download;

  /// No description provided for @downloadDocx.
  ///
  /// In ru, this message translates to:
  /// **'Скачать DOCX'**
  String get downloadDocx;

  /// No description provided for @downloadPdf.
  ///
  /// In ru, this message translates to:
  /// **'Скачать PDF'**
  String get downloadPdf;

  /// No description provided for @viewAsPdf.
  ///
  /// In ru, this message translates to:
  /// **'Просмотреть как PDF'**
  String get viewAsPdf;

  /// No description provided for @pdfWebOpenedHint.
  ///
  /// In ru, this message translates to:
  /// **'PDF открыт в новой вкладке — там же можно распечатать'**
  String get pdfWebOpenedHint;

  /// No description provided for @pdfWebOpenButton.
  ///
  /// In ru, this message translates to:
  /// **'Открыть PDF'**
  String get pdfWebOpenButton;

  /// No description provided for @downloadPptx.
  ///
  /// In ru, this message translates to:
  /// **'Скачать PPTX'**
  String get downloadPptx;

  /// No description provided for @downloadTxt.
  ///
  /// In ru, this message translates to:
  /// **'Скачать TXT'**
  String get downloadTxt;

  /// No description provided for @downloadZip.
  ///
  /// In ru, this message translates to:
  /// **'Скачать всё (ZIP)'**
  String get downloadZip;

  /// No description provided for @noContentYet.
  ///
  /// In ru, this message translates to:
  /// **'Содержимое ещё не готово'**
  String get noContentYet;

  /// No description provided for @createdOn.
  ///
  /// In ru, this message translates to:
  /// **'Создано {date}'**
  String createdOn(String date);

  /// No description provided for @profileTitle.
  ///
  /// In ru, this message translates to:
  /// **'Профиль'**
  String get profileTitle;

  /// No description provided for @editProfile.
  ///
  /// In ru, this message translates to:
  /// **'Редактировать профиль'**
  String get editProfile;

  /// No description provided for @changePassword.
  ///
  /// In ru, this message translates to:
  /// **'Изменить пароль'**
  String get changePassword;

  /// No description provided for @appLanguage.
  ///
  /// In ru, this message translates to:
  /// **'Язык приложения'**
  String get appLanguage;

  /// No description provided for @logoutConfirmTitle.
  ///
  /// In ru, this message translates to:
  /// **'Выйти из аккаунта?'**
  String get logoutConfirmTitle;

  /// No description provided for @deleteAccount.
  ///
  /// In ru, this message translates to:
  /// **'Удалить аккаунт'**
  String get deleteAccount;

  /// No description provided for @deleteAccountConfirmTitle.
  ///
  /// In ru, this message translates to:
  /// **'Удалить аккаунт навсегда?'**
  String get deleteAccountConfirmTitle;

  /// No description provided for @deleteAccountConfirmMessage.
  ///
  /// In ru, this message translates to:
  /// **'Все ваши материалы будут безвозвратно удалены'**
  String get deleteAccountConfirmMessage;

  /// No description provided for @premiumBadge.
  ///
  /// In ru, this message translates to:
  /// **'Премиум'**
  String get premiumBadge;

  /// No description provided for @freeBadge.
  ///
  /// In ru, this message translates to:
  /// **'Бесплатный'**
  String get freeBadge;

  /// No description provided for @memberSince.
  ///
  /// In ru, this message translates to:
  /// **'С нами с {date}'**
  String memberSince(String date);

  /// No description provided for @changeAvatar.
  ///
  /// In ru, this message translates to:
  /// **'Изменить фото'**
  String get changeAvatar;

  /// No description provided for @removeAvatar.
  ///
  /// In ru, this message translates to:
  /// **'Удалить фото'**
  String get removeAvatar;

  /// No description provided for @chooseFromGallery.
  ///
  /// In ru, this message translates to:
  /// **'Выбрать из галереи'**
  String get chooseFromGallery;

  /// No description provided for @takePhoto.
  ///
  /// In ru, this message translates to:
  /// **'Сделать фото'**
  String get takePhoto;

  /// No description provided for @dashboardStatsLabel.
  ///
  /// In ru, this message translates to:
  /// **'СТАТИСТИКА'**
  String get dashboardStatsLabel;

  /// No description provided for @statConspekts.
  ///
  /// In ru, this message translates to:
  /// **'Конспекты'**
  String get statConspekts;

  /// No description provided for @statTests.
  ///
  /// In ru, this message translates to:
  /// **'Тесты'**
  String get statTests;

  /// No description provided for @statPresentations.
  ///
  /// In ru, this message translates to:
  /// **'Презентации'**
  String get statPresentations;

  /// No description provided for @statLectures.
  ///
  /// In ru, this message translates to:
  /// **'Лекции'**
  String get statLectures;

  /// No description provided for @statPractical.
  ///
  /// In ru, this message translates to:
  /// **'Практические задания'**
  String get statPractical;

  /// No description provided for @comingSoonTitle.
  ///
  /// In ru, this message translates to:
  /// **'Скоро будет'**
  String get comingSoonTitle;

  /// No description provided for @comingSoonDesc.
  ///
  /// In ru, this message translates to:
  /// **'Этот шаг создания материала ещё в разработке — загляните позже'**
  String get comingSoonDesc;

  /// No description provided for @adminPanel.
  ///
  /// In ru, this message translates to:
  /// **'Админ-панель'**
  String get adminPanel;

  /// No description provided for @adminUsersTitle.
  ///
  /// In ru, this message translates to:
  /// **'Пользователи'**
  String get adminUsersTitle;

  /// No description provided for @adminSearchHint.
  ///
  /// In ru, this message translates to:
  /// **'Поиск по имени, телефону, email или ID'**
  String get adminSearchHint;

  /// No description provided for @adminNoUsers.
  ///
  /// In ru, this message translates to:
  /// **'Пользователи не найдены'**
  String get adminNoUsers;

  /// No description provided for @adminYouBadge.
  ///
  /// In ru, this message translates to:
  /// **'Вы'**
  String get adminYouBadge;

  /// No description provided for @adminTopUpAction.
  ///
  /// In ru, this message translates to:
  /// **'Пополнить баланс'**
  String get adminTopUpAction;

  /// No description provided for @adminAmountSomoni.
  ///
  /// In ru, this message translates to:
  /// **'Сумма, сомони'**
  String get adminAmountSomoni;

  /// No description provided for @adminGivePremium.
  ///
  /// In ru, this message translates to:
  /// **'Выдать premium'**
  String get adminGivePremium;

  /// No description provided for @adminRemovePremium.
  ///
  /// In ru, this message translates to:
  /// **'Убрать premium'**
  String get adminRemovePremium;

  /// No description provided for @adminMakeAdmin.
  ///
  /// In ru, this message translates to:
  /// **'Сделать админом'**
  String get adminMakeAdmin;

  /// No description provided for @adminRemoveAdmin.
  ///
  /// In ru, this message translates to:
  /// **'Убрать права админа'**
  String get adminRemoveAdmin;

  /// No description provided for @adminBalanceUpdated.
  ///
  /// In ru, this message translates to:
  /// **'Баланс пополнен'**
  String get adminBalanceUpdated;

  /// No description provided for @stepMoreOptionsTitle.
  ///
  /// In ru, this message translates to:
  /// **'Другие варианты'**
  String get stepMoreOptionsTitle;

  /// No description provided for @typeGenerateAll.
  ///
  /// In ru, this message translates to:
  /// **'Всё сразу'**
  String get typeGenerateAll;

  /// No description provided for @typeGenerateAllDesc.
  ///
  /// In ru, this message translates to:
  /// **'Конспект, тест, презентация и лекция по одной теме — генерируются вместе'**
  String get typeGenerateAllDesc;

  /// No description provided for @generateAllLoadingDesc.
  ///
  /// In ru, this message translates to:
  /// **'Это займёт чуть больше времени — 4 материала генерируются по очереди'**
  String get generateAllLoadingDesc;

  /// No description provided for @generateAllResultTitle.
  ///
  /// In ru, this message translates to:
  /// **'{count, plural, one{Готов {count} материал} few{Готово {count} материала} many{Готово {count} материалов} other{Готово {count} материалов}}'**
  String generateAllResultTitle(int count);

  /// No description provided for @generateAllSkippedNote.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось сгенерировать: {types}'**
  String generateAllSkippedNote(String types);

  /// No description provided for @typeCurriculum.
  ///
  /// In ru, this message translates to:
  /// **'Комплект (несколько тем)'**
  String get typeCurriculum;

  /// No description provided for @typeCurriculumDesc.
  ///
  /// In ru, this message translates to:
  /// **'Список тем и диапазон дат — по конспекту на каждую тему, генерируются вместе как курс'**
  String get typeCurriculumDesc;

  /// No description provided for @curriculumMyListTitle.
  ///
  /// In ru, this message translates to:
  /// **'Мои комплекты'**
  String get curriculumMyListTitle;

  /// No description provided for @curriculumImportDocx.
  ///
  /// In ru, this message translates to:
  /// **'Загрузить из .docx'**
  String get curriculumImportDocx;

  /// No description provided for @curriculumTopicsLabel.
  ///
  /// In ru, this message translates to:
  /// **'Темы'**
  String get curriculumTopicsLabel;

  /// No description provided for @curriculumTopicsHint.
  ///
  /// In ru, this message translates to:
  /// **'По одной теме на строку, например:\nПеременные и типы данных\nУсловные операторы\nЦиклы'**
  String get curriculumTopicsHint;

  /// No description provided for @curriculumDateRangeLabel.
  ///
  /// In ru, this message translates to:
  /// **'Период'**
  String get curriculumDateRangeLabel;

  /// No description provided for @curriculumRestDaysLabel.
  ///
  /// In ru, this message translates to:
  /// **'Выходные дни'**
  String get curriculumRestDaysLabel;

  /// No description provided for @curriculumCreateButton.
  ///
  /// In ru, this message translates to:
  /// **'Создать комплект'**
  String get curriculumCreateButton;

  /// No description provided for @curriculumProgress.
  ///
  /// In ru, this message translates to:
  /// **'Генерация: {done} из {total}'**
  String curriculumProgress(int done, int total);

  /// No description provided for @curriculumProgressDone.
  ///
  /// In ru, this message translates to:
  /// **'Готово: {done} из {total}'**
  String curriculumProgressDone(int done, int total);

  /// No description provided for @curriculumExamBadge.
  ///
  /// In ru, this message translates to:
  /// **'ТЕСТ'**
  String get curriculumExamBadge;

  /// No description provided for @curriculumStatusDraft.
  ///
  /// In ru, this message translates to:
  /// **'Черновик'**
  String get curriculumStatusDraft;

  /// No description provided for @curriculumStatusGenerating.
  ///
  /// In ru, this message translates to:
  /// **'Генерируется'**
  String get curriculumStatusGenerating;

  /// No description provided for @curriculumStatusReady.
  ///
  /// In ru, this message translates to:
  /// **'Готово'**
  String get curriculumStatusReady;

  /// No description provided for @curriculumStatusPartialFailed.
  ///
  /// In ru, this message translates to:
  /// **'Есть ошибки'**
  String get curriculumStatusPartialFailed;

  /// No description provided for @curriculumNoBundles.
  ///
  /// In ru, this message translates to:
  /// **'Вы ещё не создали ни одного комплекта'**
  String get curriculumNoBundles;

  /// No description provided for @curriculumStartGeneration.
  ///
  /// In ru, this message translates to:
  /// **'Начать генерацию'**
  String get curriculumStartGeneration;

  /// No description provided for @curriculumDraftHint.
  ///
  /// In ru, this message translates to:
  /// **'Проверьте темы перед генерацией — нажмите на тему, чтобы изменить её.'**
  String get curriculumDraftHint;

  /// No description provided for @curriculumEditTopicTitle.
  ///
  /// In ru, this message translates to:
  /// **'Изменить тему'**
  String get curriculumEditTopicTitle;

  /// No description provided for @curriculumDuplicate.
  ///
  /// In ru, this message translates to:
  /// **'Дублировать'**
  String get curriculumDuplicate;

  /// No description provided for @curriculumNotifReadyTitle.
  ///
  /// In ru, this message translates to:
  /// **'✅ «{title}» готово!'**
  String curriculumNotifReadyTitle(String title);

  /// No description provided for @curriculumNotifReadyBody.
  ///
  /// In ru, this message translates to:
  /// **'Все {total} занятий успешно созданы. Нажмите, чтобы посмотреть.'**
  String curriculumNotifReadyBody(int total);

  /// No description provided for @curriculumNotifPartialTitle.
  ///
  /// In ru, this message translates to:
  /// **'⚠ «{title}» готово частично'**
  String curriculumNotifPartialTitle(String title);

  /// No description provided for @curriculumNotifPartialBody.
  ///
  /// In ru, this message translates to:
  /// **'{done} из {total} занятий готовы — некоторые завершились с ошибкой, повторите в приложении.'**
  String curriculumNotifPartialBody(int done, int total);

  /// No description provided for @adminTotalUsers.
  ///
  /// In ru, this message translates to:
  /// **'Пользователи'**
  String get adminTotalUsers;

  /// No description provided for @adminTotalMaterials.
  ///
  /// In ru, this message translates to:
  /// **'Материалы'**
  String get adminTotalMaterials;

  /// No description provided for @adminTotalCurriculums.
  ///
  /// In ru, this message translates to:
  /// **'Комплекты'**
  String get adminTotalCurriculums;

  /// No description provided for @navAdminDashboard.
  ///
  /// In ru, this message translates to:
  /// **'Статистика'**
  String get navAdminDashboard;

  /// No description provided for @navAdminUsers.
  ///
  /// In ru, this message translates to:
  /// **'Пользователи'**
  String get navAdminUsers;

  /// No description provided for @topUpTitle.
  ///
  /// In ru, this message translates to:
  /// **'Пополнение баланса'**
  String get topUpTitle;

  /// No description provided for @topUpAmountLabel.
  ///
  /// In ru, this message translates to:
  /// **'Сумма пополнения, с.'**
  String get topUpAmountLabel;

  /// No description provided for @topUpAmountHelp.
  ///
  /// In ru, this message translates to:
  /// **'1 конспект, тест, презентация или лекция = 50 дирам'**
  String get topUpAmountHelp;

  /// No description provided for @topUpPayButton.
  ///
  /// In ru, this message translates to:
  /// **'Перейти к оплате'**
  String get topUpPayButton;

  /// No description provided for @topUpProvider.
  ///
  /// In ru, this message translates to:
  /// **'Оплата через Dushanbe City'**
  String get topUpProvider;

  /// No description provided for @topUpInvalidAmount.
  ///
  /// In ru, this message translates to:
  /// **'Укажите сумму от 1 до 1000 сомони'**
  String get topUpInvalidAmount;

  /// No description provided for @topUpOpenFailed.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось открыть страницу оплаты'**
  String get topUpOpenFailed;

  /// No description provided for @topUpWaiting.
  ///
  /// In ru, this message translates to:
  /// **'Ждём подтверждение оплаты от банка…'**
  String get topUpWaiting;

  /// No description provided for @topUpCheckStatus.
  ///
  /// In ru, this message translates to:
  /// **'Проверить статус'**
  String get topUpCheckStatus;

  /// No description provided for @topUpContinuePayment.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить оплату'**
  String get topUpContinuePayment;

  /// No description provided for @topUpSuccess.
  ///
  /// In ru, this message translates to:
  /// **'Баланс пополнен на {amount} с.'**
  String topUpSuccess(String amount);

  /// No description provided for @topUpStillPending.
  ///
  /// In ru, this message translates to:
  /// **'Платёж ещё обрабатывается. Как только банк подтвердит оплату, баланс пополнится автоматически.'**
  String get topUpStillPending;

  /// No description provided for @topUpFailed.
  ///
  /// In ru, this message translates to:
  /// **'Платёж не прошёл'**
  String get topUpFailed;

  /// No description provided for @topUpCanceled.
  ///
  /// In ru, this message translates to:
  /// **'Платёж отменён'**
  String get topUpCanceled;

  /// No description provided for @topUpHistory.
  ///
  /// In ru, this message translates to:
  /// **'История пополнений'**
  String get topUpHistory;

  /// No description provided for @topUpHistoryEmpty.
  ///
  /// In ru, this message translates to:
  /// **'Пополнений пока нет'**
  String get topUpHistoryEmpty;

  /// No description provided for @topUpStatusPending.
  ///
  /// In ru, this message translates to:
  /// **'В обработке'**
  String get topUpStatusPending;

  /// No description provided for @topUpStatusCompleted.
  ///
  /// In ru, this message translates to:
  /// **'Зачислено'**
  String get topUpStatusCompleted;

  /// No description provided for @topUpStatusFailed.
  ///
  /// In ru, this message translates to:
  /// **'Не прошёл'**
  String get topUpStatusFailed;

  /// No description provided for @topUpStatusCanceled.
  ///
  /// In ru, this message translates to:
  /// **'Отменён'**
  String get topUpStatusCanceled;

  /// No description provided for @lectureTemplateLabel.
  ///
  /// In ru, this message translates to:
  /// **'Шаблон лекции'**
  String get lectureTemplateLabel;

  /// No description provided for @tmplPlanspektName.
  ///
  /// In ru, this message translates to:
  /// **'План-конспект'**
  String get tmplPlanspektName;

  /// No description provided for @tmplPlanspektDesc.
  ///
  /// In ru, this message translates to:
  /// **'Лаконичный рабочий формат без обложки'**
  String get tmplPlanspektDesc;

  /// No description provided for @tmplAkademikName.
  ///
  /// In ru, this message translates to:
  /// **'Академический'**
  String get tmplAkademikName;

  /// No description provided for @tmplAkademikDesc.
  ///
  /// In ru, this message translates to:
  /// **'Титульный лист, засечный шрифт, тонкие линии'**
  String get tmplAkademikDesc;

  /// No description provided for @tmplZamonaviyName.
  ///
  /// In ru, this message translates to:
  /// **'Современный'**
  String get tmplZamonaviyName;

  /// No description provided for @tmplZamonaviyDesc.
  ///
  /// In ru, this message translates to:
  /// **'Цветная панель, крупные номера, карточки'**
  String get tmplZamonaviyDesc;

  /// No description provided for @tmplJurnalName.
  ///
  /// In ru, this message translates to:
  /// **'Журнальный'**
  String get tmplJurnalName;

  /// No description provided for @tmplJurnalDesc.
  ///
  /// In ru, this message translates to:
  /// **'Баннер на обложке, разделы на плашке'**
  String get tmplJurnalDesc;

  /// No description provided for @tmplPraktikumName.
  ///
  /// In ru, this message translates to:
  /// **'Практикум'**
  String get tmplPraktikumName;

  /// No description provided for @tmplPraktikumDesc.
  ///
  /// In ru, this message translates to:
  /// **'Рамка, поля для имени, место для записей'**
  String get tmplPraktikumDesc;

  /// No description provided for @profileContact.
  ///
  /// In ru, this message translates to:
  /// **'Связь'**
  String get profileContact;

  /// No description provided for @contactEmail.
  ///
  /// In ru, this message translates to:
  /// **'Email'**
  String get contactEmail;

  /// No description provided for @registerTerms.
  ///
  /// In ru, this message translates to:
  /// **'Условия использования'**
  String get registerTerms;

  /// No description provided for @registerPrivacy.
  ///
  /// In ru, this message translates to:
  /// **'Политика конфиденциальности'**
  String get registerPrivacy;

  /// No description provided for @gamesTitle.
  ///
  /// In ru, this message translates to:
  /// **'Игры'**
  String get gamesTitle;

  /// No description provided for @gamesDesc.
  ///
  /// In ru, this message translates to:
  /// **'Обучающие игры с вопросами от AI'**
  String get gamesDesc;

  /// No description provided for @gameTemplatesTitle.
  ///
  /// In ru, this message translates to:
  /// **'Шаблоны игр'**
  String get gameTemplatesTitle;

  /// No description provided for @gameTemplatesPrompt.
  ///
  /// In ru, this message translates to:
  /// **'Сначала выберите шаблон игры, затем настроим её параметры.'**
  String get gameTemplatesPrompt;

  /// No description provided for @gameMagicBoxName.
  ///
  /// In ru, this message translates to:
  /// **'Волшебные коробки'**
  String get gameMagicBoxName;

  /// No description provided for @gameMagicBoxDesc.
  ///
  /// In ru, this message translates to:
  /// **'Спрячьте вопрос в коробки, перемешайте их и выберите правильную.'**
  String get gameMagicBoxDesc;

  /// No description provided for @gameSecLabName.
  ///
  /// In ru, this message translates to:
  /// **'Секретная лаборатория'**
  String get gameSecLabName;

  /// No description provided for @gameSecLabDesc.
  ///
  /// In ru, this message translates to:
  /// **'Войдите в секретную лабораторию, отвечайте на вопросы и проведите великий опыт!'**
  String get gameSecLabDesc;

  /// No description provided for @gameMoreSoonTitle.
  ///
  /// In ru, this message translates to:
  /// **'Новые шаблоны'**
  String get gameMoreSoonTitle;

  /// No description provided for @gameMoreSoonDesc.
  ///
  /// In ru, this message translates to:
  /// **'Скоро добавим новые игры'**
  String get gameMoreSoonDesc;

  /// No description provided for @gameSelect.
  ///
  /// In ru, this message translates to:
  /// **'Выбрать'**
  String get gameSelect;

  /// No description provided for @gameRoundsLabel.
  ///
  /// In ru, this message translates to:
  /// **'Количество раундов'**
  String get gameRoundsLabel;

  /// No description provided for @gameTopicHint.
  ///
  /// In ru, this message translates to:
  /// **'Например: Вещества'**
  String get gameTopicHint;

  /// No description provided for @gameNoQuestions.
  ///
  /// In ru, this message translates to:
  /// **'AI не составил ни одного вопроса. Попробуйте ещё раз.'**
  String get gameNoQuestions;

  /// No description provided for @gamePreparingQuestions.
  ///
  /// In ru, this message translates to:
  /// **'Готовим вопросы...'**
  String get gamePreparingQuestions;

  /// No description provided for @gamePreparingGame.
  ///
  /// In ru, this message translates to:
  /// **'Игра готовится'**
  String get gamePreparingGame;

  /// No description provided for @gameMagicBoxSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'AI составит для вас вопросы'**
  String get gameMagicBoxSubtitle;

  /// No description provided for @gameStart.
  ///
  /// In ru, this message translates to:
  /// **'Начать игру'**
  String get gameStart;

  /// No description provided for @gameSecLabSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Настройки опыта'**
  String get gameSecLabSubtitle;

  /// No description provided for @gameSecLabStart.
  ///
  /// In ru, this message translates to:
  /// **'Начать опыт'**
  String get gameSecLabStart;

  /// No description provided for @gameMemorize.
  ///
  /// In ru, this message translates to:
  /// **'Внимательно запомните вопросы!'**
  String get gameMemorize;

  /// No description provided for @gamePlacingQuestions.
  ///
  /// In ru, this message translates to:
  /// **'Вопросы кладутся в коробки...'**
  String get gamePlacingQuestions;

  /// No description provided for @gameAttention.
  ///
  /// In ru, this message translates to:
  /// **'Внимание!'**
  String get gameAttention;

  /// No description provided for @gameGo.
  ///
  /// In ru, this message translates to:
  /// **'Начали!'**
  String get gameGo;

  /// No description provided for @gameShuffling.
  ///
  /// In ru, this message translates to:
  /// **'Коробки перемешиваются...'**
  String get gameShuffling;

  /// No description provided for @gamePickBox.
  ///
  /// In ru, this message translates to:
  /// **'Теперь выберите коробку!'**
  String get gamePickBox;

  /// No description provided for @gameNewExperiment.
  ///
  /// In ru, this message translates to:
  /// **'Новый опыт! 🧪'**
  String get gameNewExperiment;

  /// No description provided for @gameQuestion.
  ///
  /// In ru, this message translates to:
  /// **'ВОПРОС'**
  String get gameQuestion;

  /// No description provided for @gamePickReagent.
  ///
  /// In ru, this message translates to:
  /// **'ВЫБЕРИТЕ РЕАГЕНТ!'**
  String get gamePickReagent;

  /// No description provided for @gameCorrectCheer.
  ///
  /// In ru, this message translates to:
  /// **'Молодец! Верный ответ! ✅'**
  String get gameCorrectCheer;

  /// No description provided for @gameRound.
  ///
  /// In ru, this message translates to:
  /// **'РАУНД'**
  String get gameRound;

  /// No description provided for @gameWrongAnswer.
  ///
  /// In ru, this message translates to:
  /// **'Неверный ответ!'**
  String get gameWrongAnswer;

  /// No description provided for @gameYourAnswer.
  ///
  /// In ru, this message translates to:
  /// **'ВАШ ОТВЕТ'**
  String get gameYourAnswer;

  /// No description provided for @gameCorrectAnswer.
  ///
  /// In ru, this message translates to:
  /// **'ВЕРНЫЙ ОТВЕТ'**
  String get gameCorrectAnswer;

  /// No description provided for @gameWhyCorrect.
  ///
  /// In ru, this message translates to:
  /// **'ПОЧЕМУ ЭТОТ ОТВЕТ ВЕРНЫЙ? 💡'**
  String get gameWhyCorrect;

  /// No description provided for @gameContinue.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить'**
  String get gameContinue;

  /// No description provided for @gameScore.
  ///
  /// In ru, this message translates to:
  /// **'Очки'**
  String get gameScore;

  /// No description provided for @gameCorrectCount.
  ///
  /// In ru, this message translates to:
  /// **'Верные ответы'**
  String get gameCorrectCount;

  /// No description provided for @gameWrongCount.
  ///
  /// In ru, this message translates to:
  /// **'Неверные ответы'**
  String get gameWrongCount;

  /// No description provided for @gameAccuracy.
  ///
  /// In ru, this message translates to:
  /// **'Точность'**
  String get gameAccuracy;

  /// No description provided for @gameOver.
  ///
  /// In ru, this message translates to:
  /// **'Игра окончена'**
  String get gameOver;

  /// No description provided for @gameCongrats.
  ///
  /// In ru, this message translates to:
  /// **'Поздравляем! 🎉'**
  String get gameCongrats;

  /// No description provided for @gameFinishedSuccess.
  ///
  /// In ru, this message translates to:
  /// **'Вы успешно прошли игру!'**
  String get gameFinishedSuccess;

  /// No description provided for @gamePlayAgain.
  ///
  /// In ru, this message translates to:
  /// **'Играть снова'**
  String get gamePlayAgain;

  /// No description provided for @gameBackToTemplates.
  ///
  /// In ru, this message translates to:
  /// **'Вернуться к шаблонам'**
  String get gameBackToTemplates;

  /// No description provided for @gameQuestionLetter.
  ///
  /// In ru, this message translates to:
  /// **'ВОПРОС {letter}'**
  String gameQuestionLetter(String letter);

  /// No description provided for @gameBoxNumber.
  ///
  /// In ru, this message translates to:
  /// **'Коробка {number}'**
  String gameBoxNumber(int number);

  /// No description provided for @gameQuestionsPerRound.
  ///
  /// In ru, this message translates to:
  /// **'По {perRound} вопросов на раунд, всего {total} вопросов.'**
  String gameQuestionsPerRound(int perRound, int total);

  /// No description provided for @langRu.
  ///
  /// In ru, this message translates to:
  /// **'Русский'**
  String get langRu;

  /// No description provided for @langTg.
  ///
  /// In ru, this message translates to:
  /// **'Таджикский'**
  String get langTg;

  /// No description provided for @langEn.
  ///
  /// In ru, this message translates to:
  /// **'Английский'**
  String get langEn;

  /// No description provided for @weekdayMon.
  ///
  /// In ru, this message translates to:
  /// **'Пн'**
  String get weekdayMon;

  /// No description provided for @weekdayTue.
  ///
  /// In ru, this message translates to:
  /// **'Вт'**
  String get weekdayTue;

  /// No description provided for @weekdayWed.
  ///
  /// In ru, this message translates to:
  /// **'Ср'**
  String get weekdayWed;

  /// No description provided for @weekdayThu.
  ///
  /// In ru, this message translates to:
  /// **'Чт'**
  String get weekdayThu;

  /// No description provided for @weekdayFri.
  ///
  /// In ru, this message translates to:
  /// **'Пт'**
  String get weekdayFri;

  /// No description provided for @weekdaySat.
  ///
  /// In ru, this message translates to:
  /// **'Сб'**
  String get weekdaySat;

  /// No description provided for @weekdaySun.
  ///
  /// In ru, this message translates to:
  /// **'Вс'**
  String get weekdaySun;

  /// No description provided for @subjTajikLang.
  ///
  /// In ru, this message translates to:
  /// **'Таджикский язык'**
  String get subjTajikLang;

  /// No description provided for @subjTajikLit.
  ///
  /// In ru, this message translates to:
  /// **'Таджикская литература'**
  String get subjTajikLit;

  /// No description provided for @subjRussianLang.
  ///
  /// In ru, this message translates to:
  /// **'Русский язык'**
  String get subjRussianLang;

  /// No description provided for @subjEnglishLang.
  ///
  /// In ru, this message translates to:
  /// **'Английский язык'**
  String get subjEnglishLang;

  /// No description provided for @subjMath.
  ///
  /// In ru, this message translates to:
  /// **'Математика'**
  String get subjMath;

  /// No description provided for @subjAlgebra.
  ///
  /// In ru, this message translates to:
  /// **'Алгебра'**
  String get subjAlgebra;

  /// No description provided for @subjGeometry.
  ///
  /// In ru, this message translates to:
  /// **'Геометрия'**
  String get subjGeometry;

  /// No description provided for @subjInformatics.
  ///
  /// In ru, this message translates to:
  /// **'Информатика'**
  String get subjInformatics;

  /// No description provided for @subjPhysics.
  ///
  /// In ru, this message translates to:
  /// **'Физика'**
  String get subjPhysics;

  /// No description provided for @subjChemistry.
  ///
  /// In ru, this message translates to:
  /// **'Химия'**
  String get subjChemistry;

  /// No description provided for @subjBiology.
  ///
  /// In ru, this message translates to:
  /// **'Биология'**
  String get subjBiology;

  /// No description provided for @subjGeography.
  ///
  /// In ru, this message translates to:
  /// **'География'**
  String get subjGeography;

  /// No description provided for @subjHistoryTj.
  ///
  /// In ru, this message translates to:
  /// **'История Таджикистана'**
  String get subjHistoryTj;

  /// No description provided for @subjHistoryWorld.
  ///
  /// In ru, this message translates to:
  /// **'Всемирная история'**
  String get subjHistoryWorld;

  /// No description provided for @subjNatureStudy.
  ///
  /// In ru, this message translates to:
  /// **'Природоведение'**
  String get subjNatureStudy;

  /// No description provided for @subjFineArt.
  ///
  /// In ru, this message translates to:
  /// **'Изобразительное искусство'**
  String get subjFineArt;

  /// No description provided for @subjMusic.
  ///
  /// In ru, this message translates to:
  /// **'Музыка'**
  String get subjMusic;

  /// No description provided for @subjTechnology.
  ///
  /// In ru, this message translates to:
  /// **'Технология'**
  String get subjTechnology;

  /// No description provided for @subjPhysEd.
  ///
  /// In ru, this message translates to:
  /// **'Физическая культура'**
  String get subjPhysEd;

  /// No description provided for @subjLawBasics.
  ///
  /// In ru, this message translates to:
  /// **'Основы государства и права'**
  String get subjLawBasics;

  /// No description provided for @balanceTitle.
  ///
  /// In ru, this message translates to:
  /// **'Баланс'**
  String get balanceTitle;

  /// No description provided for @balanceCurrent.
  ///
  /// In ru, this message translates to:
  /// **'Текущий баланс'**
  String get balanceCurrent;

  /// No description provided for @currencySomoni.
  ///
  /// In ru, this message translates to:
  /// **'сомони'**
  String get currencySomoni;

  /// No description provided for @balanceTopUpTitle.
  ///
  /// In ru, this message translates to:
  /// **'Как пополнить'**
  String get balanceTopUpTitle;

  /// No description provided for @balanceTopUpBody.
  ///
  /// In ru, this message translates to:
  /// **'Напишите команде Dastyor — вам пришлют инструкции по оплате.'**
  String get balanceTopUpBody;

  /// No description provided for @balanceTopUpBodyEmailOnly.
  ///
  /// In ru, this message translates to:
  /// **'Напишите команде Dastyor на почту — вам пришлют инструкции по оплате.'**
  String get balanceTopUpBodyEmailOnly;

  /// No description provided for @balanceNoPaymentNote.
  ///
  /// In ru, this message translates to:
  /// **'Оплата внутри приложения не принимается. Баланс изменится после того, как команда Dastyor подтвердит платёж.'**
  String get balanceNoPaymentNote;

  /// No description provided for @contactChannelsUnconfigured.
  ///
  /// In ru, this message translates to:
  /// **'Telegram и WhatsApp пока не подключены.'**
  String get contactChannelsUnconfigured;

  /// No description provided for @contactOpenFailed.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось открыть ссылку'**
  String get contactOpenFailed;

  /// No description provided for @helpTitle.
  ///
  /// In ru, this message translates to:
  /// **'Помощь и связь'**
  String get helpTitle;

  /// No description provided for @helpIntro.
  ///
  /// In ru, this message translates to:
  /// **'Напишите нам, если что-то не работает или нужны инструкции по оплате.'**
  String get helpIntro;

  /// No description provided for @navBalance.
  ///
  /// In ru, this message translates to:
  /// **'Баланс'**
  String get navBalance;

  /// No description provided for @balanceTelegramTitle.
  ///
  /// In ru, this message translates to:
  /// **'🔗 Подключение Telegram'**
  String get balanceTelegramTitle;

  /// No description provided for @balanceTelegramSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Нажмите кнопку: бот безопасно свяжет Telegram с вашим аккаунтом Dastyor по одноразовой ссылке. Затем выберите сумму и отправьте чек; администратор проверит поступление денег.'**
  String get balanceTelegramSubtitle;

  /// No description provided for @balanceTelegramButton.
  ///
  /// In ru, this message translates to:
  /// **'🔗 Подключить аккаунт Dastyor'**
  String get balanceTelegramButton;

  /// No description provided for @balanceTelegramButtonLinked.
  ///
  /// In ru, this message translates to:
  /// **'🤖 Открыть бот в Telegram'**
  String get balanceTelegramButtonLinked;

  /// No description provided for @balanceTelegramLinkedNote.
  ///
  /// In ru, this message translates to:
  /// **'✅ Ваш аккаунт уже привязан к боту.'**
  String get balanceTelegramLinkedNote;

  /// No description provided for @balanceTelegramFailed.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось создать ссылку привязки. Попробуйте снова.'**
  String get balanceTelegramFailed;

  /// No description provided for @balanceTelegramUnavailable.
  ///
  /// In ru, this message translates to:
  /// **'Оплата через Telegram пока не настроена.'**
  String get balanceTelegramUnavailable;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ru', 'tg'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ru':
      return AppLocalizationsRu();
    case 'tg':
      return AppLocalizationsTg();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
