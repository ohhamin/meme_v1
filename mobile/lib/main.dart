import 'package:flutter/material.dart';

import 'screens/algorithm_screen.dart';
import 'screens/daily_markdown_screen.dart';
import 'screens/market_screen.dart';
import 'screens/settings_screen.dart';


void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MemeApp());
}


class MemeApp extends StatelessWidget {
  const MemeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'meme_v1',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.blueGrey,
      ),
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
    '주식',
    '코인',
    '뉴스',
    '판단',
    '알고리즘',
    '세팅',
  ];

  final _screens = const [
    MarketScreen(isStock: true),
    MarketScreen(isStock: false),
    DailyMarkdownScreen(kind: 'news'),
    DailyMarkdownScreen(kind: 'decisions'),
    AlgorithmScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_index]),
      ),
      body: IndexedStack(
        index: _index,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (value) {
          setState(() => _index = value);
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.candlestick_chart),
            label: '주식',
          ),
          NavigationDestination(
            icon: Icon(Icons.currency_bitcoin),
            label: '코인',
          ),
          NavigationDestination(
            icon: Icon(Icons.article_outlined),
            label: '뉴스',
          ),
          NavigationDestination(
            icon: Icon(Icons.psychology_alt_outlined),
            label: '판단',
          ),
          NavigationDestination(
            icon: Icon(Icons.account_tree_outlined),
            label: '알고리즘',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            label: '세팅',
          ),
        ],
      ),
    );
  }
}
