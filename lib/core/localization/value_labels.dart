import '../../l10n/gen/app_localizations.dart';
import '../constants/subjects.dart';

















String languageLabel(AppLocalizations t, String value) => switch (value) {
      'Таджикский' => t.langTg,
      'Английский' => t.langEn,
      _ => t.langRu,
    };



String weekdayShort(AppLocalizations t, int index) => switch (index) {
      1 => t.weekdayTue,
      2 => t.weekdayWed,
      3 => t.weekdayThu,
      4 => t.weekdayFri,
      5 => t.weekdaySat,
      6 => t.weekdaySun,
      _ => t.weekdayMon,
    };






String subjectLabel(AppLocalizations t, String value) => switch (value) {
      'Таджикский язык' => t.subjTajikLang,
      'Таджикская литература' => t.subjTajikLit,
      'Русский язык' => t.subjRussianLang,
      'Английский язык' => t.subjEnglishLang,
      'Математика' => t.subjMath,
      'Алгебра' => t.subjAlgebra,
      'Геометрия' => t.subjGeometry,
      'Информатика' => t.subjInformatics,
      'Физика' => t.subjPhysics,
      'Химия' => t.subjChemistry,
      'Биология' => t.subjBiology,
      'География' => t.subjGeography,
      'История Таджикистана' => t.subjHistoryTj,
      'Всемирная история' => t.subjHistoryWorld,
      'Природоведение' => t.subjNatureStudy,
      'Изобразительное искусство' => t.subjFineArt,
      'Музыка' => t.subjMusic,
      'Технология' => t.subjTechnology,
      'Физическая культура' => t.subjPhysEd,
      'Основы государства и права' => t.subjLawBasics,
      _ => value,
    };
