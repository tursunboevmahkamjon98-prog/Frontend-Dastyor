import type { Metadata, Viewport } from "next";
import { Inter, Inter_Tight, JetBrains_Mono } from "next/font/google";
import "./globals.css";


import "katex/dist/katex.min.css";
import { AuthProvider } from "@/lib/auth-context";
import { LocaleProvider } from "@/lib/i18n";
import { ThemeProvider } from "@/lib/theme";
import { THEME_INIT_SCRIPT } from "@/lib/theme-script";

/* Every font here declares cyrillic-ext, and that is not optional: Tajik
 * sits in Cyrillic Extended, not in `cyrillic`. The six letters it needs
 * beyond Russian - ғ ӣ қ ӯ ҳ ҷ (U+0493, U+04E3, U+049B, U+04EF, U+04B3,
 * U+04B7) - are all above U+045F, so a `["latin", "cyrillic"]` subset list
 * emits no @font-face covering them and the browser substitutes a system
 * face for those glyphs alone. The result is a word like "Тоҷикӣ" rendered
 * in two fonts at once, which is what the language switcher did before.
 *
 * Interface and display are the same family at two widths rather than two
 * families: Inter Tight is Inter's narrower cut, so headings get their own
 * presence without a second set of letterforms to reconcile - and without a
 * second Cyrillic design to proof.
 *
 * The list is repeated per call rather than hoisted into a constant on
 * purpose: next/font reads these options at build time with a static
 * parser, so every value has to be a literal at the call site. A shared
 * array - even `as const`, even spread - is a build error, not a refactor. */
const sans = Inter({
  variable: "--font-sans-src",
  subsets: ["latin", "latin-ext", "cyrillic", "cyrillic-ext"],
});

const display = Inter_Tight({
  variable: "--font-display-src",
  subsets: ["latin", "latin-ext", "cyrillic", "cyrillic-ext"],
});

const mono = JetBrains_Mono({
  variable: "--font-mono-src",
  subsets: ["latin", "latin-ext", "cyrillic", "cyrillic-ext"],
});

export const metadata: Metadata = {
  title: "Dastyor — учебные материалы с помощью ИИ",
  description:
    "ИИ-помощник для учителей: создавайте конспект, тест, презентацию, лекцию и целый учебный план за несколько секунд.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Dastyor",
  },
};




export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  /* Matches --color-primary. Paints the Android address bar and the PWA
   * splash, so it is brand, not chrome. */
  themeColor: "#e11d2e",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ru"
      suppressHydrationWarning
      className={`${sans.variable} ${display.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <ThemeProvider>
          <LocaleProvider>
            <AuthProvider>{children}</AuthProvider>
          </LocaleProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
