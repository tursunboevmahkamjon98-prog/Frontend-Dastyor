const { sharp } = require('./extract.js');

/**
 * Pack PNGs into an .ico. Every entry is stored PNG-compressed rather than
 * as a BMP/DIB, which every browser in use has supported since IE11 and
 * which keeps the 48px entry from costing more than the other two combined.
 */
async function buildIco(src, sizes) {
  const pngs = [];
  for (const s of sizes) {
    pngs.push(await sharp(src).resize({ width: s, height: s, fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 }, kernel: 'lanczos3' }).png({ compressionLevel: 9 }).toBuffer());
  }
  const dir = Buffer.alloc(6 + 16 * sizes.length);
  dir.writeUInt16LE(0, 0); dir.writeUInt16LE(1, 2); dir.writeUInt16LE(sizes.length, 4);
  let offset = dir.length;
  sizes.forEach((s, i) => {
    const e = 6 + 16 * i;
    dir.writeUInt8(s >= 256 ? 0 : s, e);
    dir.writeUInt8(s >= 256 ? 0 : s, e + 1);
    dir.writeUInt8(0, e + 2); dir.writeUInt8(0, e + 3);
    dir.writeUInt16LE(1, e + 4); dir.writeUInt16LE(32, e + 6);
    dir.writeUInt32LE(pngs[i].length, e + 8);
    dir.writeUInt32LE(offset, e + 12);
    offset += pngs[i].length;
  });
  return Buffer.concat([dir, ...pngs]);
}
module.exports = { buildIco };
