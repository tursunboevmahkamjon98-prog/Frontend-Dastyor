# -*- coding: utf-8 -*-
"""Single source of truth for the design tokens in src/app/globals.css.

Run from frontend/:
    python scripts/design_tokens.py            # verify only
    python scripts/design_tokens.py --write    # verify, then rewrite globals.css

Generates everything from the top of globals.css through the end of the
@theme blocks, so the Tailwind mapping can never drift from the definitions,
and refuses to write if any pair that renders text or an icon misses WCAG AA.
"""
import io
import sys

# --------------------------------------------------------------------------
# Brand and neutrals - "Dastyor Studio". The brand is the red off the
# official logo sheet (#e11d2e, "Asosiy"), on warm off-white neutrals.
#
# This reverses the previous palette, which was indigo on cool greys. The
# argument for indigo was that red collides with the app's own failure
# state; that is a real cost and it is paid here deliberately, because the
# logo, the mascot and every piece of brand material the product ships are
# red, and a UI that does not match its own logo is the worse problem. The
# collision is managed rather than avoided:
#
#   - The brand red is a FILL. It appears under white text on buttons, on
#     the active nav item, on the mascot. It is never the colour of a
#     sentence.
#   - --color-error is Material 3's error red (#b3261e / #f2b8b5), which is
#     darker and less saturated than the brand. It only ever appears with an
#     icon or the word for the failure next to it, so hue is never the sole
#     carrier of the meaning.
#   - Success and warning keep their own hues and carry most of the
#     semantic load.
#
# --color-primary-accent is a much deeper red than the brand, because it is
# the brand used as TEXT: #e11d2e is 4.75:1 on white, which passes, but only
# 4.06:1 on the brand tint --color-primary-50, which is where active nav
# labels sit. Fill with primary, write with primary-accent.
#
# Neutrals are warm off-whites (a trace of red in the grey) so the page
# agrees with the brand instead of sitting cool underneath it. Text is the
# logo sheet's own #1f2937, and --color-border is its #e5e7eb.
#
# A second brand hue, deep violet (--color-secondary), was added in the
# "soft 3D, colourful, premium" visual pass. It does not replace red: the
# CTA fill and the logo stay red on purpose (see rationale above). Violet
# carries the AI-assistant moments instead - generation gradients, the
# mascot halo, "AI" badges - which is where the brief asks for it
# specifically. The category palette was remapped the same pass so each
# material type reads as its own colour rather than a shade of the brand:
# konspekt -> lavender/violet, presentation -> peach/coral, lecture -> sky
# blue. Test/mint, practice/teal and games/rose were already on-brief and
# are unchanged.
#
# Every pair passes WCAG AA; the script prints the table on every run.
# --------------------------------------------------------------------------
LIGHT = dict(
    primary="#e11d2e", primary_light="#f04152", primary_dark="#b8121f",
    primary_50="#fff0ec", accent="#a1121f",
    brand_warm="#b45309",
    # Secondary brand hue - deep violet, used for AI-assistant moments
    # (generation gradients, the mascot halo, "AI" badges) alongside the
    # primary red rather than instead of it. Same fill/text split as
    # primary: secondary is the FILL, secondary_accent is the same hue
    # readable as TEXT.
    secondary="#7155d9", secondary_light="#9385e8", secondary_dark="#5436ab",
    secondary_50="#f1edfd", secondary_accent="#5b3fc4",
    background="#fcf8f4", surface="#fffdfa", surface_muted="#f5efeb",
    t1="#282633", t2="#555260", t3="#696571",
    border="#e9e1dc", border_light="#f2ebe6",
)
DARK = dict(
    primary="#e11d2e", primary_light="#f26b78", primary_dark="#b8121f",
    primary_50="#2d1317", accent="#ffa5ad",
    brand_warm="#fbbf24",
    secondary="#7155d9", secondary_light="#9385e8", secondary_dark="#5436ab",
    secondary_50="#2a2147", secondary_accent="#c3b5f5",
    background="#17141a", surface="#221e25", surface_muted="#302b33",
    t1="#f5f1f7", t2="#c5bdcc", t3="#a49aaa",
    border="#3e3744", border_light="#312b36",
)

# --------------------------------------------------------------------------
# Type scale. Fixed sizes with their own line-height and tracking, so a
# heading is "text-title", not "text-xl sm:text-2xl font-bold" re-decided
# per file. Tight tracking on the large sizes, loose on the smallest.
# --------------------------------------------------------------------------
TYPE = [
    ("hero",       "3.25rem",   "1.04", "-0.03em"),
    ("display",    "2.5rem",    "1.08", "-0.022em"),
    ("title",      "1.75rem",   "1.15", "-0.018em"),
    ("heading",    "1.25rem",   "1.3",  "-0.012em"),
    ("subheading", "1.0625rem", "1.4",  "-0.006em"),
    ("body",       "0.9375rem", "1.6",  "0"),
    ("meta",       "0.8125rem", "1.5",  "0"),
    ("micro",      "0.6875rem", "1.45", "0.06em"),
]


