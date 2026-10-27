/**
 * Cut the six official mascot poses out of the mascot brand sheet.
 *
 *   node scripts/brand/mascot.js scripts/brand/mascot-sheet.png
 *
 * The sheet's "Maskot har xil holatlarda" strip is the character's own
 * reference set, and each pose already maps onto a state the app actually
 * has, which is why these names are the ones the animation state machine
 * uses (see src/components/mascot/states.ts).
 *
 * Matting is the same flood-from-the-border trick as the logo mark: the
 * robot's armour is white, so "delete the white pixels" would delete the
 * character. Flooding only clears background reachable from the edge, and
 * the art has a dark enough outline everywhere that nothing leaks in. The
 * drop shadow under each robot is grey, not near-white, so it is kept out
 * by the same luminance threshold rather than being baked into a sprite
 * that then smudges on a coloured surface.
 */
const path = require('path');
const fs = require('fs');
const { lift, img } = require('./extract.js');

const SHEET = process.argv[2];
if (!SHEET) {
  console.error('usage: node scripts/brand/mascot.js <path-to-mascot-sheet.png>');
  process.exit(1);
}
const ROOT = path.resolve(__dirname, '..', '..', '..');

/* Measured off the 1254x1254 sheet by column/row profiling: the strip's
 * six cells, trimmed to the art and stopping above each caption. */
const POSES = [
  ['greeting', { left: 38, top: 617, width: 154, height: 181 }],
  ['thinking', { left: 252, top: 613, width: 132, height: 183 }],
  ['working', { left: 455, top: 616, width: 141, height: 181 }],
  ['success', { left: 657, top: 614, width: 134, height: 186 }],
  ['celebrating', { left: 859, top: 617, width: 154, height: 180 }],
  ['knowledge', { left: 1066, top: 613, width: 140, height: 183 }],
];

const out = (...p) => {
  const f = path.join(ROOT, ...p);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  return f;
};

(async () => {
  for (const [name, region] of POSES) {
    const r = await lift({ src: SHEET, region, scale: 4, erode: 2, feather: 2 });
    // 512px tall is twice the largest the mascot is ever painted (a 240px
    // dashboard panel), which is all the source has to give anyway.
    const web = img(r).resize({ height: 512, kernel: 'lanczos3' }).webp({ quality: 88 });
    await web.toFile(out('frontend', 'public', 'mascot', name + '.webp'));
    await img(r).resize({ height: 512, kernel: 'lanczos3' }).webp({ quality: 88 })
      .toFile(out('assets', 'mascot', name + '.webp'));
    console.log(name.padEnd(12), r.width + 'x' + r.height, '->', 'public/mascot/' + name + '.webp');
  }
})();
