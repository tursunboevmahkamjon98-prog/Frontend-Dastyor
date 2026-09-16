import { PRESENTATION_TEMPLATES } from "./material-types";



export type SubjectTemplate = {
  id: string;
  name: string;
  
  note: string;
  accent: string;
  support: string;
  bg: string;
  ink: string;
  
  header:
    | "rule" | "underline" | "band" | "smallcaps" | "index" | "measure"
    | "hexband" | "lozenge" | "masthead" | "prompt" | "initial" | "ornamental";
  card:
    | "rounded" | "sharp" | "tab" | "hex" | "pill" | "legend" | "plaque"
    | "window" | "quote" | "framed" | "bubble" | "ornate" | "pastel";
  marker:
    | "number" | "square" | "hexagon" | "diamond" | "chevron" | "dot"
    | "pin" | "roman" | "bracket" | "dash" | "star" | "circle" | "leaf" | "triangle";
  decor:
    | "grid" | "symbols" | "construction" | "wave" | "hexlattice" | "organic"
    | "contour" | "timeline" | "dots" | "ruled" | "ornament" | "letters"
    | "girih" | "network" | "cycle" | "none";
  
  cover: string;
  serif?: boolean;
};

export const SUBJECT_TEMPLATES: SubjectTemplate[] = [
  {
    id: "mathematics", name: "Математика",
    note: "Клетчатое поле, жёсткая левая линейка, квадратные маркеры",
    accent: "#4A3AA7", support: "#C7D2FE", bg: "#FFFFFF", ink: "#16192B",
    header: "index", card: "sharp", marker: "square", decor: "grid",
    cover: "axis",
  },
  {
    id: "algebra", name: "Алгебра",
    note: "Поле операторов на полях — символьный характер вместо построений",
    accent: "#7C3AED", support: "#DDD6FE", bg: "#FFFFFF", ink: "#16192B",
    header: "index", card: "sharp", marker: "square", decor: "symbols",
    cover: "axis",
  },
  {
    id: "geometry", name: "Геометрия",
    note: "Циркульные дуги и линии построения, треугольные маркеры",
    accent: "#0F9B6E", support: "#A7F3D0", bg: "#FFFFFF", ink: "#16192B",
    header: "index", card: "sharp", marker: "triangle", decor: "construction",
    cover: "construction",
  },
  {
    id: "physics", name: "Физика",
    note: "Волна по нижнему краю, шкала под заголовком, шевроны",
    accent: "#EB6834", support: "#FED7AA", bg: "#FCFCFD", ink: "#1B2029",
    header: "measure", card: "tab", marker: "chevron", decor: "wave",
    cover: "trajectory",
  },
  {
    id: "chemistry", name: "Химия",
    note: "Цепочка гексагонов, карточки со срезанными углами",
    accent: "#0891B2", support: "#A5F3FC", bg: "#FBFDFE", ink: "#15242B",
    header: "hexband", card: "hex", marker: "hexagon", decor: "hexlattice",
    cover: "molecule",
  },
  {
    id: "biology", name: "Биология",
    note: "Мягкие органические формы, карточки-пилюли",
    accent: "#008300", support: "#BBF7D0", bg: "#FCFEFC", ink: "#16261A",
    header: "lozenge", card: "pill", marker: "dot", decor: "organic",
    cover: "organic",
  },
  {
    id: "geography", name: "География",
    note: "Горизонтали рельефа, карточки-легенды, маркер-вершина",
    accent: "#A3702D", support: "#FDE68A", bg: "#FDFCF9", ink: "#26201A",
    header: "smallcaps", card: "legend", marker: "pin", decor: "contour",
    cover: "globe",
  },
  {
    id: "history", name: "История Таджикистана",
    note: "Антиква, двойная линейка, лента времени, римские цифры",
    accent: "#8A2635", support: "#E7D3B5", bg: "#FDFBF6", ink: "#241B17",
    header: "masthead", card: "plaque", marker: "roman", decor: "timeline",
    cover: "banner", serif: true,
  },
  {
    id: "history_world", name: "Всемирная история",
    note: "То же построение, своя палитра периода",
    accent: "#B5502E", support: "#EED9BE", bg: "#FDFBF6", ink: "#241B17",
    header: "masthead", card: "plaque", marker: "roman", decor: "timeline",
    cover: "banner", serif: true,
  },
  {
    id: "informatics", name: "Информатика",
    note: "Точечный холст редактора, окно с хромом, индексы в скобках",
    accent: "#2A78D6", support: "#BFDBFE", bg: "#FBFCFE", ink: "#151C26",
    header: "prompt", card: "window", marker: "bracket", decor: "dots",
    cover: "terminal",
  },
  {
    id: "russian", name: "Русский язык",
    note: "Тетрадная линовка, красное поле, карточки-цитаты",
    accent: "#C62839", support: "#FBCFD3", bg: "#FFFDFD", ink: "#231619",
    header: "initial", card: "quote", marker: "dash", decor: "ruled",
    cover: "page", serif: true,
  },
  {
    id: "literature", name: "Таджикская литература",
    note: "Книжная рамка, типографский орнамент, ромбы",
    accent: "#6B3FA0", support: "#E9D5FF", bg: "#FCFAFF", ink: "#20182B",
    header: "ornamental", card: "framed", marker: "diamond", decor: "ornament",
    cover: "frontispiece", serif: true,
  },
  {
    id: "english", name: "Английский язык",
    note: "Речевые облака, крупные литеры на полях",
    accent: "#1D5FC2", support: "#BFDBFE", bg: "#FCFDFF", ink: "#161E2B",
    header: "rule", card: "bubble", marker: "dot", decor: "letters",
    cover: "bubble",
  },
  {
    id: "tajik", name: "Таджикский язык",
    note: "Геометрический орнамент-гирих, звёздные маркеры",
    accent: "#0E7C86", support: "#99F6E4", bg: "#FCFEFE", ink: "#132326",
    header: "smallcaps", card: "ornate", marker: "star", decor: "girih",
    cover: "ornament",
  },
  {
    id: "social_studies", name: "Обществознание",
    note: "Граф связей, сплошная шапка, круглые маркеры",
    accent: "#4338CA", support: "#C7D2FE", bg: "#FCFCFE", ink: "#181B2A",
    header: "band", card: "rounded", marker: "circle", decor: "network",
    cover: "nodes",
  },
  {
    id: "ecology", name: "Экология",
    note: "Кольцо круговорота, мягкие карточки",
    accent: "#0E9F6E", support: "#A7F3D0", bg: "#FBFEFB", ink: "#132520",
    header: "lozenge", card: "pill", marker: "leaf", decor: "cycle",
    cover: "cycle",
  },
  {
    id: "primary_school", name: "Начальные классы",
    note: "Тетрадь на пружине, разноцветные карточки",
    accent: "#E4572E", support: "#FFD166", bg: "#FFFDF7", ink: "#2D2A4A",
    header: "rule", card: "pastel", marker: "star", decor: "none",
    cover: "notebook",
  },
  {
    id: "general", name: "Общий",
    note: "Нейтральное оформление для предмета вне списка",
    accent: "#3B82F6", support: "#DBEAFE", bg: "#FFFFFF", ink: "#1E2937",
    header: "rule", card: "rounded", marker: "number", decor: "none",
    cover: "standard",
  },
];


