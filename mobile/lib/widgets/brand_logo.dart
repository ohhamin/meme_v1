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
                    AppColors.primaryBlue.withValues(alpha: 0.16),
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
                    AppColors.primaryPurple.withValues(alpha: 0.12),
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
    this.size = 52,
    this.showBackground = false,
  });

  final double size;
  final bool showBackground;

  @override
  Widget build(BuildContext context) {
    final logo = Image.asset(
      'assets/brand/meme_app_logo.png',
      width: size,
      height: size,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
    );

    if (!showBackground) {
      return SizedBox.square(
        dimension: size,
        child: logo,
      );
    }

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(size * 0.22),
      ),
      child: logo,
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
    final size = compact ? 54.0 : 78.0;
    return BrandMark(
      size: size,
      showBackground: false,
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
            color: AppColors.surfaceElevated.withValues(alpha: 0.72),
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
              ? AppColors.primaryBlue.withValues(alpha: 0.72)
              : AppColors.borderSoft,
          width: selected ? 1.0 : 0.8,
        ),
        boxShadow: selected
            ? [
                BoxShadow(
                  color: AppColors.primaryBlue.withValues(alpha: 0.18),
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
          color: AppColors.primaryBlue.withValues(alpha: 0.30),
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.primaryBlue.withValues(alpha: 0.11),
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


