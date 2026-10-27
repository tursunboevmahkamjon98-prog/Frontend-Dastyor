/* The Dastyor logo, as drawn on the official brand sheet.
 *
 * This used to be an inline SVG path — a generic rounded-rect "document"
 * glyph that was never the real logo, just the placeholder the project
 * could draw in code. The real mark is a gradient ribbon D with a white
 * counter, which is not something to re-draw by hand in path data, so it
 * ships as artwork: see scripts/brand-assets.js for how the files are cut
 * out of the brand sheet.
 *
 * The lockup is composed here rather than served as one image, for two
 * reasons. The wordmark is dark ink and needs a reversed copy for dark
 * mode, and composing means only the 16 KB word is duplicated instead of
 * the whole logo. It also lets a collapsed sidebar drop the word and keep
 * the mark without a second asset.
 *
 * Composition is not eyeballed: MARK/WORD/GAP below are measured off the
 * sheet, so the spacing between mark and word is the one the logo was
 * drawn with at every size.
 *
 * Size is one prop, `height`, which is the height of the MARK and may be
 * any CSS length — including a clamp() — because everything else is
 * derived from it in calc(). There is no `w-8 h-8` to get wrong: the mark
 * is slightly taller than it is wide and a square box would letterbox it.
 */

/** Mark aspect ratio (w/h) and the word's size and offset relative to the
 *  mark's height, all measured from the brand sheet's primary lockup. */
const MARK_RATIO = 154 / 169;
const WORD_RATIO = 395 / 100;
const WORD_SCALE = 100 / 169;
const GAP_SCALE = (262 - (69 + 154)) / 169;

export function LogoMark({
  height = "2rem",
  className = "",
  alt = "",
}: {
  height?: string;
  className?: string;
  alt?: string;
}) {
  return (
    <img
      src="/brand/mark.webp"
      alt={alt}
      aria-hidden={alt ? undefined : true}
      draggable={false}
      width={154}
      height={169}
      className={`block shrink-0 select-none ${className}`}
      style={{ height, width: `calc(${height} * ${MARK_RATIO})` }}
    />
  );
}

export default function Logo({
  height = "2rem",
  className = "",
  showWord = true,
}: {
  /** Height of the mark; the word and the gap scale off it. */
  height?: string;
  className?: string;
  showWord?: boolean;
}) {
  if (!showWord) return <LogoMark height={height} className={className} alt="Dastyor" />;

  const word = {
    height: `calc(${height} * ${WORD_SCALE})`,
    width: `calc(${height} * ${WORD_SCALE} * ${WORD_RATIO})`,
  };

  return (
    <span
      className={`inline-flex items-center ${className}`}
      style={{ gap: `calc(${height} * ${GAP_SCALE})` }}
    >
      <LogoMark height={height} />
      {/* Both wordmarks are in the DOM and CSS picks one, so the logo is
       * right in the first paint. Reading the theme in JS would flash the
       * wrong one between hydration and the effect. */}
      <img
        src="/brand/wordmark.webp"
        alt="Dastyor"
        data-logo="light"
        draggable={false}
        width={395}
        height={100}
        className="block shrink-0 select-none"
        style={word}
      />
      <img
        src="/brand/wordmark-white.webp"
        alt=""
        aria-hidden
        data-logo="dark"
        draggable={false}
        width={395}
        height={100}
        className="block shrink-0 select-none"
        style={word}
      />
    </span>
  );
}
