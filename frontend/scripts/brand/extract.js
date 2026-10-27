const sharp = require('sharp');

/**
 * Lift a logo off the brand sheet.
 *
 * The sheet is a flat JPEG-ish render, so there is no alpha to recover --
 * it has to be reconstructed. Doing that by "delete every white pixel"
 * would also delete the white ribbon counter inside the D, so instead the
 * background is found by flooding inward from the border: only background
 * that is *connected to the outside* is cleared, and an enclosed counter
 * survives. Everything runs at `scale`x so the matte edge is computed with
 * sub-pixel headroom, then the result is downsampled to its final size.
 */
async function lift({ src, region, scale = 6, bgIsDark = false, erode = 1, feather = 2 }) {
  const { data, info } = await sharp(src)
    .extract(region)
    .resize({ width: region.width * scale, kernel: 'lanczos3' })
    .removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const W = info.width, H = info.height, ch = info.channels, N = W * H;

  const isBg = new Uint8Array(N);
  for (let p = 0; p < N; p++) {
    const i = p * ch, r = data[i], g = data[i + 1], b = data[i + 2];
    const sat = Math.max(r, g, b) - Math.min(r, g, b);
    const lum = 0.299 * r + 0.587 * g + 0.114 * b;
    isBg[p] = sat < 16 && (bgIsDark ? lum < 48 : lum > 230) ? 1 : 0;
  }

  const ext = new Uint8Array(N);
  const stack = new Int32Array(N);
  let sp = 0;
  for (let x = 0; x < W; x++) { stack[sp++] = x; stack[sp++] = (H - 1) * W + x; }
  for (let y = 0; y < H; y++) { stack[sp++] = y * W; stack[sp++] = y * W + W - 1; }
  while (sp > 0) {
    const p = stack[--sp];
    if (ext[p] || !isBg[p]) continue;
    ext[p] = 1;
    const x = p % W, y = (p / W) | 0;
    if (x > 0) stack[sp++] = p - 1;
    if (x < W - 1) stack[sp++] = p + 1;
    if (y > 0) stack[sp++] = p - W;
    if (y < H - 1) stack[sp++] = p + W;
  }

  // Grow the cleared region inward by `erode` px: the outermost ring of the
  // shape is a blend of ink and background, and keeping it leaves a pale
  // halo once the logo is placed on a dark surface.
  let cleared = ext;
  for (let k = 0; k < erode; k++) {
    const next = new Uint8Array(cleared);
    for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
      const p = y * W + x;
      if (!cleared[p] && (cleared[p - 1] || cleared[p + 1] || cleared[p - W] || cleared[p + W])) next[p] = 1;
    }
    cleared = next;
  }

  const alpha = new Float32Array(N);
  for (let p = 0; p < N; p++) alpha[p] = cleared[p] ? 0 : 255;
  boxBlur(alpha, W, H, feather);

  let minx = W, miny = H, maxx = -1, maxy = -1;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (alpha[y * W + x] > 2) {
      if (x < minx) minx = x; if (x > maxx) maxx = x;
      if (y < miny) miny = y; if (y > maxy) maxy = y;
    }
  }
  const bw = maxx - minx + 1, bh = maxy - miny + 1;
  const rgba = Buffer.alloc(bw * bh * 4);
  for (let y = 0; y < bh; y++) for (let x = 0; x < bw; x++) {
    const p = (y + miny) * W + (x + minx), o = (y * bw + x) * 4, i = p * ch;
    rgba[o] = data[i]; rgba[o + 1] = data[i + 1]; rgba[o + 2] = data[i + 2];
    rgba[o + 3] = Math.max(0, Math.min(255, Math.round(alpha[p])));
  }
  return { buf: rgba, width: bw, height: bh, scale, offset: { x: minx / scale, y: miny / scale } };
}

function boxBlur(a, W, H, r) {
  if (r < 1) return;
  const tmp = new Float32Array(a.length), d = 2 * r + 1;
  for (let y = 0; y < H; y++) {
    let sum = 0;
    for (let x = -r; x <= r; x++) sum += a[y * W + Math.min(W - 1, Math.max(0, x))];
    for (let x = 0; x < W; x++) {
      tmp[y * W + x] = sum / d;
      sum -= a[y * W + Math.min(W - 1, Math.max(0, x - r))];
      sum += a[y * W + Math.min(W - 1, Math.max(0, x + r + 1))];
    }
  }
  for (let x = 0; x < W; x++) {
    let sum = 0;
    for (let y = -r; y <= r; y++) sum += tmp[Math.min(H - 1, Math.max(0, y)) * W + x];
    for (let y = 0; y < H; y++) {
      a[y * W + x] = sum / d;
      sum -= tmp[Math.min(H - 1, Math.max(0, y - r)) * W + x];
      sum += tmp[Math.min(H - 1, Math.max(0, y + r + 1)) * W + x];
    }
  }
}

const img = ({ buf, width, height }) => sharp(buf, { raw: { width, height, channels: 4 } });

module.exports = { lift, img, sharp };
