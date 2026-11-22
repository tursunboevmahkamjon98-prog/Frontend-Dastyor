import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";


import "katex/dist/katex.min.css";
import { AuthProvider } from "@/lib/auth-context";
import { LocaleProvider } from "@/lib/i18n";

/* Self-hosted via the `geist` npm package (next/font/local under the hood)
 * instead of next/font/google — the Google Fonts CDN fetch that API needs
 * at compile time has proven unreliable on this network (repeated "Module
 * not found: @vercel/turbopack-next/internal/font/google/font" build
 * errors), and since this font loads in the root layout, that failure took
 * down every page, not just the one that happened to trigger a fresh
 * fetch. Verified before switching (via fontTools) that both
 * Geist-Variable.woff2 and GeistMono-Variable.woff2 actually contain the
 * Tajik-specific extended Cyrillic letters (ғ ӣ қ ӯ ҳ ҷ, U+0492/049A/04E2/
 * 04EE/04B2/04B6 and their lowercase pairs) — not just the basic Russian
 * Cyrillic set — since this app's primary content language depends on
 * them rendering correctly. */

export const metadata: Metadata = {
  title: "Rahnamo — учебные материалы с помощью ИИ",
  description:
    "ИИ-помощник для учителей: создавайте конспект, тест, презентацию, лекцию и целый учебный план за несколько секунд.",
  manifest: "/manifest.json",
  icons: {
    icon: "/brand/rahnamo-mark-tight.png",
    apple: "/brand/rahnamo-mark-tight.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Rahnamo",
  },
};




export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#dc2626",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ru"
      className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        {}
        <LocaleProvider>
          <AuthProvider>{children}</AuthProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
