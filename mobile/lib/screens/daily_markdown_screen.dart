import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../widgets/app_surface.dart';
import '../widgets/date_selector.dart';


class DailyMarkdownScreen extends StatefulWidget {
  const DailyMarkdownScreen({
    super.key,
    required this.kind,
  });

  final String kind;

  @override
  State<DailyMarkdownScreen> createState() => _DailyMarkdownScreenState();
}


class _DailyMarkdownScreenState extends State<DailyMarkdownScreen> {
  DateTime _selected = DateTime.now();
  late Future<String> _future;

  String get _label => widget.kind == 'news' ? '뉴스' : '판단';

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = ApiClient.instance.getDailyMarkdown(widget.kind, _selected);
  }

  void _changeDate(DateTime value) {
    setState(() {
      _selected = value;
      _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final firstDate =
        DateTime(now.year, now.month, now.day).subtract(const Duration(days: 6));

    return Column(
      children: [
        DateSelector(
          date: _selected,
          firstDate: firstDate,
          lastDate: now,
          onChanged: _changeDate,
        ),
        Expanded(
          child: FutureBuilder<String>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }

              if (snapshot.hasError) {
                return AppEmptyState(
                  icon: widget.kind == 'news'
                      ? Icons.article_outlined
                      : Icons.psychology_alt_outlined,
                  title: '이 날짜의 ' + _label + '가 없어요',
                  description: widget.kind == 'news'
                      ? '매일 오전 9시와 오후 9시에 주요 경제 뉴스가 여기에 누적됩니다.'
                      : '판단 사이클이 실행되면 결과가 여기에 쌓입니다.',
                );
              }

              final markdown = snapshot.data ?? '';
              if (markdown.trim().isEmpty) {
                return AppEmptyState(
                  icon: Icons.inbox_outlined,
                  title: '아직 내용이 없어요',
                  description: _label + ' 데이터가 생기면 이 화면에서 볼 수 있습니다.',
                );
              }

              return ListView(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
                children: [
                  AppSurface(
                    padding: const EdgeInsets.fromLTRB(20, 18, 20, 22),
                    child: MarkdownBody(
                      data: markdown,
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
                        blockquoteDecoration: BoxDecoration(
                          color: AppColors.chip,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        blockquotePadding: const EdgeInsets.all(12),
                        codeblockDecoration: BoxDecoration(
                          color: AppColors.chip,
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}
