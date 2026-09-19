import 'package:flutter/material.dart';

import '../theme/app_theme.dart';


class BrandMark extends StatelessWidget {
  const BrandMark({
    super.key,
    this.size = 34,
    this.showBackground = true,
  });

  final double size;
  final bool showBackground;

  @override
  Widget build(BuildContext context) {
    final mark = CustomPaint(
      size: Size.square(size),
      painter: _BrandMarkPainter(),
    );

    if (!showBackground) {
      return mark;
    }

    return Container(
      width: size,
      height: size,
      padding: EdgeInsets.all(size * 0.14),
      decoration: BoxDecoration(
        gradient: AppGradients.hero,
        borderRadius: BorderRadius.circular(size * 0.28),
        border: Border.all(
          color: AppColors.primaryBlue.withOpacity(0.55),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.primaryBlue.withOpacity(0.22),
            blurRadius: size * 0.45,
            spreadRadius: -size * 0.16,
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
    final markSize = compact ? 32.0 : 46.0;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        BrandMark(size: markSize),
        SizedBox(width: compact ? 10 : 13),
        Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'MEME',
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: compact ? 17 : 23,
                height: 1,
                fontWeight: FontWeight.w900,
                letterSpacing: compact ? 0.7 : 1.2,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              subtitle ?? 'AI INVEST',
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: compact ? 8.5 : 10,
                height: 1,
                fontWeight: FontWeight.w700,
                letterSpacing: compact ? 2.2 : 3,
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
        const BrandMark(size: 34),
        const SizedBox(width: 11),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'MEME AI INVEST',
                style: TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.6,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                pageTitle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).appBarTheme.titleTextStyle,
              ),
            ],
          ),
        ),
      ],
    );
  }
}


class BrandHero extends StatelessWidget {
  const BrandHero({
    super.key,
    this.title = 'Invest smarter with data',
    this.subtitle = '데이터가 만드는 더 나은 선택',
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: AppGradients.hero,
        borderRadius: BorderRadius.circular(AppRadius.extraLarge),
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
            color: AppColors.primaryPurple.withOpacity(0.12),
            blurRadius: 28,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const BrandLockup(),
          const SizedBox(height: 22),
          Text(
            title,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontSize: 22,
                ),
          ),
          const SizedBox(height: 7),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}


class _BrandMarkPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final gradient = const LinearGradient(
      begin: Alignment.bottomLeft,
      end: Alignment.topRight,
      colors: [
        AppColors.primaryBlue,
        AppColors.primaryPurple,
        AppColors.primary,
      ],
      stops: [0, 0.5, 1],
    );

    final rect = Offset.zero & size;
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * 0.19
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..shader = gradient.createShader(rect);

    final path = Path()
      ..moveTo(size.width * 0.12, size.height * 0.70)
      ..lineTo(size.width * 0.31, size.height * 0.35)
      ..lineTo(size.width * 0.52, size.height * 0.69)
      ..lineTo(size.width * 0.81, size.height * 0.28);

    canvas.drawPath(path, stroke);

    final arrow = Path()
      ..moveTo(size.width * 0.68, size.height * 0.27)
      ..lineTo(size.width * 0.88, size.height * 0.16)
      ..lineTo(size.width * 0.85, size.height * 0.39)
      ..close();

    final fill = Paint()
      ..style = PaintingStyle.fill
      ..shader = gradient.createShader(rect);
    canvas.drawPath(arrow, fill);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