export const SUBJECT_TEMPLATE_BY_SUBJECT: Record<string, string> = {
  "Математика": "mathematics",
  "Алгебра": "algebra",
  "Геометрия": "geometry",
  "Физика": "physics",
  "Химия": "chemistry",
  "Биология": "biology",
  "География": "geography",
  "История Таджикистана": "history",
  "Всемирная история": "history_world",
  "Информатика": "informatics",
  "Русский язык": "russian",
  "Таджикская литература": "literature",
  "Английский язык": "english",
  "Таджикский язык": "tajik",
  "Обществознание": "social_studies",
  "Экология": "ecology",
  "Начальные классы": "primary_school",
};

const GENERAL = SUBJECT_TEMPLATES[SUBJECT_TEMPLATES.length - 1];

export function templateById(id: string | null | undefined): SubjectTemplate | undefined {
  return SUBJECT_TEMPLATES.find((t) => t.id === String(id ?? "").trim());
}


export function subjectTemplateFor(subject: string | null | undefined): SubjectTemplate {
  const id = SUBJECT_TEMPLATE_BY_SUBJECT[String(subject ?? "").trim()];
  return (id ? templateById(id) : undefined) ?? GENERAL;
}


export function deckTemplateName(templateId: string | null | undefined): string {
  const id = String(templateId ?? "").trim();
  return (
    templateById(id)?.name ??
    PRESENTATION_TEMPLATES.find((t) => t.id === id)?.name ??
    "—"
  );
}
