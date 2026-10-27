const { lift, img, sharp } = require('./extract.js');
const { matteText } = require('./matte.js');
const fs = require('fs');
const path = require('path');
const { buildIco } = require('./ico.js');

const SHEET = process.argv[2];
if (!SHEET) {
  console.error('usage: node scripts/brand/index.js <path-to-brand-sheet.png>');
  process.exit(1);
}
const ROOT = path.resolve(__dirname, '..', '..', '..');
const CLEAR = { r: 0, g: 0, b: 0, alpha: 0 };
const WHITE = { r: 255, g: 255, b: 255, alpha: 1 };

/* Rectangles measured off the 1254x1254 brand sheet. The hero lockup at the
 * top-left is the largest clean rendering of the logo anywhere on the sheet,
 * so every colour asset comes from it; the reversed lockup can only come
 * from the dark footer tile. The mark and the wordmark are lifted
 * separately -- they need different matting, and the sheet sets the tagline
 * close enough under the wordmark that one rectangle cannot hold the lockup
 * without catching it. Their original sheet coordinates are kept so the
 * recomposed lockup has exactly the spacing the designer drew. */
const PARTS = {
  color: {
    mark: { left: 69, top: 137, width: 154, height: 169 },
    word: { left: 262, top: 177, width: 395, height: 100 },
    dark: false,
  },
  white: {
    mark: { left: 82, top: 1000, width: 68, height: 74 },
    word: { left: 168, top: 1017, width: 162, height: 40 },
    dark: true,
  },
};

const out = (...p) => {
  const f = path.join(ROOT, ...p);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  return f;
};

/** Rebuild a lockup at `scale`x from the parts, at their sheet geometry. */
async function lockup(spec) {
  const S = 8;
  const mr = pad(spec.mark, 3), wr = pad(spec.word, 10);
  const mark = await lift({ src: SHEET, region: mr, scale: S, bgIsDark: spec.dark, erode: 5, feather: 4 });
  const word = await matteText({ src: SHEET, region: pad(spec.word, 10), scale: S, bgIsDark: spec.dark });

  // Where each part actually landed on the sheet, feathering included.
  const box = (p, r) => ({ x: r.left + p.offset.x, y: r.top + p.offset.y, w: p.width / S, h: p.height / S });
  const bm = box(mark, mr), bw_ = box(word, wr);
  const left = Math.min(bm.x, bw_.x), top = Math.min(bm.y, bw_.y);
  const right = Math.max(bm.x + bm.w, bw_.x + bw_.w), bottom = Math.max(bm.y + bm.h, bw_.y + bw_.h);
  const W = Math.ceil((right - left) * S), H = Math.ceil((bottom - top) * S);

  const place = (p, b) => ({
    input: p.buf,
    raw: { width: p.width, height: p.height, channels: 4 },
    left: Math.round((b.x - left) * S),
    top: Math.round((b.y - top) * S),
  });

  return sharp({ create: { width: W, height: H, channels: 4, background: CLEAR } })
    .composite([place(mark, bm), place(word, bw_)])
    .png().toBuffer();
}

const pad = (r, n) => ({ left: r.left - n, top: r.top - n, width: r.width + 2 * n, height: r.height + 2 * n });

/** Centre a transparent logo on a square canvas, leaving `pad` margin. */
async function square(src, size, padFrac, bg) {
  const inner = Math.round(size * (1 - 2 * padFrac));
  const fit = await sharp(src).resize({ width: inner, height: inner, fit: 'contain', background: CLEAR, kernel: 'lanczos3' }).png().toBuffer();
  const m = await sharp(fit).metadata();
  return sharp({ create: { width: size, height: size, channels: 4, background: bg || CLEAR } })
    .composite([{ input: fit, left: Math.round((size - m.width) / 2), top: Math.round((size - m.height) / 2) }])
    .png({ compressionLevel: 9 });
}

