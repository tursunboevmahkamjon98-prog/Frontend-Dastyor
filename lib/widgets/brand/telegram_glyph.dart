import 'package:flutter/material.dart';

/// Telegram's paper-plane mark, drawn rather than imported.
///
/// Drawn because the alternatives are worse here:
///
///  * `Icons.send_rounded` (what [ContactChannels] uses) is a generic
///    send arrow. It is fine for a row labelled "Telegram", but the
///    top-up button is a primary action whose whole job is to be
///    recognised instantly, and the real mark is what people recognise.
///  * A PNG/SVG asset would mean a new file in `assets/`, a pubspec
///    entry, and either `flutter_svg` or a raster that blurs when the
///    button scales with the system text size.
///
/// A path costs nothing, scales perfectly and inherits its colour, so the
/// same glyph works white-on-red here and could work red-on-white
/// elsewhere without a second asset.
///
/// The shape is a single polygon: the long wing from the top-right tip
/// down to the left edge, with the tail notch that dips below and folds
/// back up. That notch is the detail that makes it read as Telegram's
/// plane and not as a generic triangle, so it is drawn explicitly rather
/// than smoothed away.
class TelegramGlyph extends StatelessWidget {
  const TelegramGlyph({super.key, this.size = 20, this.color});

  final double size;

  /// Defaults to the ambient [IconTheme] colour, so the glyph behaves
  /// like an [Icon] inside buttons and list rows.
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final resolved = color ?? IconTheme.of(context).color ?? Colors.white;
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _TelegramPlanePainter(resolved),
        // The mark is decorative: the button that contains it carries the
        // label and the semantics, so announcing "Telegram logo" here
        // would make a screen reader say the name twice.
        isComplex: false,
      ),
    );
  }
}

class _TelegramPlanePainter extends CustomPainter {
  const _TelegramPlanePainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    // Authored against a 24x24 box and scaled, so the proportions hold at
    // any size instead of being retuned per call site.
    final scale = size.width / 24.0;
    Offset p(double x, double y) => Offset(x * scale, y * scale);

    final plane = Path()
      ..moveTo(p(22.6, 2.9).dx, p(22.6, 2.9).dy) // top-right tip
      ..lineTo(p(1.4, 11.4).dx, p(1.4, 11.4).dy) // left edge
      ..lineTo(p(8.6, 14.3).dx, p(8.6, 14.3).dy) // underside of the wing
      ..lineTo(p(8.6, 21.3).dx, p(8.6, 21.3).dy) // tail dips below
      ..lineTo(p(12.1, 16.3).dx, p(12.1, 16.3).dy) // folds back up
      ..lineTo(p(18.4, 21.1).dx, p(18.4, 21.1).dy) // trailing edge
      ..close();

    // The fold: a wedge from the wing's underside up to the tip, left
    // partly transparent. On the real mark this is the shaded inner face
    // of the folded paper; without it the glyph flattens into a plain
    // arrowhead at small sizes.
    final fold = Path()
      ..moveTo(p(8.6, 14.3).dx, p(8.6, 14.3).dy)
      ..lineTo(p(22.6, 2.9).dx, p(22.6, 2.9).dy)
      ..lineTo(p(12.1, 16.3).dx, p(12.1, 16.3).dy)
      ..close();

    // saveLayer confines the dstOut below to this glyph. Without it the
    // blend would erase into whatever the parent already painted — the
    // button's red fill — and punch a real hole through it.
    //
    // Thinning the plane's own alpha, rather than painting a second
    // guessed colour, is what keeps the glyph correct on any background:
    // the fold reads as a shade of the surface behind it, so the same
    // widget works white-on-red and red-on-white.
    canvas.saveLayer(Offset.zero & size, Paint());
    canvas.drawPath(plane, Paint()..color = color);
    canvas.drawPath(
      fold,
      Paint()
        ..color = const Color(0xFF000000).withValues(alpha: 0.30)
        ..blendMode = BlendMode.dstOut,
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(_TelegramPlanePainter oldDelegate) =>
      oldDelegate.color != color;
}
