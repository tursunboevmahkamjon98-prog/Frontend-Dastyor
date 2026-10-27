// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'Dastyor';

  @override
  String get appTagline =>
      'Lesson notes, tests, presentations and lectures — in seconds, with AI';

  @override
  String get authSideBullet2 => 'Ready in seconds thanks to AI';

  @override
  String get authSideBullet3 =>
      'Create on your phone — print from your computer';

  @override
  String get chooseLanguageTitle => 'Choose a language';

  @override
  String get chooseLanguageSubtitle => 'You can change it anytime in settings';

  @override
  String get continueBtn => 'Continue';

  @override
  String get skip => 'Skip';

  @override
  String get getStarted => 'Get started';

  @override
  String get next => 'Next';

  @override
  String get back => 'Back';

  @override
  String get onboardTitle1 => 'Materials in seconds';

  @override
  String get onboardDesc1 =>
      'Lesson notes, tests, presentations and lectures are ready in seconds — not hours';

  @override
  String get onboardTitle2 => 'From your textbook or AI';

  @override
  String get onboardDesc2 =>
      'Create every material from your own textbook or with artificial intelligence';

  @override
  String get onboardTitle3 => 'In 3 languages';

  @override
  String get onboardDesc3 =>
      'The app and materials are available in Russian, English and Tajik';

  @override
  String get qrLoginTitle => 'Sign in via the app';

  @override
  String get qrLoginStep1 => 'Open the Dastyor app on your phone';

  @override
  String get qrLoginStep2 => 'Go to Profile → \"Log in on computer\"';

  @override
  String get qrLoginStep3 => 'Point your camera at this QR code';

  @override
  String get qrLoginError => 'Couldn\'t create a QR code';

  @override
  String get qrLoginRetry => 'Refresh code';

  @override
  String get qrScanTitle => 'Scan QR code';

  @override
  String get qrScanHint =>
      'Point your camera at the QR code on your computer screen';

  @override
  String get qrScanConfirmTitle => 'Log in on computer?';

  @override
  String get qrScanConfirmDesc =>
      'You\'re confirming sign-in to your Dastyor account on another device.';

  @override
  String get qrScanConfirmButton => 'Confirm';

  @override
  String get qrScanSuccess => 'You\'re signed in on your computer';

  @override
  String get qrScanInvalid => 'This isn\'t a Dastyor sign-in QR code';

  @override
  String get profileLoginOnComputer => 'Log in on computer';

  @override
  String get profileLinkedDevices => 'Linked devices';

  @override
  String get linkedDevicesTitle => 'Linked devices';

  @override
  String get linkedDevicesEmptyTitle => 'No linked devices';

  @override
  String get linkedDevicesEmptySubtitle =>
      'Browsers you\'ve signed into via QR code or phone number will show up here';

  @override
  String linkedDevicesLoggedInAt(String date) {
    return 'Signed in $date';
  }

  @override
  String get linkedDevicesLogoutTitle => 'Log out on this device?';

  @override
  String get welcomeBack => 'Welcome back';

  @override
  String get welcomeBackSubtitle => 'Sign in to keep going';

  @override
  String get createAccount => 'Create account';

  @override
  String get createAccountSubtitle => 'Sign up with your phone number';

  @override
  String get fullName => 'Full name';

  @override
  String get fullNameHint => 'e.g. Aziz Rahimov';

  @override
  String get phoneNumber => 'Phone number';

  @override
  String get password => 'Password';

  @override
  String get confirmPassword => 'Confirm password';

  @override
  String get currentPassword => 'Current password';

  @override
  String get newPassword => 'New password';

  @override
  String get confirmNewPassword => 'Confirm new password';

  @override
  String get login => 'Log in';

  @override
  String get register => 'Sign up';

  @override
  String get loginWithQrInstead => 'Log in with QR code';

  @override
  String get qrLoginUsePhoneInstead => 'Log in with phone number';

  @override
  String get logout => 'Log out';

  @override
  String get dontHaveAccount => 'Don\'t have an account?';

  @override
  String get alreadyHaveAccount => 'Already have an account?';

  @override
  String get forgotPassword => 'Forgot password?';

  @override
  String get sendCode => 'Send code';

  @override
  String get otpTitle => 'Enter the code';

  @override
  String get otpSubtitle => 'We sent a 6-digit code to';

  @override
  String get otpResendQuestion => 'Didn\'t get the code?';

  @override
  String get otpResend => 'Resend code';

  @override
  String otpResendIn(int seconds) {
    return 'Resend in ${seconds}s';
  }

  @override
  String get otpVerify => 'Verify';

  @override
  String get otpInvalid => 'Invalid code';

  @override
  String get resetPasswordTitle => 'New password';

  @override
  String get resetPasswordSubtitle => 'Set a new password to sign in';

  @override
  String get resetPasswordButton => 'Save password';

  @override
  String get passwordChangedSuccess => 'Password changed successfully';

  @override
  String get errorRequired => 'This field is required';

  @override
  String get errorPhoneInvalid => 'Enter a number like +992 XX XXX XXXX';

  @override
  String get errorPasswordShort => 'At least 6 characters';

  @override
  String get errorPasswordMismatch => 'Passwords don\'t match';

  @override
  String get errorNameShort => 'Enter your full name';

  @override
  String get errorNetwork => 'Can\'t reach the server. Check your connection';

  @override
  String get errorGeneric => 'Something went wrong. Please try again';

  @override
  String get errorPhoneTaken => 'This phone number is already registered';

  @override
  String get errorInvalidCredentials => 'Invalid phone number or password';

  @override
  String get errorTooManyAttempts => 'Too many attempts. Please wait a bit';

  @override
  String get errorSessionExpired => 'Session expired. Please sign in again';

  @override
  String dashboardGreetingMorning(String name) {
    return 'Good morning, $name!';
  }

  @override
  String dashboardGreetingDay(String name) {
    return 'Good afternoon, $name!';
  }

  @override
  String dashboardGreetingEvening(String name) {
    return 'Good evening, $name!';
  }

  @override
  String get dashboardSubtitle => 'What shall we prepare today?';

  @override
  String get quickCreate => 'Create material';

  @override
  String get recentMaterials => 'Recent materials';

  @override
  String get viewAll => 'View all';

  @override
  String get emptyMaterialsTitle => 'No materials yet';

  @override
  String get emptyMaterialsSubtitle =>
      'Create your first lesson notes, test, presentation or lecture';

  @override
  String get navHome => 'Home';

  @override
  String get navMaterials => 'Materials';

  @override
  String get navCreate => 'Create';

  @override
  String get navProfile => 'Profile';

  @override
  String get typeKonspekt => 'Lesson notes';

  @override
  String get typeTest => 'Test';

  @override
  String get typePrezentatsiya => 'Presentation';

  @override
  String get typeLektsiya => 'Lecture';

  @override
  String get typeAmaliy => 'Practical tasks';

  @override
  String get typeKonspektDesc => 'A full lesson plan with class flow';

  @override
  String get typeTestDesc => 'Questions to check understanding';

  @override
  String get typePrezentatsiyaDesc => 'Slides for the lesson';

  @override
  String get typeLektsiyaDesc => 'An in-depth explanation of the topic';

  @override
  String get typeAmaliyDesc => 'A task for independent practice';

  @override
  String get createMaterialTitle => 'New material';

  @override
  String get stepTypeTitle => 'What are we creating?';

  @override
  String get stepDetailsTitle => 'About the material';

  @override
  String get stepSourceTitle => 'Material source';

  @override
  String get stepOptionsTitle => 'Options';

  @override
  String get stepReviewTitle => 'Ready to create';

  @override
  String get subjectLabel => 'Subject';

  @override
  String get subjectHint => 'e.g. Mathematics';

  @override
  String get gradeLabel => 'Grade';

  @override
  String get gradeHint => 'e.g. 7';

  @override
  String get topicLabel => 'Lesson topic';

  @override
  String get topicHint => 'e.g. Pythagorean theorem';

  @override
  String get levelLabel => 'Difficulty level';

  @override
  String get levelEasy => 'Easy';

  @override
  String get levelMedium => 'Medium';

  @override
  String get levelHard => 'Hard';

  @override
  String get materialLanguageLabel => 'Material language';

  @override
  String get sourceQuestionTitle => 'How should it be created?';

  @override
  String get sourceQuestionSubtitle =>
      'Choose what Dastyor should base the material on';

  @override
  String get sourceOptionBookTitle => 'From your textbook';

  @override
  String get sourceOptionBookDesc =>
      'Upload your textbook or notes (PDF, DOCX, TXT) — the material will be based on it';

  @override
  String get sourceOptionAiTitle => 'With AI';

  @override
  String get sourceOptionAiDesc =>
      'AI prepares the material on its own, based on the topic and grade';

  @override
  String get uploadSourceFile => 'Upload file';

  @override
  String get uploadSourceHint => 'PDF, DOCX or TXT, up to 15 MB';

  @override
  String get uploadSourceChange => 'Replace file';

  @override
  String get uploadSourceRequired => 'Upload a file to continue';

  @override
  String get uploadSourceTooLarge => 'File is too large (max 15 MB)';

  @override
  String get uploadSourceReading => 'Reading file…';

  @override
  String get questionCountLabel => 'Number of questions';

  @override
  String get slideCountLabel => 'Number of slides';

  @override
  String get testTypeLabel => 'Question type';

  @override
  String get testTypeMixed => 'Mixed';

  @override
  String get testTypeMultipleChoice => 'Single correct answer';

  @override
  String get testTypeTrueFalse => 'True / false';

  @override
  String get testTypeMultipleSelect => 'Multiple correct answers';

  @override
  String get testTypeOpenEnded => 'Open-ended';

  @override
  String get templateLabel => 'Design';

  @override
  String get includeHomework => 'Homework';

  @override
  String get includeFunFacts => 'Fun facts';

  @override
  String get includeAssessment => 'Assessment criteria';

  @override
  String get generateButton => 'Create material';

  @override
  String get generatingTitle => 'Dastyor is preparing your material';

  @override
  String get generatingSubtitle => 'This usually takes a few seconds…';

  @override
  String get generationFailed =>
      'Couldn\'t create the material. Please try again';

  @override
  String get freeLimitReachedTitle => 'Free limit reached';

  @override
  String get freeLimitReachedDesc =>
      '1 free material of each type is included. A paid subscription is needed for more';

  @override
  String get materialSaved => 'Material saved';

  @override
  String get errorInsufficientBalance =>
      'Your free one (per type) is used up and your balance is too low';

  @override
  String get insufficientBalanceDesc =>
      '1 konspekt, test, presentation, or lecture = 50 dirams. Contact us below, pay, and we\'ll add it to your balance.';

  @override
  String get balanceLabel => 'Balance';

  @override
  String get profileBalanceCta => 'Link Telegram and top up your balance';

  @override
  String get topUpBalance => 'Top up balance';

  @override
  String get contactTelegram => 'Message on Telegram';

  @override
  String get contactWhatsapp => 'Message on WhatsApp';

  @override
  String get contactPhone => 'Phone';

  @override
  String get myMaterialsTitle => 'My materials';

  @override
  String get searchHint => 'Search by topic or subject';

  @override
  String get favoriteAdd => 'Add to favorites';

  @override
  String get favoriteRemove => 'Remove from favorites';

  @override
  String get favoritesOnly => 'Favorites only';

  @override
  String get deleteConfirmTitle => 'Delete this material?';

  @override
  String get deleteConfirmMessage => 'This action can\'t be undone';

  @override
  String get ok => 'OK';

  @override
  String get cancel => 'Cancel';

  @override
  String get save => 'Save';

  @override
  String get delete => 'Delete';

  @override
  String get edit => 'Edit';

  @override
  String get konspektEditTitle => 'Edit konspekt';

  @override
  String get addItem => 'Add';

  @override
  String get changesSaved => 'Changes saved';

  @override
  String get unsavedChangesTitle => 'Discard changes?';

  @override
  String get unsavedChangesMessage => 'Your edits haven\'t been saved yet.';

  @override
  String get discard => 'Discard';

  @override
  String get close => 'Close';

  @override
  String get retry => 'Retry';

  @override
  String get loading => 'Loading…';

  @override
  String get yes => 'Yes';

  @override
  String get no => 'No';

  @override
  String get download => 'Download';

  @override
  String get downloadDocx => 'Download DOCX';

  @override
  String get downloadPdf => 'Download PDF';

  @override
  String get viewAsPdf => 'View as PDF';

  @override
  String get pdfWebOpenedHint =>
      'The PDF opened in a new tab — you can print it from there';

  @override
  String get pdfWebOpenButton => 'Open PDF';

  @override
  String get downloadPptx => 'Download PPTX';

  @override
  String get downloadTxt => 'Download TXT';

  @override
  String get downloadZip => 'Download all (ZIP)';

  @override
  String get noContentYet => 'No content yet';

  @override
  String createdOn(String date) {
    return 'Created $date';
  }

  @override
  String get profileTitle => 'Profile';

  @override
  String get editProfile => 'Edit profile';

  @override
  String get changePassword => 'Change password';

  @override
  String get appLanguage => 'App language';

  @override
  String get logoutConfirmTitle => 'Log out of your account?';

  @override
  String get deleteAccount => 'Delete account';

  @override
  String get deleteAccountConfirmTitle => 'Delete your account permanently?';

  @override
  String get deleteAccountConfirmMessage =>
      'All your materials will be permanently deleted';

  @override
  String get premiumBadge => 'Premium';

  @override
  String get freeBadge => 'Free';

  @override
  String memberSince(String date) {
    return 'Member since $date';
  }

  @override
  String get changeAvatar => 'Change photo';

  @override
  String get removeAvatar => 'Remove photo';

  @override
  String get chooseFromGallery => 'Choose from gallery';

  @override
  String get takePhoto => 'Take a photo';

  @override
  String get dashboardStatsLabel => 'STATISTICS';

  @override
  String get statConspekts => 'Lesson notes';

  @override
  String get statTests => 'Tests';

  @override
  String get statPresentations => 'Presentations';

  @override
  String get statLectures => 'Lectures';

  @override
  String get statPractical => 'Practical tasks';

  @override
  String get comingSoonTitle => 'Coming soon';

  @override
  String get comingSoonDesc =>
      'This part of material creation is still being built — check back soon';

  @override
  String get adminPanel => 'Admin panel';

  @override
  String get adminUsersTitle => 'Users';

  @override
  String get adminSearchHint => 'Search by name, phone, email, or ID';

  @override
  String get adminNoUsers => 'No users found';

  @override
  String get adminYouBadge => 'You';

  @override
  String get adminTopUpAction => 'Top up balance';

  @override
  String get adminAmountSomoni => 'Amount, somoni';

  @override
  String get adminGivePremium => 'Grant premium';

  @override
  String get adminRemovePremium => 'Remove premium';

  @override
  String get adminMakeAdmin => 'Make admin';

  @override
  String get adminRemoveAdmin => 'Remove admin rights';

  @override
  String get adminBalanceUpdated => 'Balance updated';

  @override
  String get stepMoreOptionsTitle => 'More options';

  @override
  String get typeGenerateAll => 'Everything at once';

  @override
  String get typeGenerateAllDesc =>
      'Konspekt, test, presentation and lecture for one topic, generated together';

  @override
  String get generateAllLoadingDesc =>
      'This takes a bit longer — 4 materials are being generated one after another';

  @override
  String generateAllResultTitle(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count materials generated',
      one: '$count material generated',
    );
    return '$_temp0';
  }

  @override
  String generateAllSkippedNote(String types) {
    return 'Couldn\'t be generated: $types';
  }

  @override
  String get typeCurriculum => 'Bundle (several topics)';

  @override
  String get typeCurriculumDesc =>
      'Give a list of topics and a date range — one konspekt per topic, generated together as a course';

  @override
  String get curriculumMyListTitle => 'My bundles';

  @override
  String get curriculumImportDocx => 'Import from .docx';

  @override
  String get curriculumTopicsLabel => 'Topics';

  @override
  String get curriculumTopicsHint =>
      'One topic per line, e.g.:\nVariables and data types\nConditionals\nLoops';

  @override
  String get curriculumDateRangeLabel => 'Date range';

  @override
  String get curriculumRestDaysLabel => 'Days off';

  @override
  String get curriculumCreateButton => 'Create bundle';

  @override
  String curriculumProgress(int done, int total) {
    return 'Generating: $done of $total';
  }

  @override
  String curriculumProgressDone(int done, int total) {
    return 'Ready: $done of $total';
  }

  @override
  String get curriculumExamBadge => 'TEST';

  @override
  String get curriculumStatusDraft => 'Draft';

  @override
  String get curriculumStatusGenerating => 'Generating';

  @override
  String get curriculumStatusReady => 'Ready';

  @override
  String get curriculumStatusPartialFailed => 'Some days failed';

  @override
  String get curriculumNoBundles => 'You haven\'t created any bundles yet';

  @override
  String get curriculumStartGeneration => 'Start generation';

  @override
  String get curriculumDraftHint =>
      'Review the topics before generating — tap a topic to change it.';

  @override
  String get curriculumEditTopicTitle => 'Edit topic';

  @override
  String get curriculumDuplicate => 'Duplicate';

  @override
  String curriculumNotifReadyTitle(String title) {
    return '✅ \"$title\" is ready!';
  }

  @override
  String curriculumNotifReadyBody(int total) {
    return 'All $total lessons were created successfully. Tap to view.';
  }

  @override
  String curriculumNotifPartialTitle(String title) {
    return '⚠ \"$title\" partially ready';
  }

  @override
  String curriculumNotifPartialBody(int done, int total) {
    return '$done of $total lessons are ready — some failed, retry them in the app.';
  }

  @override
  String get adminTotalUsers => 'Users';

  @override
  String get adminTotalMaterials => 'Materials';

  @override
  String get adminTotalCurriculums => 'Bundles';

  @override
  String get navAdminDashboard => 'Dashboard';

  @override
  String get navAdminUsers => 'Users';

  @override
  String get topUpTitle => 'Top up balance';

  @override
  String get topUpAmountLabel => 'Amount, somoni';

  @override
  String get topUpAmountHelp =>
      '1 konspekt, test, presentation or lecture = 50 dirams';

  @override
  String get topUpPayButton => 'Go to payment';

  @override
  String get topUpProvider => 'Payment via Dushanbe City';

  @override
  String get topUpInvalidAmount => 'Enter an amount between 1 and 1000 somoni';

  @override
  String get topUpOpenFailed => 'Could not open the payment page';

  @override
  String get topUpWaiting => 'Waiting for the bank to confirm the payment…';

  @override
  String get topUpCheckStatus => 'Check status';

  @override
  String get topUpContinuePayment => 'Continue payment';

  @override
  String topUpSuccess(String amount) {
    return 'Balance topped up by $amount somoni';
  }

  @override
  String get topUpStillPending =>
      'The payment is still being processed. Your balance will be topped up automatically once the bank confirms it.';

  @override
  String get topUpFailed => 'The payment did not go through';

  @override
  String get topUpCanceled => 'Payment canceled';

  @override
  String get topUpHistory => 'Top-up history';

  @override
  String get topUpHistoryEmpty => 'No top-ups yet';

  @override
  String get topUpStatusPending => 'Processing';

  @override
  String get topUpStatusCompleted => 'Credited';

  @override
  String get topUpStatusFailed => 'Failed';

  @override
  String get topUpStatusCanceled => 'Canceled';

  @override
  String get lectureTemplateLabel => 'Lecture template';

  @override
  String get tmplPlanspektName => 'Lesson plan';

  @override
  String get tmplPlanspektDesc => 'Concise working format, no cover page';

  @override
  String get tmplAkademikName => 'Academic';

  @override
  String get tmplAkademikDesc => 'Title page, serif type, thin rules';

  @override
  String get tmplZamonaviyName => 'Modern';

  @override
  String get tmplZamonaviyDesc => 'Colour panel, large numerals, cards';

  @override
  String get tmplJurnalName => 'Editorial';

  @override
  String get tmplJurnalDesc => 'Banner cover, sections on a colour band';

  @override
  String get tmplPraktikumName => 'Worksheet';

  @override
  String get tmplPraktikumDesc => 'Frame, name fields, room to write';

  @override
  String get profileContact => 'Contact';

  @override
  String get contactEmail => 'Email';

  @override
  String get registerTerms => 'Terms of use';

  @override
  String get registerPrivacy => 'Privacy policy';

  @override
  String get gamesTitle => 'Games';

  @override
  String get gamesDesc => 'Educational games with AI-written questions';

  @override
  String get gameTemplatesTitle => 'Game templates';

  @override
  String get gameTemplatesPrompt =>
      'Pick a game template first, then we will set it up.';

  @override
  String get gameMagicBoxName => 'Magic boxes';

  @override
  String get gameMagicBoxDesc =>
      'Hide a question in the boxes, shuffle them, then pick the right one.';

  @override
  String get gameSecLabName => 'Secret laboratory';

  @override
  String get gameSecLabDesc =>
      'Enter the secret lab, answer the questions and run the great experiment!';

  @override
  String get gameMoreSoonTitle => 'New templates';

  @override
  String get gameMoreSoonDesc => 'More games are coming soon';

  @override
  String get gameSelect => 'Choose';

  @override
  String get gameRoundsLabel => 'Number of rounds';

  @override
  String get gameTopicHint => 'For example: Substances';

  @override
  String get gameNoQuestions =>
      'The AI produced no questions. Please try again.';

  @override
  String get gamePreparingQuestions => 'Preparing questions...';

  @override
  String get gamePreparingGame => 'Setting the game up';

  @override
  String get gameMagicBoxSubtitle => 'The AI will write the questions for you';

  @override
  String get gameStart => 'Start the game';

  @override
  String get gameSecLabSubtitle => 'Experiment settings';

  @override
  String get gameSecLabStart => 'Start the experiment';

  @override
  String get gameMemorize => 'Memorise the questions carefully!';

  @override
  String get gamePlacingQuestions => 'Putting the questions into the boxes...';

  @override
  String get gameAttention => 'Get ready!';

  @override
  String get gameGo => 'Go!';

  @override
  String get gameShuffling => 'Shuffling the boxes...';

  @override
  String get gamePickBox => 'Now pick a box!';

  @override
  String get gameNewExperiment => 'New experiment! 🧪';

  @override
  String get gameQuestion => 'QUESTION';

  @override
  String get gamePickReagent => 'PICK A REAGENT!';

  @override
  String get gameCorrectCheer => 'Well done! Correct answer! ✅';

  @override
  String get gameRound => 'ROUND';

  @override
  String get gameWrongAnswer => 'Wrong answer!';

  @override
  String get gameYourAnswer => 'YOUR ANSWER';

  @override
  String get gameCorrectAnswer => 'CORRECT ANSWER';

  @override
  String get gameWhyCorrect => 'WHY IS THIS THE RIGHT ANSWER? 💡';

  @override
  String get gameContinue => 'Continue';

  @override
  String get gameScore => 'Score';

  @override
  String get gameCorrectCount => 'Correct answers';

  @override
  String get gameWrongCount => 'Wrong answers';

  @override
  String get gameAccuracy => 'Accuracy';

  @override
  String get gameOver => 'Game over';

  @override
  String get gameCongrats => 'Congratulations! 🎉';

  @override
  String get gameFinishedSuccess => 'You finished the game successfully!';

  @override
  String get gamePlayAgain => 'Play again';

  @override
  String get gameBackToTemplates => 'Back to templates';

  @override
  String gameQuestionLetter(String letter) {
    return 'QUESTION $letter';
  }

  @override
  String gameBoxNumber(int number) {
    return 'Box $number';
  }

  @override
  String gameQuestionsPerRound(int perRound, int total) {
    return '$perRound questions per round, $total questions in total.';
  }

  @override
  String get langRu => 'Russian';

  @override
  String get langTg => 'Tajik';

  @override
  String get langEn => 'English';

  @override
  String get weekdayMon => 'Mon';

  @override
  String get weekdayTue => 'Tue';

  @override
  String get weekdayWed => 'Wed';

  @override
  String get weekdayThu => 'Thu';

  @override
  String get weekdayFri => 'Fri';

  @override
  String get weekdaySat => 'Sat';

  @override
  String get weekdaySun => 'Sun';

  @override
  String get subjTajikLang => 'Tajik language';

  @override
  String get subjTajikLit => 'Tajik literature';

  @override
  String get subjRussianLang => 'Russian language';

  @override
  String get subjEnglishLang => 'English language';

  @override
  String get subjMath => 'Mathematics';

  @override
  String get subjAlgebra => 'Algebra';

  @override
  String get subjGeometry => 'Geometry';

  @override
  String get subjInformatics => 'Computer science';

  @override
  String get subjPhysics => 'Physics';

  @override
  String get subjChemistry => 'Chemistry';

  @override
  String get subjBiology => 'Biology';

  @override
  String get subjGeography => 'Geography';

  @override
  String get subjHistoryTj => 'History of Tajikistan';

  @override
  String get subjHistoryWorld => 'World history';

  @override
  String get subjNatureStudy => 'Nature study';

  @override
  String get subjFineArt => 'Fine art';

  @override
  String get subjMusic => 'Music';

  @override
  String get subjTechnology => 'Technology';

  @override
  String get subjPhysEd => 'Physical education';

  @override
  String get subjLawBasics => 'Basics of state and law';

  @override
  String get balanceTitle => 'Balance';

  @override
  String get balanceCurrent => 'Current balance';

  @override
  String get currencySomoni => 'somoni';

  @override
  String get balanceTopUpTitle => 'How to top up';

  @override
  String get balanceTopUpBody =>
      'Message the Dastyor team and they will send you payment instructions.';

  @override
  String get balanceTopUpBodyEmailOnly =>
      'Email the Dastyor team and they will send you payment instructions.';

  @override
  String get balanceNoPaymentNote =>
      'Payments are not taken inside the app. Your balance changes once the Dastyor team confirms the payment.';

  @override
  String get contactChannelsUnconfigured =>
      'Telegram and WhatsApp are not set up yet.';

  @override
  String get contactOpenFailed => 'Couldn’t open the link';

  @override
  String get helpTitle => 'Help and contact';

  @override
  String get helpIntro =>
      'Write to us if something is not working or you need payment instructions.';

  @override
  String get navBalance => 'Balance';

  @override
  String get balanceTelegramTitle => '🔗 Connect Telegram';

  @override
  String get balanceTelegramSubtitle =>
      'Tap the button to securely link Telegram to your Dastyor account with a one-time link. Then choose an amount and send the receipt in the bot; an administrator will verify the payment.';

  @override
  String get balanceTelegramButton => '🔗 Link Dastyor account';

  @override
  String get balanceTelegramButtonLinked => '🤖 Open Telegram bot';

  @override
  String get balanceTelegramLinkedNote =>
      '✅ Your account is already linked to the bot.';

  @override
  String get balanceTelegramFailed =>
      'Couldn’t create the linking link. Please try again.';

  @override
  String get balanceTelegramUnavailable =>
      'Telegram top-up is not configured yet.';
}