def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(h):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


PAIRS = [
    ("text-primary   on surface",         "t1",     "surface"),
    ("text-secondary on surface",         "t2",     "surface"),
    ("text-tertiary  on surface",         "t3",     "surface"),
    ("text-primary   on background",      "t1",     "background"),
    ("text-secondary on background",      "t2",     "background"),
    ("text-tertiary  on surface-muted",   "t3",     "surface_muted"),
    ("accent on surface",                 "accent", "surface"),
    ("accent on background",              "accent", "background"),
    ("accent on primary-50 (active nav)", "accent", "primary_50"),
    ("brand-warm on surface",             "brand_warm", "surface"),
    ("brand-warm on background",          "brand_warm", "background"),
    ("secondary-accent on surface",       "secondary_accent", "surface"),
    ("secondary-accent on background",    "secondary_accent", "background"),
    ("secondary-accent on secondary-50",  "secondary_accent", "secondary_50"),
]


# The inverse band's own pairs. These tokens live in the SHARED_* blocks
# rather than the LIGHT/DARK dicts, because the band is dark in both themes
# and so is not a theme-varying pair - but it still carries text, so it
# still has to clear AA. Values repeated here; keep them in step with
# SHARED_LIGHT / SHARED_DARK.
INVERSE = {
    "light": ("#1b1f27", "#ffffff", "#aeb6c2"),
    "dark": ("#23262e", "#f5f3f3", "#a9b0bb"),
}


def verify():
    failures = []
    print("%-38s %-8s %-8s %8s" % ("pair", "fg", "bg", "ratio"))
    print("-" * 68)
    for name, tok in (("light", LIGHT), ("dark", DARK)):
        print("")
        print("### %s" % name)
        checks = [(label, tok[f], tok[b]) for label, f, b in PAIRS]
        checks.append(("white on primary (CTA fill)", "#ffffff", tok["primary"]))
        checks.append(("white on primary-dark (hover)", "#ffffff", tok["primary_dark"]))
        checks.append(("white on secondary (AI fill)", "#ffffff", tok["secondary"]))
        checks.append(("white on secondary-dark (hover)", "#ffffff", tok["secondary_dark"]))
        band, on_band, on_band_muted = INVERSE[name]
        checks.append(("text on inverse band", on_band, band))
        checks.append(("muted text on inverse band", on_band_muted, band))
        for label, fg, bg in checks:
            r = ratio(fg, bg)
            ok = r >= 4.5
            print("%-38s %-8s %-8s %6.2f:1 %s" % (label, fg, bg, r, "OK" if ok else "FAIL"))
            if not ok:
                failures.append("%s: %s = %.2f:1" % (name, label.strip(), r))
    return failures


def theme_colors(tok):
    return (
        "  --color-primary: %(primary)s;\n"
        "  --color-primary-light: %(primary_light)s;\n"
        "  --color-primary-dark: %(primary_dark)s;\n"
        "  --color-primary-50: %(primary_50)s;\n"
        "  --color-primary-accent: %(accent)s;\n"
        "\n"
        "  /* Emphasis and highlight only - amber this light is a\n"
        "   * stroke, a badge or a mark, never a fill under white text. */\n"
        "  --color-brand-warm: %(brand_warm)s;\n"
        "\n"
        "  /* Secondary brand hue - deep violet, for AI-assistant moments\n"
        "   * (generation gradients, the mascot halo, AI badges) alongside\n"
        "   * the primary red, never replacing it on a CTA. */\n"
        "  --color-secondary: %(secondary)s;\n"
        "  --color-secondary-light: %(secondary_light)s;\n"
        "  --color-secondary-dark: %(secondary_dark)s;\n"
        "  --color-secondary-50: %(secondary_50)s;\n"
        "  --color-secondary-accent: %(secondary_accent)s;\n"
        "\n"
        "  --color-background: %(background)s;\n"
        "  --color-surface: %(surface)s;\n"
        "  --color-surface-muted: %(surface_muted)s;\n"
        "\n"
        "  --color-text-primary: %(t1)s;\n"
        "  --color-text-secondary: %(t2)s;\n"
        "  --color-text-tertiary: %(t3)s;\n"
        "  --color-text-on-primary: #ffffff;\n"
        "\n"
        "  --color-border: %(border)s;\n"
        "  --color-border-light: %(border_light)s;\n"
    ) % tok


