import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'screens/ai_hub_screen.dart';
import 'screens/daily_markdown_screen.dart';
import 'screens/market_screen.dart';
import 'screens/paper_dashboard_screen.dart';
import 'screens/settings_screen.dart';
import 'services/push_registration.dart';
import 'services/api_client.dart';
import 'theme/app_theme.dart';
import 'widgets/brand_logo.dart';


Future<void> _reportFlutterError(
  Object error,
  StackTrace stack, {
  String library = 'flutter',
  String context = '',
}) async {
  try {
    await ApiClient.instance.reportClientError(
      message: error.toString(),
      stack: stack.toString(),
      library: library,
      context: context,
    );
  } catch (_) {
    // Error reporting must never create another user-visible failure.
  }
}

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    unawaited(
      _reportFlutterError(
        details.exception,
        details.stack ?? StackTrace.current,
        library: details.library ?? 'flutter',
        context: details.context?.toDescription() ?? '',
      ),
    );
  };

  PlatformDispatcher.instance.onError = (error, stack) {
    unawaited(_reportFlutterError(error, stack, library: 'platform'));
    return true;
  };
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      statusBarBrightness: Brightness.dark,
      systemNavigationBarColor: AppColors.background,
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );
  runApp(const MemeApp());
  unawaited(PushRegistrationService.instance.initialize());
}


class MemeApp extends StatelessWidget {
  const MemeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MEME AI INVEST',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: const AppShell(),
    );
  }
}


class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}


class _AppShellState extends State<AppShell> {
  // The former home/Paper dashboard is now the Performance tab.
  int _index = 4;

  static const _titles = [
    '주식',
    '코인',
    'AI 판단',
    '뉴스',
    '성과',
    '설정',
  ];

  final List<Widget> _screens = [
    const MarketScreen(isStock: true),
    const MarketScreen(isStock: false),
    const AiHubScreen(),
    const DailyMarkdownScreen(kind: 'news'),
    const PaperDashboardScreen(),
    const SettingsScreen(),
  ];

  void _selectTab(int value) {
    setState(() {
      _index = value;
      // These screens are mode-aware on the backend. Recreate them whenever
      // the user enters the tab so Paper/Live changes are reflected right away.
      if (value == 0) {
        _screens[0] = MarketScreen(key: UniqueKey(), isStock: true);
      } else if (value == 1) {
        _screens[1] = MarketScreen(key: UniqueKey(), isStock: false);
      } else if (value == 2) {
        _screens[2] = AiHubScreen(key: UniqueKey());
      } else if (value == 4) {
        _screens[4] = PaperDashboardScreen(key: UniqueKey());
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return AppBackdrop(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: BrandAppBarTitle(pageTitle: _titles[_index]),
        ),
        body: SafeArea(
          top: false,
          child: IndexedStack(
            index: _index,
            children: _screens,
          ),
        ),
        bottomNavigationBar: DecoratedBox(
          decoration: const BoxDecoration(
            color: Color(0xF507111E),
            border: Border(
              top: BorderSide(
                color: AppColors.divider,
                width: 0.8,
              ),
            ),
          ),
          child: Theme(
            data: Theme.of(context).copyWith(
              splashFactory: NoSplash.splashFactory,
              splashColor: Colors.transparent,
              highlightColor: Colors.transparent,
              hoverColor: Colors.transparent,
            ),
            child: NavigationBar(
              selectedIndex: _index,
              onDestinationSelected: _selectTab,
              destinations: const [
              NavigationDestination(
                icon: BrandNavIcon(icon: Icons.bar_chart_rounded),
                selectedIcon: BrandNavIcon(
                  icon: Icons.bar_chart_rounded,
                  selected: true,
                ),
                label: '주식',
              ),
              NavigationDestination(
                icon: BrandNavIcon(icon: Icons.currency_bitcoin_rounded),
                selectedIcon: BrandNavIcon(
                  icon: Icons.currency_bitcoin_rounded,
                  selected: true,
                ),
                label: '코인',
              ),
              NavigationDestination(
                icon: BrandNavIcon(icon: Icons.psychology_alt_outlined),
                selectedIcon: BrandNavIcon(
                  icon: Icons.psychology_alt_rounded,
                  selected: true,
                ),
                label: 'AI 판단',
              ),
              NavigationDestination(
                icon: BrandNavIcon(icon: Icons.article_outlined),
                selectedIcon: BrandNavIcon(
                  icon: Icons.article_rounded,
                  selected: true,
                ),
                label: '뉴스',
              ),
              NavigationDestination(
                icon: BrandNavIcon(icon: Icons.pie_chart_outline_rounded),
                selectedIcon: BrandNavIcon(
                  icon: Icons.pie_chart_rounded,
                  selected: true,
                ),
                label: '성과',
              ),
              NavigationDestination(
                icon: BrandNavIcon(icon: Icons.settings_outlined),
                selectedIcon: BrandNavIcon(
                  icon: Icons.settings_rounded,
                  selected: true,
                ),
                label: '설정',
              ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
