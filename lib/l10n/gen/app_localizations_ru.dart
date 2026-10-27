// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appName => 'Dastyor';

  @override
  String get appTagline =>
      'Конспект, тест, презентация и лекция — за секунды, с помощью ИИ';

  @override
  String get authSideBullet2 => 'Готово за секунды благодаря ИИ';

  @override
  String get authSideBullet3 =>
      'Создавайте на телефоне — печатайте с компьютера';

  @override
  String get chooseLanguageTitle => 'Выберите язык';

  @override
  String get chooseLanguageSubtitle =>
      'Вы всегда сможете изменить его в настройках';

  @override
  String get continueBtn => 'Продолжить';

  @override
  String get skip => 'Пропустить';

  @override
  String get getStarted => 'Начать';

  @override
  String get next => 'Далее';

  @override
  String get back => 'Назад';

  @override
  String get onboardTitle1 => 'Материалы за секунды';

  @override
  String get onboardDesc1 =>
      'Конспект, тест, презентация и лекция готовятся за считанные секунды — не часы';

  @override
  String get onboardTitle2 => 'На основе учебника или ИИ';

  @override
  String get onboardDesc2 =>
      'Каждый материал можно создать по вашему учебнику или с помощью искусственного интеллекта';

  @override
  String get onboardTitle3 => 'На 3 языках';

  @override
  String get onboardDesc3 =>
      'Приложение и материалы доступны на русском, английском и таджикском';

  @override
  String get qrLoginTitle => 'Вход через приложение';

  @override
  String get qrLoginStep1 => 'Откройте приложение Dastyor на телефоне';

  @override
  String get qrLoginStep2 => 'Перейдите в Профиль → «Вход на компьютере»';

  @override
  String get qrLoginStep3 => 'Наведите камеру на этот QR-код';

  @override
  String get qrLoginError => 'Не удалось создать QR-код';

  @override
  String get qrLoginRetry => 'Обновить код';

  @override
  String get qrScanTitle => 'Сканировать QR-код';

  @override
  String get qrScanHint => 'Наведите камеру на QR-код на экране компьютера';

  @override
  String get qrScanConfirmTitle => 'Войти на компьютере?';

  @override
  String get qrScanConfirmDesc =>
      'Вы подтверждаете вход в свой аккаунт Dastyor на другом устройстве.';

  @override
  String get qrScanConfirmButton => 'Подтвердить';

  @override
  String get qrScanSuccess => 'Вы вошли на компьютере';

  @override
  String get qrScanInvalid => 'Это не QR-код для входа Dastyor';

  @override
  String get profileLoginOnComputer => 'Вход на компьютере';

  @override
  String get profileLinkedDevices => 'Связанные устройства';

  @override
  String get linkedDevicesTitle => 'Связанные устройства';

  @override
  String get linkedDevicesEmptyTitle => 'Нет связанных устройств';

  @override
  String get linkedDevicesEmptySubtitle =>
      'Здесь появятся браузеры, где вы вошли через QR-код или по номеру телефона';

  @override
  String linkedDevicesLoggedInAt(String date) {
    return 'Вход выполнен $date';
  }

  @override
  String get linkedDevicesLogoutTitle => 'Выйти на этом устройстве?';

  @override
  String get welcomeBack => 'С возвращением';

  @override
  String get welcomeBackSubtitle => 'Войдите, чтобы продолжить работу';

  @override
  String get createAccount => 'Создать аккаунт';

  @override
  String get createAccountSubtitle => 'Зарегистрируйтесь по номеру телефона';

  @override
  String get fullName => 'Полное имя';

  @override
  String get fullNameHint => 'Например, Азиз Раҳимов';

  @override
  String get phoneNumber => 'Номер телефона';

  @override
  String get password => 'Пароль';

  @override
  String get confirmPassword => 'Подтвердите пароль';

  @override
  String get currentPassword => 'Текущий пароль';

  @override
  String get newPassword => 'Новый пароль';

  @override
  String get confirmNewPassword => 'Подтвердите новый пароль';

  @override
  String get login => 'Войти';

  @override
  String get register => 'Зарегистрироваться';

  @override
  String get loginWithQrInstead => 'Войти через QR-код';

  @override
  String get qrLoginUsePhoneInstead => 'Войти по номеру телефона';

  @override
  String get logout => 'Выйти';

  @override
  String get dontHaveAccount => 'Нет аккаунта?';

  @override
  String get alreadyHaveAccount => 'Уже есть аккаунт?';

  @override
  String get forgotPassword => 'Забыли пароль?';

  @override
  String get sendCode => 'Отправить код';

  @override
  String get otpTitle => 'Введите код';

  @override
  String get otpSubtitle => 'Мы отправили 6-значный код на';

  @override
  String get otpResendQuestion => 'Не пришёл код?';

  @override
  String get otpResend => 'Отправить повторно';

  @override
  String otpResendIn(int seconds) {
    return 'Повторно через $seconds с';
  }

  @override
  String get otpVerify => 'Подтвердить';

  @override
  String get otpInvalid => 'Неверный код';

  @override
  String get resetPasswordTitle => 'Новый пароль';

  @override
  String get resetPasswordSubtitle => 'Придумайте новый пароль для входа';

  @override
  String get resetPasswordButton => 'Сохранить пароль';

  @override
  String get passwordChangedSuccess => 'Пароль успешно изменён';

  @override
  String get errorRequired => 'Обязательное поле';

  @override
  String get errorPhoneInvalid => 'Введите номер в формате +992 XX XXX XXXX';

  @override
  String get errorPasswordShort => 'Минимум 6 символов';

  @override
  String get errorPasswordMismatch => 'Пароли не совпадают';

  @override
  String get errorNameShort => 'Введите имя и фамилию';

  @override
  String get errorNetwork => 'Нет соединения с сервером. Проверьте интернет';

  @override
  String get errorGeneric => 'Что-то пошло не так. Попробуйте снова';

  @override
  String get errorPhoneTaken => 'Этот номер уже зарегистрирован';

  @override
  String get errorInvalidCredentials => 'Неверный номер телефона или пароль';

  @override
  String get errorTooManyAttempts => 'Слишком много попыток. Подождите немного';

  @override
  String get errorSessionExpired => 'Сессия истекла. Войдите снова';

  @override
  String dashboardGreetingMorning(String name) {
    return 'Доброе утро, $name!';
  }

  @override
  String dashboardGreetingDay(String name) {
    return 'Добрый день, $name!';
  }

  @override
  String dashboardGreetingEvening(String name) {
    return 'Добрый вечер, $name!';
  }

  @override
  String get dashboardSubtitle => 'Что подготовим сегодня?';

  @override
  String get quickCreate => 'Создать материал';

  @override
  String get recentMaterials => 'Недавние материалы';

  @override
  String get viewAll => 'Все';

  @override
  String get emptyMaterialsTitle => 'Пока нет материалов';

  @override
  String get emptyMaterialsSubtitle =>
      'Создайте первый конспект, тест, презентацию или лекцию';

  @override
  String get navHome => 'Главная';

  @override
  String get navMaterials => 'Материалы';

  @override
  String get navCreate => 'Создать';

  @override
  String get navProfile => 'Профиль';

  @override
  String get typeKonspekt => 'Конспект';

  @override
  String get typeTest => 'Тест';

  @override
  String get typePrezentatsiya => 'Презентация';

  @override
  String get typeLektsiya => 'Лекция';

  @override
  String get typeAmaliy => 'Практическое задание';

  @override
  String get typeKonspektDesc => 'План урока с ходом занятия';

  @override
  String get typeTestDesc => 'Вопросы для проверки знаний';

  @override
  String get typePrezentatsiyaDesc => 'Слайды для урока';

  @override
  String get typeLektsiyaDesc => 'Развёрнутое объяснение темы';

  @override
  String get typeAmaliyDesc => 'Задание для самостоятельной работы';

  @override
  String get createMaterialTitle => 'Новый материал';

  @override
  String get stepTypeTitle => 'Что создаём?';

  @override
  String get stepDetailsTitle => 'О материале';

  @override
  String get stepSourceTitle => 'Источник материала';

  @override
  String get stepOptionsTitle => 'Параметры';

  @override
  String get stepReviewTitle => 'Готово к созданию';

  @override
  String get subjectLabel => 'Предмет';

  @override
  String get subjectHint => 'Например, Математика';

  @override
  String get gradeLabel => 'Класс';

  @override
  String get gradeHint => 'Например, 7';

  @override
  String get topicLabel => 'Тема урока';

  @override
  String get topicHint => 'Например, Теорема Пифагора';

  @override
  String get levelLabel => 'Уровень сложности';

  @override
  String get levelEasy => 'Лёгкий';

  @override
  String get levelMedium => 'Средний';

  @override
  String get levelHard => 'Сложный';

  @override
  String get materialLanguageLabel => 'Язык материала';

  @override
  String get sourceQuestionTitle => 'Как подготовить материал?';

  @override
  String get sourceQuestionSubtitle =>
      'Выберите, на основе чего Dastyor создаст материал';

  @override
  String get sourceOptionBookTitle => 'По вашему учебнику';

  @override
  String get sourceOptionBookDesc =>
      'Загрузите файл учебника или конспекта (PDF, DOCX, TXT) — материал будет основан именно на нём';

  @override
  String get sourceOptionAiTitle => 'С помощью ИИ';

  @override
  String get sourceOptionAiDesc =>
      'Искусственный интеллект подготовит материал самостоятельно, по теме и классу';

  @override
  String get uploadSourceFile => 'Загрузить файл';

  @override
  String get uploadSourceHint => 'PDF, DOCX или TXT, до 15 МБ';

  @override
  String get uploadSourceChange => 'Заменить файл';

  @override
  String get uploadSourceRequired => 'Загрузите файл, чтобы продолжить';

  @override
  String get uploadSourceTooLarge => 'Файл слишком большой (максимум 15 МБ)';

  @override
  String get uploadSourceReading => 'Читаем файл…';

  @override
  String get questionCountLabel => 'Количество вопросов';

  @override
  String get slideCountLabel => 'Количество слайдов';

  @override
  String get testTypeLabel => 'Тип вопросов';

  @override
  String get testTypeMixed => 'Смешанный';

  @override
  String get testTypeMultipleChoice => 'Один правильный ответ';

  @override
  String get testTypeTrueFalse => 'Верно / неверно';

  @override
  String get testTypeMultipleSelect => 'Несколько правильных';

  @override
  String get testTypeOpenEnded => 'Открытый вопрос';

  @override
  String get templateLabel => 'Оформление';

  @override
  String get includeHomework => 'Домашнее задание';

  @override
  String get includeFunFacts => 'Интересные факты';

  @override
  String get includeAssessment => 'Критерии оценивания';

  @override
  String get generateButton => 'Создать материал';

  @override
  String get generatingTitle => 'Dastyor готовит материал';

  @override
  String get generatingSubtitle => 'Обычно это занимает несколько секунд…';

  @override
  String get generationFailed =>
      'Не удалось создать материал. Попробуйте ещё раз';

  @override
  String get freeLimitReachedTitle => 'Бесплатный лимит исчерпан';

  @override
  String get freeLimitReachedDesc =>
      'Бесплатно доступно по 1 материалу каждого типа. Для новых материалов нужна платная подписка';

  @override
  String get materialSaved => 'Материал сохранён';

  @override
  String get errorInsufficientBalance =>
      'Бесплатный (по 1 каждого типа) использован, а баланса не хватает';

  @override
  String get insufficientBalanceDesc =>
      '1 конспект, тест, презентация или лекция = 50 дирам. Свяжитесь с нами ниже, оплатите — и мы пополним ваш баланс.';

  @override
  String get balanceLabel => 'Баланс';

  @override
  String get profileBalanceCta => 'Подключить Telegram и пополнить баланс';

  @override
  String get topUpBalance => 'Пополнить баланс';

  @override
  String get contactTelegram => 'Написать в Telegram';

  @override
  String get contactWhatsapp => 'Написать в WhatsApp';

  @override
  String get contactPhone => 'Телефон';

  @override
  String get myMaterialsTitle => 'Мои материалы';

  @override
  String get searchHint => 'Поиск по теме или предмету';

  @override
  String get favoriteAdd => 'В избранное';

  @override
  String get favoriteRemove => 'Убрать из избранного';

  @override
  String get favoritesOnly => 'Только избранные';

  @override
  String get deleteConfirmTitle => 'Удалить материал?';

  @override
  String get deleteConfirmMessage => 'Это действие нельзя отменить';

  @override
  String get ok => 'ОК';

  @override
  String get cancel => 'Отмена';

  @override
  String get save => 'Сохранить';

  @override
  String get delete => 'Удалить';

  @override
  String get edit => 'Редактировать';

  @override
  String get konspektEditTitle => 'Редактировать конспект';

  @override
  String get addItem => 'Добавить';

  @override
  String get changesSaved => 'Изменения сохранены';

  @override
  String get unsavedChangesTitle => 'Отменить изменения?';

  @override
  String get unsavedChangesMessage => 'Ваши изменения ещё не сохранены.';

  @override
  String get discard => 'Отменить';

  @override
  String get close => 'Закрыть';

  @override
  String get retry => 'Повторить';

  @override
  String get loading => 'Загрузка…';

  @override
  String get yes => 'Да';

  @override
  String get no => 'Нет';

  @override
  String get download => 'Скачать';

  @override
  String get downloadDocx => 'Скачать DOCX';

  @override
  String get downloadPdf => 'Скачать PDF';

  @override
  String get viewAsPdf => 'Просмотреть как PDF';

  @override
  String get pdfWebOpenedHint =>
      'PDF открыт в новой вкладке — там же можно распечатать';

  @override
  String get pdfWebOpenButton => 'Открыть PDF';

  @override
  String get downloadPptx => 'Скачать PPTX';

  @override
  String get downloadTxt => 'Скачать TXT';

  @override
  String get downloadZip => 'Скачать всё (ZIP)';

  @override
  String get noContentYet => 'Содержимое ещё не готово';

  @override
  String createdOn(String date) {
    return 'Создано $date';
  }

  @override
  String get profileTitle => 'Профиль';

  @override
  String get editProfile => 'Редактировать профиль';

  @override
  String get changePassword => 'Изменить пароль';

  @override
  String get appLanguage => 'Язык приложения';

  @override
  String get logoutConfirmTitle => 'Выйти из аккаунта?';

  @override
  String get deleteAccount => 'Удалить аккаунт';

  @override
  String get deleteAccountConfirmTitle => 'Удалить аккаунт навсегда?';

  @override
  String get deleteAccountConfirmMessage =>
      'Все ваши материалы будут безвозвратно удалены';

  @override
  String get premiumBadge => 'Премиум';

  @override
  String get freeBadge => 'Бесплатный';

  @override
  String memberSince(String date) {
    return 'С нами с $date';
  }

  @override
  String get changeAvatar => 'Изменить фото';

  @override
  String get removeAvatar => 'Удалить фото';

  @override
  String get chooseFromGallery => 'Выбрать из галереи';

  @override
  String get takePhoto => 'Сделать фото';

  @override
  String get dashboardStatsLabel => 'СТАТИСТИКА';

  @override
  String get statConspekts => 'Конспекты';

  @override
  String get statTests => 'Тесты';

  @override
  String get statPresentations => 'Презентации';

  @override
  String get statLectures => 'Лекции';

  @override
  String get statPractical => 'Практические задания';

  @override
  String get comingSoonTitle => 'Скоро будет';

  @override
  String get comingSoonDesc =>
      'Этот шаг создания материала ещё в разработке — загляните позже';

  @override
  String get adminPanel => 'Админ-панель';

  @override
  String get adminUsersTitle => 'Пользователи';

  @override
  String get adminSearchHint => 'Поиск по имени, телефону, email или ID';

  @override
  String get adminNoUsers => 'Пользователи не найдены';

  @override
  String get adminYouBadge => 'Вы';

  @override
  String get adminTopUpAction => 'Пополнить баланс';

  @override
  String get adminAmountSomoni => 'Сумма, сомони';

  @override
  String get adminGivePremium => 'Выдать premium';

  @override
  String get adminRemovePremium => 'Убрать premium';

  @override
  String get adminMakeAdmin => 'Сделать админом';

  @override
  String get adminRemoveAdmin => 'Убрать права админа';

  @override
  String get adminBalanceUpdated => 'Баланс пополнен';

  @override
  String get stepMoreOptionsTitle => 'Другие варианты';

  @override
  String get typeGenerateAll => 'Всё сразу';

  @override
  String get typeGenerateAllDesc =>
      'Конспект, тест, презентация и лекция по одной теме — генерируются вместе';

  @override
  String get generateAllLoadingDesc =>
      'Это займёт чуть больше времени — 4 материала генерируются по очереди';

  @override
  String generateAllResultTitle(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Готово $count материалов',
      many: 'Готово $count материалов',
      few: 'Готово $count материала',
      one: 'Готов $count материал',
    );
    return '$_temp0';
  }

  @override
  String generateAllSkippedNote(String types) {
    return 'Не удалось сгенерировать: $types';
  }

  @override
  String get typeCurriculum => 'Комплект (несколько тем)';

  @override
  String get typeCurriculumDesc =>
      'Список тем и диапазон дат — по конспекту на каждую тему, генерируются вместе как курс';

  @override
  String get curriculumMyListTitle => 'Мои комплекты';

  @override
  String get curriculumImportDocx => 'Загрузить из .docx';

  @override
  String get curriculumTopicsLabel => 'Темы';

  @override
  String get curriculumTopicsHint =>
      'По одной теме на строку, например:\nПеременные и типы данных\nУсловные операторы\nЦиклы';

  @override
  String get curriculumDateRangeLabel => 'Период';

  @override
  String get curriculumRestDaysLabel => 'Выходные дни';

  @override
  String get curriculumCreateButton => 'Создать комплект';

  @override
  String curriculumProgress(int done, int total) {
    return 'Генерация: $done из $total';
  }

  @override
  String curriculumProgressDone(int done, int total) {
    return 'Готово: $done из $total';
  }

  @override
  String get curriculumExamBadge => 'ТЕСТ';

  @override
  String get curriculumStatusDraft => 'Черновик';

  @override
  String get curriculumStatusGenerating => 'Генерируется';

  @override
  String get curriculumStatusReady => 'Готово';

  @override
  String get curriculumStatusPartialFailed => 'Есть ошибки';

  @override
  String get curriculumNoBundles => 'Вы ещё не создали ни одного комплекта';

  @override
  String get curriculumStartGeneration => 'Начать генерацию';

  @override
  String get curriculumDraftHint =>
      'Проверьте темы перед генерацией — нажмите на тему, чтобы изменить её.';

  @override
  String get curriculumEditTopicTitle => 'Изменить тему';

  @override
  String get curriculumDuplicate => 'Дублировать';

  @override
  String curriculumNotifReadyTitle(String title) {
    return '✅ «$title» готово!';
  }

  @override
  String curriculumNotifReadyBody(int total) {
    return 'Все $total занятий успешно созданы. Нажмите, чтобы посмотреть.';
  }

  @override
  String curriculumNotifPartialTitle(String title) {
    return '⚠ «$title» готово частично';
  }

  @override
  String curriculumNotifPartialBody(int done, int total) {
    return '$done из $total занятий готовы — некоторые завершились с ошибкой, повторите в приложении.';
  }

  @override
  String get adminTotalUsers => 'Пользователи';

  @override
  String get adminTotalMaterials => 'Материалы';

  @override
  String get adminTotalCurriculums => 'Комплекты';

  @override
  String get navAdminDashboard => 'Статистика';

  @override
  String get navAdminUsers => 'Пользователи';

  @override
  String get topUpTitle => 'Пополнение баланса';

  @override
  String get topUpAmountLabel => 'Сумма пополнения, с.';

  @override
  String get topUpAmountHelp =>
      '1 конспект, тест, презентация или лекция = 50 дирам';

  @override
  String get topUpPayButton => 'Перейти к оплате';

  @override
  String get topUpProvider => 'Оплата через Dushanbe City';

  @override
  String get topUpInvalidAmount => 'Укажите сумму от 1 до 1000 сомони';

  @override
  String get topUpOpenFailed => 'Не удалось открыть страницу оплаты';

  @override
  String get topUpWaiting => 'Ждём подтверждение оплаты от банка…';

  @override
  String get topUpCheckStatus => 'Проверить статус';

  @override
  String get topUpContinuePayment => 'Продолжить оплату';

  @override
  String topUpSuccess(String amount) {
    return 'Баланс пополнен на $amount с.';
  }

  @override
  String get topUpStillPending =>
      'Платёж ещё обрабатывается. Как только банк подтвердит оплату, баланс пополнится автоматически.';

  @override
  String get topUpFailed => 'Платёж не прошёл';

  @override
  String get topUpCanceled => 'Платёж отменён';

  @override
  String get topUpHistory => 'История пополнений';

  @override
  String get topUpHistoryEmpty => 'Пополнений пока нет';

  @override
  String get topUpStatusPending => 'В обработке';

  @override
  String get topUpStatusCompleted => 'Зачислено';

  @override
  String get topUpStatusFailed => 'Не прошёл';

  @override
  String get topUpStatusCanceled => 'Отменён';

  @override
  String get lectureTemplateLabel => 'Шаблон лекции';

  @override
  String get tmplPlanspektName => 'План-конспект';

  @override
  String get tmplPlanspektDesc => 'Лаконичный рабочий формат без обложки';

  @override
  String get tmplAkademikName => 'Академический';

  @override
  String get tmplAkademikDesc => 'Титульный лист, засечный шрифт, тонкие линии';

  @override
  String get tmplZamonaviyName => 'Современный';

  @override
  String get tmplZamonaviyDesc => 'Цветная панель, крупные номера, карточки';

  @override
  String get tmplJurnalName => 'Журнальный';

  @override
  String get tmplJurnalDesc => 'Баннер на обложке, разделы на плашке';

  @override
  String get tmplPraktikumName => 'Практикум';

  @override
  String get tmplPraktikumDesc => 'Рамка, поля для имени, место для записей';

  @override
  String get profileContact => 'Связь';

  @override
  String get contactEmail => 'Email';

  @override
  String get registerTerms => 'Условия использования';

  @override
  String get registerPrivacy => 'Политика конфиденциальности';

  @override
  String get gamesTitle => 'Игры';

  @override
  String get gamesDesc => 'Обучающие игры с вопросами от AI';

  @override
  String get gameTemplatesTitle => 'Шаблоны игр';

  @override
  String get gameTemplatesPrompt =>
      'Сначала выберите шаблон игры, затем настроим её параметры.';

  @override
  String get gameMagicBoxName => 'Волшебные коробки';

  @override
  String get gameMagicBoxDesc =>
      'Спрячьте вопрос в коробки, перемешайте их и выберите правильную.';

  @override
  String get gameSecLabName => 'Секретная лаборатория';

  @override
  String get gameSecLabDesc =>
      'Войдите в секретную лабораторию, отвечайте на вопросы и проведите великий опыт!';

  @override
  String get gameMoreSoonTitle => 'Новые шаблоны';

  @override
  String get gameMoreSoonDesc => 'Скоро добавим новые игры';

  @override
  String get gameSelect => 'Выбрать';

  @override
  String get gameRoundsLabel => 'Количество раундов';

  @override
  String get gameTopicHint => 'Например: Вещества';

  @override
  String get gameNoQuestions =>
      'AI не составил ни одного вопроса. Попробуйте ещё раз.';

  @override
  String get gamePreparingQuestions => 'Готовим вопросы...';

  @override
  String get gamePreparingGame => 'Игра готовится';

  @override
  String get gameMagicBoxSubtitle => 'AI составит для вас вопросы';

  @override
  String get gameStart => 'Начать игру';

  @override
  String get gameSecLabSubtitle => 'Настройки опыта';

  @override
  String get gameSecLabStart => 'Начать опыт';

  @override
  String get gameMemorize => 'Внимательно запомните вопросы!';

  @override
  String get gamePlacingQuestions => 'Вопросы кладутся в коробки...';

  @override
  String get gameAttention => 'Внимание!';

  @override
  String get gameGo => 'Начали!';

  @override
  String get gameShuffling => 'Коробки перемешиваются...';

  @override
  String get gamePickBox => 'Теперь выберите коробку!';

  @override
  String get gameNewExperiment => 'Новый опыт! 🧪';

  @override
  String get gameQuestion => 'ВОПРОС';

  @override
  String get gamePickReagent => 'ВЫБЕРИТЕ РЕАГЕНТ!';

  @override
  String get gameCorrectCheer => 'Молодец! Верный ответ! ✅';

  @override
  String get gameRound => 'РАУНД';

  @override
  String get gameWrongAnswer => 'Неверный ответ!';

  @override
  String get gameYourAnswer => 'ВАШ ОТВЕТ';

  @override
  String get gameCorrectAnswer => 'ВЕРНЫЙ ОТВЕТ';

  @override
  String get gameWhyCorrect => 'ПОЧЕМУ ЭТОТ ОТВЕТ ВЕРНЫЙ? 💡';

  @override
  String get gameContinue => 'Продолжить';

  @override
  String get gameScore => 'Очки';

  @override
  String get gameCorrectCount => 'Верные ответы';

  @override
  String get gameWrongCount => 'Неверные ответы';

  @override
  String get gameAccuracy => 'Точность';

  @override
  String get gameOver => 'Игра окончена';

  @override
  String get gameCongrats => 'Поздравляем! 🎉';

  @override
  String get gameFinishedSuccess => 'Вы успешно прошли игру!';

  @override
  String get gamePlayAgain => 'Играть снова';

  @override
  String get gameBackToTemplates => 'Вернуться к шаблонам';

  @override
  String gameQuestionLetter(String letter) {
    return 'ВОПРОС $letter';
  }

  @override
  String gameBoxNumber(int number) {
    return 'Коробка $number';
  }

  @override
  String gameQuestionsPerRound(int perRound, int total) {
    return 'По $perRound вопросов на раунд, всего $total вопросов.';
  }

  @override
  String get langRu => 'Русский';

  @override
  String get langTg => 'Таджикский';

  @override
  String get langEn => 'Английский';

  @override
  String get weekdayMon => 'Пн';

  @override
  String get weekdayTue => 'Вт';

  @override
  String get weekdayWed => 'Ср';

  @override
  String get weekdayThu => 'Чт';

  @override
  String get weekdayFri => 'Пт';

  @override
  String get weekdaySat => 'Сб';

  @override
  String get weekdaySun => 'Вс';

  @override
  String get subjTajikLang => 'Таджикский язык';

  @override
  String get subjTajikLit => 'Таджикская литература';

  @override
  String get subjRussianLang => 'Русский язык';

  @override
  String get subjEnglishLang => 'Английский язык';

  @override
  String get subjMath => 'Математика';

  @override
  String get subjAlgebra => 'Алгебра';

  @override
  String get subjGeometry => 'Геометрия';

  @override
  String get subjInformatics => 'Информатика';

  @override
  String get subjPhysics => 'Физика';

  @override
  String get subjChemistry => 'Химия';

  @override
  String get subjBiology => 'Биология';

  @override
  String get subjGeography => 'География';

  @override
  String get subjHistoryTj => 'История Таджикистана';

  @override
  String get subjHistoryWorld => 'Всемирная история';

  @override
  String get subjNatureStudy => 'Природоведение';

  @override
  String get subjFineArt => 'Изобразительное искусство';

  @override
  String get subjMusic => 'Музыка';

  @override
  String get subjTechnology => 'Технология';

  @override
  String get subjPhysEd => 'Физическая культура';

  @override
  String get subjLawBasics => 'Основы государства и права';

  @override
  String get balanceTitle => 'Баланс';

  @override
  String get balanceCurrent => 'Текущий баланс';

  @override
  String get currencySomoni => 'сомони';

  @override
  String get balanceTopUpTitle => 'Как пополнить';

  @override
  String get balanceTopUpBody =>
      'Напишите команде Dastyor — вам пришлют инструкции по оплате.';

  @override
  String get balanceTopUpBodyEmailOnly =>
      'Напишите команде Dastyor на почту — вам пришлют инструкции по оплате.';

  @override
  String get balanceNoPaymentNote =>
      'Оплата внутри приложения не принимается. Баланс изменится после того, как команда Dastyor подтвердит платёж.';

  @override
  String get contactChannelsUnconfigured =>
      'Telegram и WhatsApp пока не подключены.';

  @override
  String get contactOpenFailed => 'Не удалось открыть ссылку';

  @override
  String get helpTitle => 'Помощь и связь';

  @override
  String get helpIntro =>
      'Напишите нам, если что-то не работает или нужны инструкции по оплате.';

  @override
  String get navBalance => 'Баланс';

  @override
  String get balanceTelegramTitle => '🔗 Подключение Telegram';

  @override
  String get balanceTelegramSubtitle =>
      'Нажмите кнопку: бот безопасно свяжет Telegram с вашим аккаунтом Dastyor по одноразовой ссылке. Затем выберите сумму и отправьте чек; администратор проверит поступление денег.';

  @override
  String get balanceTelegramButton => '🔗 Подключить аккаунт Dastyor';

  @override
  String get balanceTelegramButtonLinked => '🤖 Открыть бот в Telegram';

  @override
  String get balanceTelegramLinkedNote => '✅ Ваш аккаунт уже привязан к боту.';

  @override
  String get balanceTelegramFailed =>
      'Не удалось создать ссылку привязки. Попробуйте снова.';

  @override
  String get balanceTelegramUnavailable =>
      'Оплата через Telegram пока не настроена.';
}
