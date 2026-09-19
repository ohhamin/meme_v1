import 'package:flutter/material.dart';


abstract final class AppColors {
  // MEME AI INVEST brand palette.
  static const background = Color(0xFF07111F);
  static const backgroundSoft = Color(0xFF0A1627);
  static const surface = Color(0xFF0E1C2F);
  static const surfaceElevated = Color(0xFF13243A);
  static const surfaceStrong = Color(0xFF172A43);
  static const border = Color(0xFF1E3857);

  static const textPrimary = Color(0xFFF5F8FF);
  static const textSecondary = Color(0xFFA0B2C9);
  static const textMuted = Color(0xFF71839B);

  static const primary = Color(0xFF2FD8FF);
  static const primaryBlue = Color(0xFF2F7BFF);
  static const primaryPurple = Color(0xFF8B5CFF);
  static const primarySoft = Color(0xFF102C4C);

  static const positive = Color(0xFF21D49B);
  static const positiveSoft = Color(0xFF123B34);
  static const negative = Color(0xFFFF6275);
  static const negativeSoft = Color(0xFF3D1E2B);
  static const warning = Color(0xFFFFBF5B);

  static const divider = Color(0xFF1B304A);
  static const chip = Color(0xFF12243A);
}


abstract final class AppGradients {
  static const primary = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      AppColors.primary,
      AppColors.primaryBlue,
      AppColors.primaryPurple,
    ],
  );

  static const surface = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      AppColors.surfaceElevated,
      AppColors.surface,
    ],
  );

  static const hero = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF123866),
      Color(0xFF0B2342),
      Color(0xFF20194B),
    ],
  );
}


abstract final class AppRadius {
  static const small = 10.0;
  static const medium = 14.0;
  static const large = 20.0;
  static const extraLarge = 26.0;
  static const pill = 999.0;
}


abstract final class AppSpacing {
  static const xs = 4.0;
  static const sm = 8.0;
  static const md = 12.0;
  static const lg = 16.0;
  static const xl = 20.0;
  static const xxl = 24.0;
  static const section = 28.0;
}


ThemeData buildAppTheme() {
  final scheme = const ColorScheme.dark(
    primary: AppColors.primaryBlue,
    secondary: AppColors.primary,
    surface: AppColors.surface,
    error: AppColors.negative,
    onPrimary: Colors.white,
    onSecondary: AppColors.background,
    onSurface: AppColors.textPrimary,
    onError: Colors.white,
  );

  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: AppColors.background,
    colorScheme: scheme,
  );

  return base.copyWith(
    splashFactory: InkSparkle.splashFactory,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.background,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      toolbarHeight: 70,
      titleSpacing: 20,
      titleTextStyle: TextStyle(
        color: AppColors.textPrimary,
        fontSize: 22,
        height: 1.2,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.5,
      ),
    ),
    textTheme: base.textTheme.copyWith(
      headlineMedium: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 28,
        height: 1.2,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.8,
      ),
      titleLarge: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 20,
        height: 1.35,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.4,
      ),
      titleMedium: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 17,
        height: 1.4,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.25,
      ),
      bodyLarge: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 16,
        height: 1.5,
        fontWeight: FontWeight.w500,
        letterSpacing: -0.2,
      ),
      bodyMedium: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 14,
        height: 1.5,
        fontWeight: FontWeight.w500,
        letterSpacing: -0.15,
      ),
      bodySmall: const TextStyle(
        color: AppColors.textSecondary,
        fontSize: 12,
        height: 1.45,
        fontWeight: FontWeight.w500,
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      height: 70,
      backgroundColor: AppColors.backgroundSoft,
      indicatorColor: AppColors.primarySoft,
      elevation: 0,
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const IconThemeData(
            color: AppColors.primary,
            size: 23,
          );
        }
        return const IconThemeData(
          color: AppColors.textMuted,
          size: 22,
        );
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return TextStyle(
          color: selected ? AppColors.primary : AppColors.textMuted,
          fontSize: 10.5,
          height: 1.1,
          fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
          letterSpacing: -0.2,
        );
      }),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surfaceElevated,
      hintStyle: const TextStyle(color: AppColors.textMuted),
      labelStyle: const TextStyle(color: AppColors.textSecondary),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.medium),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.medium),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.medium),
        borderSide: const BorderSide(
          color: AppColors.primary,
          width: 1.4,
        ),
      ),
      contentPadding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 16,
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primaryBlue,
        foregroundColor: Colors.white,
        minimumSize: const Size(0, 50),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.medium),
        ),
        textStyle: const TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.textPrimary,
        minimumSize: const Size(0, 50),
        side: const BorderSide(color: AppColors.border),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.medium),
        ),
        textStyle: const TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primary,
      ),
    ),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.all(Colors.white),
      trackColor: WidgetStateProperty.resolveWith((states) {
        return states.contains(WidgetState.selected)
            ? AppColors.primaryBlue
            : AppColors.border;
      }),
      trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: AppColors.surfaceStrong,
      contentTextStyle: const TextStyle(
        color: AppColors.textPrimary,
        fontWeight: FontWeight.w600,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.medium),
      ),
      behavior: SnackBarBehavior.floating,
    ),
    dividerTheme: const DividerThemeData(
      color: AppColors.divider,
      thickness: 1,
      space: 1,
    ),
  );
}
