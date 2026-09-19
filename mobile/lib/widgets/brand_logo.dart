import 'package:flutter/material.dart';

import '../theme/app_theme.dart';


class AppBackdrop extends StatelessWidget {
  const AppBackdrop({
    super.key,
    required this.child,
  });

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: AppGradients.backdrop,
          ),
        ),
        Positioned(
          top: -150,
          left: -120,
          child: IgnorePointer(
            child: Container(
              width: 320,
              height: 320,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppColors.primaryBlue.withOpacity(0.16),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
        ),
        Positioned(
          right: -150,
          bottom: -40,
          child: IgnorePointer(
            child: Container(
              width: 340,
              height: 340,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppColors.primaryPurple.withOpacity(0.12),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
        ),
        child,
      ],
    );
  }
}


class BrandMark extends StatelessWidget {
  const BrandMark({
    super.key,
    this.size = 36,
    this.showBackground = true,
  });

  final double size;
  final bool showBackground;

  @override
  Widget build(BuildContext context) {
    final mark = CustomPaint(
      size: Size.square(size),
      painter: const _BrandMarkPainter(),
    );

    if (!showBackground) {
      return SizedBox.square(
        dimension: size,
        child: mark,
      );
    }

    return Container(
      width: size,
      height: size,
      padding: EdgeInsets.all(size * 0.10),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF0D3764),
            Color(0xFF08152B),
            Color(0xFF080C1D),
          ],
        ),
        borderRadius: BorderRadius.circular(size * 0.25),
        border: Border.all(
          color: AppColors.primaryBlue.withOpacity(0.48),
          width: 0.9,
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.primaryBlue.withOpacity(0.20),
            blurRadius: size * 0.50,
            spreadRadius: -size * 0.22,
          ),
          BoxShadow(
            color: Colors.black.withOpacity(0.28),
            blurRadius: size * 0.30,
            offset: Offset(0, size * 0.10),
          ),
        ],
      ),
      child: mark,
    );
  }
}


class BrandLockup extends StatelessWidget {
  const BrandLockup({
    super.key,
    this.compact = false,
    this.subtitle,
  });

  final bool compact;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final markSize = compact ? 36.0 : 52.0;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        BrandMark(
          size: markSize,
          showBackground: false,
        ),
        SizedBox(width: compact ? 9 : 12),
        Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'MEME',
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: compact ? 18 : 25,
                height: 0.95,
                fontWeight: FontWeight.w900,
                letterSpacing: compact ? 0.5 : 0.9,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              subtitle ?? 'AI INVEST',
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: compact ? 8.0 : 10.0,
                height: 1,
                fontWeight: FontWeight.w600,
                letterSpacing: compact ? 2.8 : 3.6,
              ),
            ),
          ],
        ),
      ],
    );
  }
}


class BrandAppBarTitle extends StatelessWidget {
  const BrandAppBarTitle({
    super.key,
    required this.pageTitle,
  });

  final String pageTitle;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const BrandLockup(compact: true),
        const Spacer(),
        Container(
          constraints: const BoxConstraints(maxWidth: 104),
          padding: const EdgeInsets.symmetric(
            horizontal: 10,
            vertical: 6,
          ),
          decoration: BoxDecoration(
            color: AppColors.surfaceElevated.withOpacity(0.72),
            borderRadius: BorderRadius.circular(AppRadius.pill),
            border: Border.all(
              color: AppColors.borderSoft,
              width: 0.8,
            ),
          ),
          child: Text(
            pageTitle,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.1,
            ),
          ),
        ),
      ],
    );
  }
}


class BrandNavIcon extends StatelessWidget {
  const BrandNavIcon({
    super.key,
    required this.icon,
    this.selected = false,
  });

  final IconData icon;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final iconWidget = Icon(
      icon,
      size: 22,
      color: Colors.white,
    );

    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      width: 38,
      height: 38,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        gradient: selected
            ? const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF0A2746),
                  Color(0xFF071323),
                ],
              )
            : null,
        color: selected ? null : const Color(0xFF071321),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: selected
              ? AppColors.primaryBlue.withOpacity(0.72)
              : AppColors.borderSoft,
          width: selected ? 1.0 : 0.8,
        ),
        boxShadow: selected
            ? [
                BoxShadow(
                  color: AppColors.primaryBlue.withOpacity(0.18),
                  blurRadius: 14,
                  spreadRadius: -4,
                ),
              ]
            : null,
      ),
      child: selected
          ? ShaderMask(
              shaderCallback: (bounds) =>
                  AppGradients.primary.createShader(bounds),
              blendMode: BlendMode.srcIn,
              child: iconWidget,
            )
          : Icon(
              icon,
              size: 22,
              color: const Color(0xFF51BEEB),
            ),
    );
  }
}