(async () => {
  const mark = await lift({ src: SHEET, region: pad(PARTS.color.mark, 3), scale: 6, erode: 4, feather: 3 });
  const tmp = out('frontend', 'public', 'brand', '.mark-src.png');
  fs.writeFileSync(tmp, await img(mark).png().toBuffer());
  console.log('mark', mark.width + 'x' + mark.height);

  // Standalone wordmarks too: the lockup is composed in the markup from
  // mark + wordmark, so switching to the reversed logo in dark mode costs
  // one 12 KB word rather than a second copy of the whole lockup.
  const wordC = await matteText({ src: SHEET, region: pad(PARTS.color.word, 10), scale: 8, bgIsDark: false });
  const wordW = await matteText({ src: SHEET, region: pad(PARTS.white.word, 10), scale: 8, bgIsDark: true });
  await img(wordC).resize({ width: 440, kernel: 'lanczos3' }).webp({ quality: 88 }).toFile(out('frontend', 'public', 'brand', 'wordmark.webp'));
  await img(wordW).resize({ width: 440, kernel: 'lanczos3' }).webp({ quality: 88 }).toFile(out('frontend', 'public', 'brand', 'wordmark-white.webp'));
  await img(wordC).resize({ width: 440, kernel: 'lanczos3' }).webp({ quality: 88 }).toFile(out('assets', 'images', 'logo_wordmark.webp'));
  await img(wordW).resize({ width: 440, kernel: 'lanczos3' }).webp({ quality: 88 }).toFile(out('assets', 'images', 'logo_wordmark_white.webp'));
  console.log('lockup geometry (sheet units): mark', JSON.stringify(PARTS.color.mark), 'word', JSON.stringify(PARTS.color.word));

  const lk = await lockup(PARTS.color);
  const lkW = await lockup(PARTS.white);

  const png = (s) => s.png({ compressionLevel: 9 });
  const w = (b, width) => sharp(b).resize({ width, kernel: 'lanczos3' }).png({ compressionLevel: 9 });

  // --- Web brand assets ----------------------------------------------
  // WebP, not PNG: the mark is a smooth gradient under an alpha channel,
  // which is close to the worst case for PNG's filters -- the same artwork
  // is 556 KB as a 1024px PNG and 23 KB as a 512px WebP. Sizes are set from
  // what the pages actually paint (nav mark ~32px, auth lockup ~200px),
  // doubled for 2x displays, not from the source resolution.
  await sharp(await img(mark).png().toBuffer()).resize({ width: 512, kernel: 'lanczos3' }).webp({ quality: 90 }).toFile(out('frontend', 'public', 'brand', 'mark.webp'));
  await sharp(lk).resize({ width: 800, kernel: 'lanczos3' }).webp({ quality: 90 }).toFile(out('frontend', 'public', 'brand', 'lockup.webp'));
  await sharp(lkW).resize({ width: 800, kernel: 'lanczos3' }).webp({ quality: 90 }).toFile(out('frontend', 'public', 'brand', 'lockup-white.webp'));

  // --- Web favicon + PWA (Next app-router file conventions) -------------
  fs.writeFileSync(out('frontend', 'src', 'app', 'favicon.ico'), await buildIco(tmp, [16, 32, 48]));
  await (await square(tmp, 192, 0.06)).toFile(out('frontend', 'src', 'app', 'icon.png'));
  await (await square(tmp, 180, 0.14, WHITE)).toFile(out('frontend', 'src', 'app', 'apple-icon.png'));
  await (await square(tmp, 192, 0.08, WHITE)).toFile(out('frontend', 'public', 'brand', 'icon-192.png'));
  await (await square(tmp, 512, 0.08, WHITE)).toFile(out('frontend', 'public', 'brand', 'icon-512.png'));
  await (await square(tmp, 512, 0.22, WHITE)).toFile(out('frontend', 'public', 'brand', 'icon-maskable-512.png'));

  // --- Flutter ----------------------------------------------------------
  // WebP for the same reason as the web, and Flutter decodes it natively:
  // 134 KB of PNG becomes 11 KB, which is APK size on phones that are the
  // whole reason this app is sideloaded. Sizes are the largest the app
  // paints (a 128dp splash mark on a 3x screen), not the source resolution.
  await sharp(await img(mark).png().toBuffer()).resize({ width: 384, kernel: 'lanczos3' }).webp({ quality: 90 }).toFile(out('assets', 'images', 'logo_mark.webp'));
  await sharp(lk).resize({ width: 800, kernel: 'lanczos3' }).webp({ quality: 90 }).toFile(out('assets', 'images', 'logo_lockup.webp'));
  await sharp(lkW).resize({ width: 800, kernel: 'lanczos3' }).webp({ quality: 90 }).toFile(out('assets', 'images', 'logo_lockup_white.webp'));
  // flutter_launcher_icons sources. assets/icon/ is not in pubspec's asset
  // list, so these are build-time inputs only and never ship in the APK.
  await (await square(tmp, 1024, 0.16, WHITE)).toFile(out('assets', 'icon', 'app_icon.png'));
  // The adaptive-icon XML already insets this drawable by 16%, and
  // Android's safe zone is the centre 66%, so the artwork fills its own
  // frame here instead of being padded twice and ending up tiny.
  await (await square(tmp, 1024, 0.08)).toFile(out('assets', 'icon', 'app_icon_fg.png'));
  await (await square(tmp, 1024, 0.16)).toFile(out('assets', 'icon', 'app_icon_transparent.png'));

  // --- Flutter web shell ------------------------------------------------
  for (const [size, padf, name] of [[192, 0.08, 'Icon-192.png'], [512, 0.08, 'Icon-512.png'], [192, 0.22, 'Icon-maskable-192.png'], [512, 0.22, 'Icon-maskable-512.png']]) {
    await (await square(tmp, size, padf, WHITE)).toFile(out('web', 'icons', name));
  }
  fs.writeFileSync(out('web', 'favicon.png'), await (await square(tmp, 64, 0.06)).toBuffer());

  fs.unlinkSync(tmp);
  console.log('assets written');
})();