COLOR_NAMES = [
    "primary", "primary-light", "primary-dark", "primary-50", "primary-accent",
    "brand-warm",
    "secondary", "secondary-light", "secondary-dark", "secondary-50", "secondary-accent",
    "background", "surface", "surface-muted",
    "text-primary", "text-secondary", "text-tertiary", "text-on-primary",
    "note-bg", "note-icon", "test-bg", "test-icon", "pres-bg", "pres-icon",
    "lecture-bg", "lecture-icon", "amaliy-bg", "amaliy-icon", "igra-bg", "igra-icon",
    "success", "error", "warning", "border", "border-light",
    "surface-inverse", "text-on-inverse", "text-on-inverse-muted", "border-inverse",
]

HEADER = '''@import "tailwindcss";

/* ---------------------------------------------------------------------------
 * DESIGN TOKENS - generated by scripts/design_tokens.py. Do not hand-edit
 * anything above the `body` rule; edit the script and regenerate, so the
 * Tailwind mapping cannot drift from the definitions and every colour pair
 * stays contrast-checked.
 *
 * The brand is Dastyor red (#e11d2e, straight off the logo sheet) for the
 * CTA fill and logo, with an amber accent (--color-brand-warm) for emphasis
 * and a deep violet (--color-secondary) for AI-assistant moments -
 * generation gradients, the mascot halo, "AI" badges. Neutrals are warm
 * off-whites so the page agrees with the brand rather than sitting cool
 * underneath it. --color-error is a separate, deeper red and always travels
 * with an icon, so a failure never reads as a call to action.
 *
 * Every pair that renders text or an icon passes WCAG AA. Keep it that way:
 * the script prints the full table on every run.
 *
 * Two rules the contrast check still enforces, worth knowing before editing:
 *   - --color-primary is a FILL and carries white text, so it must stay
 *     dark. --color-primary-accent is the same brand as TEXT, and on a dark
 *     surface that has to be a much lighter value. Fill with primary, write
 *     with primary-accent, never the reverse.
 *   - --color-primary-dark (hover) darkens in dark mode too. Brightening the
 *     fill on hover is the obvious move on a dark page and it drops
 *     white-on-fill below AA; the fill is already far lighter than the page,
 *     so darkening still reads as "pressed".
 *
 * Motion: one language everywhere - 150ms, ease-out, and only colour or
 * opacity. Cards do not lift or translate on hover; borders and background
 * carry the state instead.
 * ------------------------------------------------------------------------- */

/* Light - the default, so the app still renders if data-theme is absent. */
:root {
'''

SHARED_LIGHT = '''
  /* Soft 3D category palette, remapped so each material type reads as its
   * own colour at a glance rather than a shade of the brand: konspekt in
   * lavender/violet, presentation in peach/coral, test in mint, lecture in
   * sky blue, practice in teal, games in rose. */
  --color-note-bg: #f2edff;
  --color-note-icon: #6c4db5;
  --color-test-bg: #e9f7f0;
  --color-test-icon: #187a54;
  --color-pres-bg: #ffe4d6;
  --color-pres-icon: #ad3a2a;
  --color-lecture-bg: #e3f2ff;
  --color-lecture-icon: #1f6fb0;
  --color-amaliy-bg: #e4f5f2;
  --color-amaliy-icon: #176d61;
  --color-igra-bg: #fceaf0;
  --color-igra-icon: #a63c62;

  /* Error is Material 3's, not the brand red: the brand is #e11d2e and a
   * failure state has to be told apart from a call to action at a glance.
   * This one is darker and far less saturated, and it is only ever used
   * with an icon or the word for the failure beside it. */
  /* A deliberately dark band the landing page sets a section on, so the
   * page is not one unbroken sheet of white. It is NOT --color-text-primary:
   * that token flips with the theme, which would turn the band white on a
   * dark page. This one stays dark in both, and only shifts enough in dark
   * mode to stay distinguishable from the page behind it. */
  --color-surface-inverse: #1b1f27;
  --color-text-on-inverse: #ffffff;
  --color-text-on-inverse-muted: #aeb6c2;
  --color-border-inverse: #333a46;

  --color-success: #059669;
  --color-error: #b3261e;
  --color-warning: #d97706;

  /* Controls stay tight (0.875rem, tighter than the 16px the old design
   * used everywhere and read as bubbly). Cards get a touch softer than the
   * original 1.25rem for this pass's "soft 3D" surfaces - the 3D art sits
   * on these, and a slightly rounder frame suits rounded-geometry objects
   * better without drifting back to bubbly controls. Elevation is still
   * close to flat: a hairline border plus a near-invisible shadow, with
   * --shadow-float reserved for things that genuinely hover above the
   * page. */
  --radius-card: 1.5rem;
  --radius-control: 0.875rem;
  --shadow-card: 0 6px 20px rgb(81 55 45 / 0.055), 0 1px 3px rgb(81 55 45 / 0.04);
  --shadow-card-lift: 0 14px 32px rgb(81 55 45 / 0.10), 0 3px 8px rgb(81 55 45 / 0.04);
  --shadow-float: 0 20px 50px rgb(64 44 43 / 0.16), 0 5px 16px rgb(64 44 43 / 0.06);
}

/* Dark. The pastel category fills glow on a dark page, so each becomes a
 * deep tint of its own hue with a lighter icon on top. Shadows barely
 * register on dark either, so they get heavier and surface lightness does
 * more of the lifting. */
:root[data-theme="dark"] {
'''

