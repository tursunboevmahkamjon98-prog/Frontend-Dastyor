const { sharp } = require('./extract.js');

/**
 * Matte flat two-tone artwork (the "Dastyor" wordmark) out of its plate.
 *
 * The flood fill used for the mark cannot be used here: a letter counter --
 * the hole in a D, an a, an o -- is background that is *not* connected to
 * the outside, so a fill would leave every counter opaque. Text is flat
 * ink on a flat plate, though, which makes the real matte recoverable:
 * alpha is just how far the pixel travelled from the plate towards the ink,
 * which also reconstructs the antialiasing instead of stair-stepping it.
 */
async function matteText({ src, region, scale = 8, bgIsDark = false, gamma = 1.0 }) {
  const { data, info } = await sharp(src)
    .extract(region)
    .resize({ width: region.width * scale, kernel: 'lanczos3' })
    .removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const W = info.width, H = info.height, ch = info.channels, N = W * H;

  const lum = new Float32Array(N);
  for (let p = 0; p < N; p++) {
    const i = p * ch;
    lum[p] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
  }
  // The plate level is the modal luminance of the padded region, not a
  // percentile: a percentile drifts with how much ink the crop happens to
  // contain, and any drift shows up as a faint rectangle of non-zero alpha
  // around the word.
  const hist = new Uint32Array(256);
  for (let p = 0; p < N; p++) hist[Math.max(0, Math.min(255, Math.round(lum[p])))]++;
  let bgLum = 0, best = -1;
  for (let v = 0; v < 256; v++) {
    const isPlateSide = bgIsDark ? v < 128 : v > 128;
    if (isPlateSide && hist[v] > best) { best = hist[v]; bgLum = v; }
  }
  const sorted = Float32Array.from(lum).sort();
  const pct = (q) => sorted[Math.min(N - 1, Math.max(0, Math.round(q * (N - 1))))];
  const inkLum = bgIsDark ? pct(0.995) : pct(0.005);

  // Average the solid core of the ink so partial-coverage pixels, which are
  // blends with the plate, do not drag the colour towards the plate.
  let rs = 0, gs = 0, bs = 0, n = 0;
  const core = bgIsDark ? inkLum - 12 : inkLum + 12;
  for (let p = 0; p < N; p++) {
    if (bgIsDark ? lum[p] > core : lum[p] < core) {
      const i = p * ch; rs += data[i]; gs += data[i + 1]; bs += data[i + 2]; n++;
    }
  }
  const ink = n ? [Math.round(rs / n), Math.round(gs / n), Math.round(bs / n)] : [0, 0, 0];

  const span = inkLum - bgLum;
  let minx = W, miny = H, maxx = -1, maxy = -1;
  const alpha = new Float32Array(N);
  for (let p = 0; p < N; p++) {
    let a = (lum[p] - bgLum) / span;
    // Clip the toe: plate pixels sit a hair off the modal value and would
    // otherwise carry a few percent of alpha across the whole rectangle.
    a = Math.max(0, Math.min(1, (a - 0.07) / 0.93));
    if (gamma !== 1) a = Math.pow(a, gamma);
    alpha[p] = a * 255;
    if (a > 0.02) {
      const x = p % W, y = (p / W) | 0;
      if (x < minx) minx = x; if (x > maxx) maxx = x;
      if (y < miny) miny = y; if (y > maxy) maxy = y;
    }
  }

  const bw = maxx - minx + 1, bh = maxy - miny + 1;
  const rgba = Buffer.alloc(bw * bh * 4);
  for (let y = 0; y < bh; y++) for (let x = 0; x < bw; x++) {
    const p = (y + miny) * W + (x + minx), o = (y * bw + x) * 4;
    rgba[o] = ink[0]; rgba[o + 1] = ink[1]; rgba[o + 2] = ink[2];
    rgba[o + 3] = Math.round(alpha[p]);
  }
  return { buf: rgba, width: bw, height: bh, ink, offset: { x: minx / scale, y: miny / scale }, scale };
}

module.exports = { matteText };
