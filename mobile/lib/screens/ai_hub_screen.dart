import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import 'algorithm_screen.dart';
import 'decision_screen.dart';


class AiHubScreen extends StatelessWidget {
  const AiHubScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Column(
        children: [
          Container(
            margin: const EdgeInsets.fromLTRB(20, 4, 20, 14),
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: AppColors.chip,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: AppColors.borderSoft,
                width: 0.8,
              ),
            ),
            child: TabBar(
              dividerColor: Colors.transparent,
              indicatorSize: TabBarIndicatorSize.tab,
              labelColor: AppColors.textPrimary,
              unselectedLabelColor: AppColors.textMuted,
              labelStyle: const TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 13,
              ),
              unselectedLabelStyle: const TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
              indicator: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xFF0E2948),
                    Color(0xFF09182A),
                  ],
                ),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: AppColors.primaryBlue.withValues(alpha: 0.42),
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.primaryBlue.withValues(alpha: 0.10),
                    blurRadius: 14,
                    spreadRadius: -6,
                  ),
                ],
              ),
              tabs: const [
                Tab(
                  icon: Icon(Icons.psychology_alt_outlined, size: 19),
                  text: 'AI 판단',
                ),
                Tab(
                  icon: Icon(Icons.account_tree_outlined, size: 19),
                  text: '알고리즘',
                ),
              ],
            ),
          ),
          const Expanded(
            child: TabBarView(
              children: [
                DecisionScreen(),
                AlgorithmScreen(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