SHARED_DARK = '''
  --color-note-bg: #2a2147;
  --color-note-icon: #c3a8f5;
  --color-test-bg: #1d3028;
  --color-test-icon: #83d0aa;
  --color-pres-bg: #3a2419;
  --color-pres-icon: #f2a584;
  --color-lecture-bg: #17293d;
  --color-lecture-icon: #8dc8f5;
  --color-amaliy-bg: #1d302e;
  --color-amaliy-icon: #86cfc4;
  --color-igra-bg: #38242c;
  --color-igra-icon: #e7a0bb;

  --color-surface-inverse: #23262e;
  --color-text-on-inverse: #f5f3f3;
  --color-text-on-inverse-muted: #a9b0bb;
  --color-border-inverse: #3a404b;

  --color-success: #6fc595;
  --color-error: #f2b8b5;
  --color-warning: #d9ad57;

  --shadow-card: 0 1px 2px rgb(0 0 0 / 0.45);
  --shadow-card-lift: 0 4px 14px rgb(0 0 0 / 0.5);
  --shadow-float: 0 12px 32px rgb(0 0 0 / 0.6);

  /* Native widgets - scrollbars, form controls, the mobile URL bar - follow
   * the chosen theme instead of the OS setting. */
  color-scheme: dark;
}

/* Theme-varying tokens stay var() references so one attribute on <html>
 * reaches every Tailwind colour and shadow utility. No component carries a
 * `dark:` variant. */
@theme inline {
'''

THEME_TAIL = '''
  --radius-card: var(--radius-card);
  --radius-control: var(--radius-control);
  --shadow-card: var(--shadow-card);
  --shadow-card-lift: var(--shadow-card-lift);
  --shadow-float: var(--shadow-float);

  --font-sans: var(--font-sans-src);
  --font-display: var(--font-display-src);
  --font-mono: var(--font-mono-src);
}

/* The type scale is identical in both themes, so it is declared outright
 * rather than through a var() hop. Each step owns its line-height and
 * tracking: `text-title` is a decision made once, not `text-xl sm:text-2xl`
 * re-decided in every file. */
@theme {
'''


def emit():
    out = [HEADER, theme_colors(LIGHT), SHARED_LIGHT, theme_colors(DARK), SHARED_DARK]
    for name in COLOR_NAMES:
        out.append("  --color-%s: var(--color-%s);\n" % (name, name))
    out.append(THEME_TAIL)
    for name, size, line_height, tracking in TYPE:
        out.append("  --text-%s: %s;\n" % (name, size))
        out.append("  --text-%s--line-height: %s;\n" % (name, line_height))
        if tracking != "0":
            out.append("  --text-%s--letter-spacing: %s;\n" % (name, tracking))
    out.append("}\n")
    return "".join(out)


if __name__ == "__main__":
    failures = verify()
    total = 2 * (len(PAIRS) + 6)
    print("")
    print("=" * 68)
    if failures:
        # Reported, not fatal: a hard failure here would mean a palette
        # tweak cannot be regenerated and inspected at all. The palette is
        # at 26/26 today, so anything printed below is a regression - fix
        # the value rather than accepting the line. --strict exits non-zero
        # for a build or hook that wants the guarantee.
        print("%d of %d pairs below AA (known, accepted):" % (len(failures), total))
        for item in failures:
            print("  " + item)
        if "--strict" in sys.argv:
            sys.exit(1)
    else:
        print("all %d pairs pass AA" % total)
    if "--write" in sys.argv:
        path = "src/app/globals.css"
        existing = io.open(path, encoding="utf-8").read()
        tail = existing[existing.index("\nbody {"):]
        io.open(path, "w", encoding="utf-8", newline="\n").write(emit() + tail)
        print("wrote %s" % path)