class BrandHero extends StatelessWidget {
  const BrandHero({
    super.key,
    this.title = 'INVEST SMARTER TOGETHER',
    this.subtitle = '데이터가 만드는 더 나은 선택',
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(22, 22, 22, 20),
      decoration: BoxDecoration(
        gradient: AppGradients.hero,
        borderRadius: BorderRadius.circular(AppRadius.extraLarge),
        border: Border.all(
          color: AppColors.primaryBlue.withOpacity(0.30),
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.primaryBlue.withOpacity(0.11),
            blurRadius: 28,
            spreadRadius: -10,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const BrandLockup(),
          const SizedBox(height: 22),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: AppColors.textPrimary,
                ),
          ),
          const SizedBox(height: 9),
          Row(
            children: [
              Container(
                width: 38,
                height: 3,
                decoration: BoxDecoration(
                  gradient: AppGradients.primary,
                  borderRadius: BorderRadius.circular(99),
                ),
              ),
              const SizedBox(width: 10),
              Text(
                title,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                      letterSpacing: 2.0,
                      fontSize: 9,
                    ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}


class _BrandMarkPainter extends CustomPainter {
  const _BrandMarkPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;

    final shadowPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * 0.19
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..color = AppColors.primaryBlue.withOpacity(0.22)
      ..maskFilter = MaskFilter.blur(
        BlurStyle.normal,
        size.width * 0.055,
      );

    final left = Path()
      ..moveTo(size.width * 0.15, size.height * 0.73)
      ..cubicTo(
        size.width * 0.23,
        size.height * 0.57,
        size.width * 0.27,
        size.height * 0.39,
        size.width * 0.37,
        size.height * 0.37,
      )
      ..cubicTo(
        size.width * 0.44,
        size.height * 0.36,
        size.width * 0.49,
        size.height * 0.48,
        size.width * 0.56,
        size.height * 0.62,
      );

    final rise = Path()
      ..moveTo(size.width * 0.56, size.height * 0.62)
      ..cubicTo(
        size.width * 0.60,
        size.height * 0.70,
        size.width * 0.67,
        size.height * 0.67,
        size.width * 0.72,
        size.height * 0.58,
      )
      ..lineTo(size.width * 0.86, size.height * 0.31);

    canvas.drawPath(left, shadowPaint);
    canvas.drawPath(rise, shadowPaint);

    final leftPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * 0.18
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..shader = const LinearGradient(
        begin: Alignment.bottomLeft,
        end: Alignment.topRight,
        colors: [
          Color(0xFF087EFF),
          Color(0xFF12CFFC),
          Color(0xFF355DFF),
        ],
        stops: [0.0, 0.58, 1.0],
      ).createShader(rect);
    canvas.drawPath(left, leftPaint);

    final fold = Path()
      ..moveTo(size.width * 0.40, size.height * 0.39)
      ..cubicTo(
        size.width * 0.46,
        size.height * 0.44,
        size.width * 0.50,
        size.height * 0.55,
        size.width * 0.56,
        size.height * 0.63,
      )
      ..cubicTo(
        size.width * 0.61,
        size.height * 0.70,
        size.width * 0.67,
        size.height * 0.68,
        size.width * 0.72,
        size.height * 0.59,
      );

    final foldPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * 0.18
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          Color(0xFF315CFF),
          Color(0xFF6D50FF),
          Color(0xFFCE4DF2),
        ],
      ).createShader(rect);
    canvas.drawPath(fold, foldPaint);

    final risePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * 0.18
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..shader = const LinearGradient(
        begin: Alignment.bottomLeft,
        end: Alignment.topRight,
        colors: [
          Color(0xFF824CFF),
          Color(0xFF079BFF),
          Color(0xFF22E6F4),
        ],
        stops: [0.0, 0.48, 1.0],
      ).createShader(rect);
    canvas.drawPath(rise, risePaint);

    final arrow = Path()
      ..moveTo(size.width * 0.72, size.height * 0.26)
      ..lineTo(size.width * 0.92, size.height * 0.18)
      ..quadraticBezierTo(
        size.width * 0.95,
        size.height * 0.17,
        size.width * 0.94,
        size.height * 0.21,
      )
      ..lineTo(size.width * 0.92, size.height * 0.41)
      ..lineTo(size.width * 0.85, size.height * 0.33)
      ..close();

    final arrowPaint = Paint()
      ..style = PaintingStyle.fill
      ..shader = const LinearGradient(
        begin: Alignment.bottomLeft,
        end: Alignment.topRight,
        colors: [
          Color(0xFF079BFF),
          Color(0xFF23E4F2),
        ],
      ).createShader(rect);
    canvas.drawPath(arrow, arrowPaint);

    final highlight = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * 0.022
      ..strokeCap = StrokeCap.round
      ..color = Colors.white.withOpacity(0.16);

    final highlightPath = Path()
      ..moveTo(size.width * 0.18, size.height * 0.67)
      ..cubicTo(
        size.width * 0.28,
        size.height * 0.46,
        size.width * 0.32,
        size.height * 0.34,
        size.width * 0.39,
        size.height * 0.39,
      );
    canvas.drawPath(highlightPath, highlight);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
