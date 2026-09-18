import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../widgets/app_surface.dart';


class AlgorithmScreen extends StatefulWidget {
  const AlgorithmScreen({super.key});

  @override
  State<AlgorithmScreen> createState() => _AlgorithmScreenState();
}


class _AlgorithmScreenState extends State<AlgorithmScreen> {
  late Future<String> _current;
  late Future<List<Map<String, dynamic>>> _proposals;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _current = ApiClient.instance.getCurrentAlgorithm();
    _proposals = ApiClient.instance.getAlgorithmProposals();
  }

  Future<void> _apply(String id) async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          padding: const EdgeInsets.fromLTRB(22, 12, 22, 24),
          decoration: const BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
          ),
          child: SafeArea(
            top: false,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 38,
                    height: 4,
                    decoration: BoxDecoration(
                      color: AppColors.divider,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                Text(
                  '이 제안을 적용할까요?',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  '다음 판단 사이클부터 현재 알고리즘 규칙에 반영돼요.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
                const SizedBox(height: 22),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: const Text('돌아가기'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: const Text('적용'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );

    if (ok != true) return;

    try {
      await ApiClient.instance.applyAlgorithmProposal(id);
      if (!mounted) return;
      setState(_reload);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('알고리즘 제안을 적용했어요.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _cancel(String id) async {
    try {
      await ApiClient.instance.cancelAlgorithmProposal(id);
      if (!mounted) return;
      setState(_reload);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('제안을 취소했어요.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Column(
        children: [
          Container(
            margin: const EdgeInsets.fromLTRB(20, 4, 20, 18),
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: AppColors.chip,
              borderRadius: BorderRadius.circular(16),
            ),
            child: TabBar(
              dividerColor: Colors.transparent,
              indicatorSize: TabBarIndicatorSize.tab,
              labelColor: AppColors.textPrimary,
              unselectedLabelColor: AppColors.textSecondary,
              labelStyle: const TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 14,
              ),
              unselectedLabelStyle: const TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 14,
              ),
              indicator: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(12),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x10000000),
                    blurRadius: 8,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              tabs: const [
                Tab(text: '현재'),
                Tab(text: '제안'),
              ],
            ),
          ),
          Expanded(
            child: TabBarView(
              children: [
                _CurrentAlgorithm(future: _current),
                _ProposalList(
                  future: _proposals,
                  onApply: _apply,
                  onCancel: _cancel,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}


class _CurrentAlgorithm extends StatelessWidget {
  const _CurrentAlgorithm({required this.future});

  final Future<String> future;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }

        if (snapshot.hasError) {
          return const AppEmptyState(
            icon: Icons.account_tree_outlined,
            title: '알고리즘을 불러오지 못했어요',
            description: '백엔드 연결 상태를 확인해 주세요.',
          );
        }

        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
          children: [
            AppSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.positiveSoft,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: const Text(
                      '현재 적용 중',
                      style: TextStyle(
                        color: AppColors.positive,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  MarkdownBody(
                    data: snapshot.data ?? '',
                    selectable: true,
                    styleSheet: MarkdownStyleSheet(
                      h1: Theme.of(context).textTheme.titleLarge,
                      h2: Theme.of(context).textTheme.titleMedium,
                      h3: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontSize: 15,
                          ),
                      p: Theme.of(context).textTheme.bodyMedium,
                      listBullet:
                          Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: AppColors.primary,
                                fontWeight: FontWeight.w800,
                              ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}


class _ProposalList extends StatelessWidget {
  const _ProposalList({
    required this.future,
    required this.onApply,
    required this.onCancel,
  });

  final Future<List<Map<String, dynamic>>> future;
  final ValueChanged<String> onApply;
  final ValueChanged<String> onCancel;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }

        if (snapshot.hasError) {
          return const AppEmptyState(
            icon: Icons.cloud_off_rounded,
            title: '제안을 불러오지 못했어요',
            description: '잠시 뒤 다시 확인해 주세요.',
          );
        }

        final items = snapshot.data ?? <Map<String, dynamic>>[];
        if (items.isEmpty) {
          return const AppEmptyState(
            icon: Icons.auto_awesome_outlined,
            title: '새로운 제안이 없어요',
            description: '매매 데이터가 쌓이고 개선 포인트가 발견되면 여기에 제안이 나타납니다.',
          );
        }

        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
          itemCount: items.length,
          separatorBuilder: (_, __) => const SizedBox(height: 12),
          itemBuilder: (context, index) {
            final item = items[index];
            final id = item['id']?.toString() ?? '';

            return AppSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.primarySoft,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: const Text(
                      '검토 필요',
                      style: TextStyle(
                        color: AppColors.primary,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    item['title']?.toString() ?? '알고리즘 개선 제안',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),
                  MarkdownBody(
                    data: item['markdown']?.toString() ?? '',
                    styleSheet: MarkdownStyleSheet(
                      h1: const TextStyle(fontSize: 0, height: 0),
                      h2: Theme.of(context).textTheme.titleMedium,
                      p: Theme.of(context).textTheme.bodyMedium,
                      listBullet:
                          Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: AppColors.primary,
                              ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton(
                          onPressed: () => onApply(id),
                          child: const Text('적용'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => onCancel(id),
                          child: const Text('취소'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}
