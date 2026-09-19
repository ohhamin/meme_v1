import 'dart:async';

import 'package:flutter/material.dart';

import 'screens/algorithm_screen.dart';
import 'screens/daily_markdown_screen.dart';
import 'screens/decision_screen.dart';
import 'screens/market_screen.dart';
import 'screens/paper_dashboard_screen.dart';
import 'screens/settings_screen.dart';
import 'theme/app_theme.dart';
import 'services/push_registration.dart';


void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MemeApp());
  unawaited(PushRegistrationService.instance.initialize());
}


class MemeApp extends StatelessWidget {
  const MemeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'meme_v1',
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
  int _index = 0;

  static const _titles = [
    'Paper 대시보드',
    '주식',
    '코인',
    '뉴스',
    '판단',
    '알고리즘',
    '세팅',
  ];

  final List<Widget> _screens = [
    const PaperDashboardScreen(),
    const MarketScreen(isStock: true),
    const MarketScreen(isStock: false),
    const DailyMarkdownScreen(kind: 'news'),
    const DecisionScreen(),
    const AlgorithmScreen(),
    const SettingsScreen(),
  ];

  void _selectTab(int value) {
    setState(() {
      _index = value;
      // These screens are mode-aware on the backend. Recreate them whenever
      // the user enters the tab so a Paper/Live change in Settings is reflected
      // immediately without requiring pull-to-refresh.
      if (value == 1) {
        _screens[1] = MarketScreen(key: UniqueKey(), isStock: true);
      } else if (value == 2) {
        _screens[2] = MarketScreen(key: UniqueKey(), isStock: false);
      } else if (value == 4) {
        _screens[4] = DecisionScreen(key: UniqueKey());
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_index]),
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
          color: AppColors.surface,
          border: Border(
            top: BorderSide(
              color: AppColors.divider,
              width: 0.7,
            ),
          ),
        ),
        child: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: _selectTab,
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.space_dashboard_outlined),
              selectedIcon: Icon(Icons.space_dashboard_rounded),
              label: '홈',
            ),
            NavigationDestination(
              icon: Icon(Icons.show_chart_rounded),
              selectedIcon: Icon(Icons.show_chart_rounded),
              label: '주식',
            ),
            NavigationDestination(
              icon: Icon(Icons.currency_bitcoin_rounded),
              selectedIcon: Icon(Icons.currency_bitcoin_rounded),
              label: '코인',
            ),
            NavigationDestination(
              icon: Icon(Icons.article_outlined),
              selectedIcon: Icon(Icons.article_rounded),
              label: '뉴스',
            ),
            NavigationDestination(
              icon: Icon(Icons.psychology_alt_outlined),
              selectedIcon: Icon(Icons.psychology_alt_rounded),
              label: '판단',
            ),
            NavigationDestination(
              icon: Icon(Icons.account_tree_outlined),
              selectedIcon: Icon(Icons.account_tree_rounded),
              label: '알고리즘',
            ),
            NavigationDestination(
              icon: Icon(Icons.settings_outlined),
              selectedIcon: Icon(Icons.settings_rounded),
              label: '세팅',
            ),
          ],
        ),
      ),
    );
  }
}
