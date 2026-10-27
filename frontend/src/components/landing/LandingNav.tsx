"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import Logo from "@/components/Logo";
import LocaleSwitcher from "@/components/LocaleSwitcher";
import { useT } from "@/lib/i18n";
import { NAV_LINKS } from "./sections";

/* The landing header.
 *
 * The version this replaces hid its section links behind `hidden md:flex`
 * with nothing in their place, so a phone — which is most of this
 * product's traffic — got a header with a logo and two buttons and no way
 * to reach any section of the page it was sitting on top of. The links now
 * move into a real panel.
 */
export default function LandingNav() {
  const t = useT();
  const [open, setOpen] = useState(false);

  /* The panel is portalled to <body>, and it has to be.
   *
   * The header below carries `backdrop-blur`, and a backdrop-filter makes
   * an element a containing block for its `position: fixed` descendants —
   * so a panel rendered inside the header resolves `inset-0` against the
   * 64px header box rather than the viewport, and gets clipped to a strip
   * with its links scrolled out of sight. The content was all there; it
   * was invisible. SamplesGallery portals its lightbox for the same class
   * of reason.
   *
   * No mounted guard is needed: `open` only ever becomes true from a
   * click, so the portal — and the `document` reference in it — is never
   * reached during server rendering. */

  /* Hold the page still while the panel is up, and give Escape the same
   * job as the close button. Restoring the previous overflow rather than
   * clearing it keeps this from fighting any other lock. */
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <header className="sticky top-0 z-40 border-b border-border-light/80 bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-7xl items-center gap-3 px-4 py-3.5 sm:gap-4 sm:px-6 lg:px-8">
        <Link href="/" aria-label="Dastyor" className="shrink-0">
          <Logo height="1.875rem" />
        </Link>

        <nav className="ml-6 hidden items-center gap-0.5 lg:flex">
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-control px-3 py-2 text-meta font-medium text-text-secondary transition-colors duration-150 hover:bg-surface-muted hover:text-text-primary"
            >
              {t(l.labelKey)}
            </a>
          ))}
        </nav>

        <div className="ml-auto flex min-w-0 shrink-0 items-center gap-1.5 sm:gap-2">
          <div className="hidden sm:block">
            <LocaleSwitcher />
          </div>
          <Link
            href="/login"
            className="hidden rounded-control px-3.5 py-2 text-meta font-semibold text-text-primary transition-colors duration-150 hover:bg-surface-muted sm:inline-block"
          >
            {t("login.submit")}
          </Link>
          <Link
            href="/register"
            className="hidden whitespace-nowrap rounded-control bg-primary px-4 py-2 text-meta font-semibold text-white transition-colors duration-150 hover:bg-primary-dark sm:inline-block"
          >
            {t("landing.start")}
          </Link>
          <button
            type="button"
            onClick={() => setOpen(true)}
            aria-label={t("landing.nav.menu")}
            aria-expanded={open}
            className="flex h-9 w-9 items-center justify-center rounded-control border border-border text-text-primary transition-colors duration-150 hover:bg-surface-muted lg:hidden"
          >
            <Menu className="h-4.5 w-4.5" strokeWidth={2} />
          </button>
        </div>
      </div>

      {open && createPortal(
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label={t("landing.nav.closeMenu")}
            onClick={() => setOpen(false)}
            className="absolute inset-0 h-full w-full cursor-default bg-text-primary/35 backdrop-blur-[2px]"
          />
          <div className="absolute inset-x-0 top-0 flex max-h-full flex-col overflow-y-auto border-b border-border-light bg-surface p-4 shadow-float">
            <div className="mb-5 flex items-center justify-between gap-4">
              <Logo height="1.75rem" />
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label={t("landing.nav.closeMenu")}
                className="flex h-9 w-9 items-center justify-center rounded-control border border-border text-text-primary transition-colors duration-150 hover:bg-surface-muted"
              >
                <X className="h-4.5 w-4.5" strokeWidth={2} />
              </button>
            </div>

            <nav className="flex flex-col">
              {NAV_LINKS.map((l) => (
                <a
                  key={l.href}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="border-b border-border-light py-3 text-subheading font-medium text-text-primary transition-colors duration-150 hover:text-primary-accent"
                >
                  {t(l.labelKey)}
                </a>
              ))}
            </nav>

            <div className="mt-5 flex flex-col gap-2.5">
              <Link
                href="/register"
                onClick={() => setOpen(false)}
                className="rounded-control bg-primary px-4 py-3 text-center text-body font-semibold text-white transition-colors duration-150 hover:bg-primary-dark"
              >
                {t("landing.hero.ctaPrimary")}
              </Link>
              <Link
                href="/login"
                onClick={() => setOpen(false)}
                className="rounded-control border border-border px-4 py-3 text-center text-body font-semibold text-text-primary transition-colors duration-150 hover:bg-surface-muted"
              >
                {t("login.submit")}
              </Link>
            </div>

            <div className="mt-5 flex justify-center">
              <LocaleSwitcher />
            </div>
          </div>
        </div>,
        document.body,
      )}
    </header>
  );
}
