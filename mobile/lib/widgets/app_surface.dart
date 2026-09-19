import 'package:flutter/material.dart';

import '../theme/app_theme.dart';


class AppSurface extends StatelessWidget {
  const AppSurface({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(18),
    this.margin,
    this.emphasized = false,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      padding: padding,
      decoration: BoxDecoration(
        gradient: AppGradients.surface,
        borderRadius: BorderRadius.circular(AppRadius.large),
        border: Border.all(
          color: emphasized
              ? AppColors.primaryBlue.withOpacity(0.34)
              : AppColors.borderSoft,
          width: emphasized ? 1.0 : 0.8,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.22),
            blurRadius: 20,
            spreadRadius: -10,
            offset: const Offset(0, 12),
          ),
          if (emphasized)
            BoxShadow(
              color: AppColors.primaryBlue.withOpacity(0.10),
              blurRadius: 24,
              spreadRadius: -12,
            ),
        ],
      ),
      child: child,
    );
  }
}


class SectionTitle extends StatelessWidget {
  const SectionTitle(
    this.title, {
    super.key,
    this.trailing,
  });

  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 3,
          height: 18,
          decoration: BoxDecoration(
            gradient: AppGradients.primary,
            borderRadius: BorderRadius.circular(99),
          ),
        ),
        const SizedBox(width: 9),
        Expanded(
          child: Text(
            title,
            style: Theme.of(context).textTheme.titleLarge,
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}


class AppEmptyState extends StatelessWidget {
  const AppEmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.description,
  });

  final IconData icon;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 58,
              height: 58,
              decoration: BoxDecoration(
                color: AppColors.surfaceElevated,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: AppColors.borderSoft,
                ),
              ),
              child: ShaderMask(
                shaderCallback: (bounds) =>
                    AppGradients.primary.createShader(bounds),
                blendMode: BlendMode.srcIn,
                child: Icon(
                  icon,
                  color: Colors.white,
                  size: 27,
                ),
              ),
            ),
            const SizedBox(height: 18),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            Text(
              description,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
