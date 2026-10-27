# Colour system

`src/app/globals.css` is generated from its first line through the end of
the `@theme` blocks. Do not hand-edit that region — edit
`design_tokens.py` and regenerate:

```bash
python scripts/design_tokens.py            # verify only: prints every checked pair
python scripts/design_tokens.py --write    # verify, then rewrite globals.css
python scripts/design_tokens.py --strict   # exit non-zero if any pair misses AA
```

`design_tokens.py` holds the brand and neutral tokens for both themes and
checks every pair that renders text or an icon against WCAG AA (4.5:1). All
26 pass; `--write` still emits when one does not, so a regression is visible
rather than unregenerable, and `--strict` is there for anything that wants
the hard guarantee.

The brand is Dastyor red (`--color-primary`, #e11d2e, taken from the logo
sheet) with an amber secondary (`--color-brand-warm`, emphasis only — never
a fill under white text). `--color-error` is a separate, deeper red so a
failure never reads as a call to action; see the header comment in
`design_tokens.py` for why that collision is accepted rather than avoided.

Run it from `frontend/`. Category colours, status colours and the
elevation/radius scale are the same in every palette and live in this
script's `SHARED_LIGHT` / `SHARED_DARK` headers, not in the token dicts.

## Logo and brand assets

Every logo file in the repo — web, Flutter, favicon, launcher icons — is cut
out of the official brand sheet by `scripts/brand/`, so there is one source
of truth and no hand-retouched copy to drift from it:

```bash
node scripts/brand/index.js scripts/brand/brand-sheet.png
```

It writes `public/brand/*` and `src/app/{favicon.ico,icon.png,apple-icon.png}`,
and — reaching outside `frontend/` — the Flutter app's `assets/images/*`,
`assets/icon/*` and `web/icons/*`. `assets/icon/` holds only the sources for
the native launcher icons, so after regenerating them run:

```bash
cd .. && dart run flutter_launcher_icons
```

The sheet is a flat render with no alpha, so transparency has to be
reconstructed — and the mark and the wordmark need opposite treatments:

- **The mark** (`extract.js`) is matted by flooding inward from the border.
  Deleting every white pixel would also delete the white ribbon counter
  inside the D; flooding clears only background connected to the outside,
  so an enclosed counter survives.
- **The wordmark** (`matte.js`) is matted from luminance instead, because a
  flood fill can never reach inside the counter of a *D*, *a* or *o* and
  would leave every one of them opaque. Flat ink on a flat plate makes the
  true alpha recoverable, antialiasing included.
- **The lockup** is composed from the two parts at their measured sheet
  coordinates — in markup on the web, as one image for Flutter — because
  the tagline sits too close under the word for a single rectangle to catch
  the lockup alone.

`ico.js` packs the 16/32/48 favicon entries as PNG rather than BMP.

Sizes come from what the UI actually paints, doubled for 2x displays, and
the display assets are WebP: the mark is a gradient under an alpha channel,
close to PNG's worst case — 556 KB as a 1024px PNG against 22 KB as a 512px
WebP.

## Hero images

`public/samples/hero/*.webp` are generated from the full-size sample PNGs,
resized to the width they actually paint at in `components/HeroDocuments.tsx`:

```bash
node -e "
const sharp = require('sharp');
[['public/samples/konspekt/2.png','public/samples/hero/konspekt.webp',640],
 ['public/samples/test/1.png','public/samples/hero/test.webp',480],
 ['public/samples/prezentatsiya/1.png','public/samples/hero/slide.webp',640],
].forEach(([src,out,w]) => sharp(src).resize({width:w}).webp({quality:82}).toFile(out));
"
```

301 KB of PNG becomes 72 KB of WebP. Re-run it if the chosen sample pages
change; the originals stay where they are for the samples gallery, which
shows them full size.
