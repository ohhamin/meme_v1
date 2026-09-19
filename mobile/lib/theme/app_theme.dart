import 'package:flutter/material.dart';


abstract final class AppColors {
  // MEME AI INVEST reference palette (2026-09).
  static const background = Color(0xFF030C18);
  static const backgroundSoft = Color(0xFF071220);
  static const surface = Color(0xFF071423);
  static const surfaceElevated = Color(0xFF0A1B2D);
  static const surfaceStrong = Color(0xFF0D2238);
  static const border = Color(0xFF173B61);
  static const borderSoft = Color(0xFF102A47);

  static const textPrimary = Color(0xFFF7F9FD);
  static const textSecondary = Color(0xFF9AAECB);
  static const textMuted = Color(0xFF6C82A1);

  static const primary = Color(0xFF22DFF7);
  static const primaryBlue = Color(0xFF0797FF);
  static const primaryDeepBlue = Color(0xFF315BFF);
  static const primaryPurple = Color(0xFF8554FF);
  static const primaryPink = Color(0xFFD84DF2);
  static const primarySoft = Color(0xFF0A2844);

  static const positive = Color(0xFF26D6A1);
  static const positiveSoft = Color(0xFF0D332D);
  static const negative = Color(0xFFFF6478);
  static const negativeSoft = Color(0xFF371A29);
  static const warning = Color(0xFFFFC25E);

  static const divider = Color(0xFF102A44);
  static const chip = Color(0xFF0B1C2F);
}


abstract final class AppGradients {
  static const primary = LinearGradient(
    begin: Alignment.bottomLeft,
    end: Alignment.topRight,
    colors: [
      AppColors.primaryBlue,
      AppColors.primaryDeepBlue,
      AppColors.primaryPurple,
      AppColors.primary,
    ],
    stops: [0.0, 0.34, 0.64, 1.0],
  );

  static const surface = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF0A1B2E),
      Color(0xFF071321),
      Color(0xFF050F1C),
    ],
  );

  static const hero = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF0D3764),
      Color(0xFF081932),
      Color(0xFF0A1025),
      Color(0xFF1A0D38),
    ],
    stops: [0.0, 0.38, 0.70, 1.0],
  );

  static const backdrop = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF0A1B32),
      AppColors.background,
      Color(0xFF020812),
    ],
    stops: [0.0, 0.48, 1.0],
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
    scaffoldBackgroundColor: Colors.transparent,
    colorScheme: scheme,
  );

  return base.copyWith(
    splashFactory: InkSparkle.splashFactory,
    appBarTheme: const AppBarTheme(
      backgroundColor: Color(0xF7030C18),
      foregroundColor: AppColors.textPrimary,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      toolbarHeight: 72,
      titleSpacing: 18,
      titleTextStyle: TextStyle(
        color: AppColors.textPrimary,
        fontSize: 20,
        height: 1.2,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.4,
      ),
    ),
    textTheme: base.textTheme.copyWith(
      headlineMedium: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 28,
        height: 1.15,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.8,
      ),
      titleLarge: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 19,
        height: 1.35,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.35,
      ),
      titleMedium: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 16,
        height: 1.4,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.2,
      ),
      bodyLarge: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 16,
        height: 1.5,
        fontWeight: FontWeight.w500,
        letterSpacing: -0.15,
      ),
      bodyMedium: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 14,
        height: 1.5,
        fontWeight: FontWeight.w500,
        letterSpacing: -0.1,
      ),
      bodySmall: const TextStyle(
        color: AppColors.textSecondary,
        fontSize: 12,
        height: 1.45,
        fontWeight: FontWeight.w500,
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      height: 86,
      backgroundColor: const Color(0xF507111E),
      surfaceTintColor: Colors.transparent,
      indicatorColor: Colors.transparent,
      elevation: 0,
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
      iconTheme: WidgetStateProperty.all(
        const IconThemeData(size: 22),
      ),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return TextStyle(
          color: selected ? AppColors.textPrimary : AppColors.textMuted,
          fontSize: 10,
          height: 1.1,
          fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
          letterSpacing: -0.1,
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
        borderSide: const BorderSide(color: AppColors.borderSoft),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.medium),
        borderSide: const BorderSide(color: AppColors.borderSoft),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.medium),
        borderSide: const BorderSide(
          color: AppColors.primary,
          width: 1.2,
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
