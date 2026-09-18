import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../services/api_client.dart';


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
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('알고리즘 제안 적용'),
        content: const Text(
          '적용하면 다음 판단부터 현재 알고리즘 규칙에 반영됩니다. 적용할까요?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('적용'),
          ),
        ],
      ),
    );

    if (ok != true) return;

    try {
      await ApiClient.instance.applyAlgorithmProposal(id);
      if (!mounted) return;
      setState(_reload);
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
          const TabBar(
            tabs: [
              Tab(text: '현재'),
              Tab(text: '제안'),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                FutureBuilder<String>(
                  future: _current,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (snapshot.hasError) {
                      return Center(child: Text(snapshot.error.toString()));
                    }
                    return Markdown(
                      data: snapshot.data ?? '',
                      padding: const EdgeInsets.all(16),
                    );
                  },
                ),
                FutureBuilder<List<Map<String, dynamic>>>(
                  future: _proposals,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (snapshot.hasError) {
                      return Center(child: Text(snapshot.error.toString()));
                    }

                    final items =
                        snapshot.data ?? <Map<String, dynamic>>[];
                    if (items.isEmpty) {
                      return const Center(
                        child: Text('현재 대기 중인 알고리즘 제안이 없습니다.'),
                      );
                    }

                    return ListView.separated(
                      padding: const EdgeInsets.all(12),
                      itemCount: items.length,
                      separatorBuilder: (_, __) =>
                          const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final item = items[index];
                        final id = item['id']?.toString() ?? '';
                        return Card(
                          child: Padding(
                            padding: const EdgeInsets.all(14),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  item['title']?.toString() ?? '제안',
                                  style:
                                      Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 8),
                                MarkdownBody(
                                  data: item['markdown']?.toString() ?? '',
                                ),
                                const SizedBox(height: 12),
                                Row(
                                  children: [
                                    Expanded(
                                      child: FilledButton(
                                        onPressed: () => _apply(id),
                                        child: const Text('적용'),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: OutlinedButton(
                                        onPressed: () => _cancel(id),
                                        child: const Text('취소'),
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
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
