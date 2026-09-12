import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
// KaTeX's stylesheet — needed globally by components/konspekt/MathText.tsx,
// which renders every konspekt's inline `$...$` formulas client-side.
import "katex/dist/katex.min.css";
import { AuthProvider } from "@/lib/auth-context";
import { LocaleProvider } from "@/lib/i18n";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin", "cyrillic"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
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

// mobile-first: works as a normal responsive website in any Android/iOS
// browser; the PWA manifest additionally lets it be "added to home screen"
// for an app-like full-screen feel without needing a native .apk build.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#dc2626",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ru"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        {/* LocaleProvider outermost: it swaps <html lang> and every string
            below it, including the ones AuthProvider's subtree renders. */}
        <LocaleProvider>
          <AuthProvider>{children}</AuthProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
