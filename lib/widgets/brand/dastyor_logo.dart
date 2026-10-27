import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// The Dastyor logo, as drawn on the official brand sheet.
///
/// Before this, every screen reached for `assets/images/logo_mark.svg`
/// directly and several of them tinted it solid white with a
/// `ColorFilter`, which worked only because the old placeholder mark was a
/// flat single-colour glyph. The real mark is a gradient ribbon with a
/// white counter — flattening it to one colour destroys it — so the
/// asset is wrapped here instead, and screens that need the logo on a dark
/// or coloured surface ask for [plate] rather than inventing a treatment.
///
/// Sizing is by height only. The mark is slightly taller than it is wide
/// (154x169 on the sheet), so a square `SizedBox` letterboxes it and any
/// `BoxFit.fill` squashes it.
class DastyorMark extends StatelessWidget {
  const DastyorMark({
    super.key,
    this.height = 32,
    this.plate = false,
  });

  /// Height of the mark in logical pixels; width follows the aspect ratio.
  final double height;

  /// Draw the white rounded plate from the brand sheet's "app ikonka (oq
  /// fon)" behind the mark. That is the sanctioned way to put the logo on
  /// a dark or brand-red surface; it is never recoloured.
  final bool plate;

  /// Mark aspect ratio (w/h), measured from the brand sheet.
  static const double ratio = 154 / 169;

  @override
  Widget build(BuildContext context) {
    final mark = Image.asset(
      'assets/images/logo_mark.webp',
      height: height,
      width: height * ratio,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.medium,
    );
    if (!plate) return mark;

    final box = height * 1.52;
    return Container(
      width: box,
      height: box,
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(box * 0.26),
      ),
      alignment: Alignment.center,
      child: mark,
    );
  }
}

/// Mark plus the "Dastyor" wordmark, at the spacing the logo was drawn
/// with. Use [reversed] on dark or brand-red surfaces — the wordmark is
/// dark ink and disappears otherwise.
class DastyorLockup extends StatelessWidget {
  const DastyorLockup({
    super.key,
    this.height = 32,
    this.reversed = false,
  });

  /// Height of the MARK; the word and the gap are derived from it, so this
  /// is taller than the image it produces is tall by the word alone.
  final double height;
  final bool reversed;

  /// Lockup aspect ratio (w/h) of the composed artwork, from the sheet:
  /// the mark is 154x169 and the word ends at x=657 of a 588-wide box.
  static const double ratio = 588 / 169;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      reversed
          ? 'assets/images/logo_lockup_white.webp'
          : 'assets/images/logo_lockup.webp',
      height: height,
      width: height * ratio,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.medium,
    );
  }
}
