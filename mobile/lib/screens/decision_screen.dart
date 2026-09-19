import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../widgets/app_surface.dart';
import '../widgets/date_selector.dart';


class DecisionScreen extends StatefulWidget {
  const DecisionScreen({super.key});

  @override
  State<DecisionScreen> createState() => _DecisionScreenState();
}


class _DecisionScreenState extends State<DecisionScreen> {
  DateTime _selected = DateTime.now();
  late Future<String> _future;
  late Future<Map<String, dynamic>?> _latestFuture;
  String _mode = 'paper';

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = _loadMarkdown();
    _latestFuture = _loadLatest();
  }

  Future<String> _loadMarkdown() async {
    final settings = await ApiClient.instance.getSettings();
    _mode = settings['mode']?.toString() ?? 'paper';
    return ApiClient.instance.getDailyMarkdown('decisions', _selected);
  }

  Future<Map<String, dynamic>?> _loadLatest() async {
    final settings = await ApiClient.instance.getSettings();
    final mode = settings['mode']?.toString() ?? 'paper';
    _mode = mode;
    return ApiClient.instance.getLatestDecision(mode: mode);
  }

  void _changeDate(DateTime value) {
    setState(() {
      _selected = value;
      _load();
    });
  }

  Future<void> _refresh() async {
    setState(_load);
    await Future.wait([
      _future,
      _latestFuture,
    ]);
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
                return const AppEmptyState(
                  icon: Icons.psychology_alt_outlined,
                  title: '이 날짜의 판단이 없어요',
                  description: '판단 사이클이 실행되면 종목별 카드가 여기에 쌓입니다.',
                );
              }

              final markdown = snapshot.data ?? '';
              final mode = _mode.toUpperCase();
              final cards = _DecisionParser.parse(markdown)
                  .where((item) => item.executionMode == mode)
                  .toList();
              final latestTime =
                  cards.isEmpty ? '' : cards.last.time;
              final latestCards = latestTime.isEmpty
                  ? <_DecisionCardData>[]
                  : cards.where((item) => item.time == latestTime).toList();
              final latestSummary = '';

              if (cards.isEmpty) {
                return Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                  child: AppSurface(
                    child: MarkdownBody(data: markdown),
                  ),
                );
              }

              final displayCards = cards.reversed.toList();
              return RefreshIndicator(
                onRefresh: _refresh,
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
                  itemCount: displayCards.length + 1,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    if (index == 0) {
                      return FutureBuilder<Map<String, dynamic>?>(
                        future: _latestFuture,
                        builder: (context, latestSnapshot) {
                          final latest = latestSnapshot.data;
                          final structuredCards = latest == null
                              ? <_DecisionCardData>[]
                              : _DecisionParser.fromLatestApi(latest);
                          return _LatestCycleSummary(
                            time: latest?['time']?.toString() ?? latestTime,
                            cards: structuredCards.isNotEmpty
                                ? structuredCards
                                : latestCards,
                            summary:
                                latest?['cycle_summary']?.toString() ??
                                    latestSummary,
                          );
                        },
                      );
                    }
                    return _DecisionCard(data: displayCards[index - 1]);
                  },
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}


class _LatestCycleSummary extends StatelessWidget {
  const _LatestCycleSummary({
    required this.time,
    required this.cards,
    required this.summary,
  });

  final String time;
  final List<_DecisionCardData> cards;
  final String summary;

  @override
  Widget build(BuildContext context) {
    int count(String action) => cards
        .where((item) => item.action.toUpperCase() == action)
        .length;

    return AppSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '최근 판단 1회',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              Text(
                time.isEmpty ? '-' : time,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(child: _Metric(label: 'BUY', value: count('BUY').toString())),
              Expanded(child: _Metric(label: 'HOLD', value: count('HOLD').toString())),
              Expanded(child: _Metric(label: 'SELL', value: count('SELL').toString())),
            ],
          ),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: 14),
            const Divider(),
            const SizedBox(height: 12),
            Text('사이클 요약', style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 6),
            Text(summary, style: Theme.of(context).textTheme.bodyMedium),
          ],
          const SizedBox(height: 10),
          Text(
            '아래에는 최신 판단부터 표시돼요. 아래로 당겨 새로고침할 수 있어요.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}


class _DecisionCardData {
  const _DecisionCardData({
    required this.time,
    required this.symbol,
    required this.action,
    required this.score,
    required this.reason,
    required this.risk,
    this.blockReason,
    this.nextCheck,
    this.orderSide,
    this.orderQuantity,
    this.orderNotional,
    this.executionMode = 'PAPER',
  });

  final String time;
  final String symbol;
  final String action;
  final String score;
  final String reason;
  final String risk;
  final String? blockReason;
  final String? nextCheck;
  final String? orderSide;
  final String? orderQuantity;
  final String? orderNotional;
  final String executionMode;
}


class _DecisionParser {
  static List<_DecisionCardData> fromLatestApi(
    Map<String, dynamic> data,
  ) {
    final rawItems = data['items'] as List<dynamic>? ?? <dynamic>[];
    return rawItems.map((raw) {
      final item = (raw as Map).cast<String, dynamic>();
      return _DecisionCardData(
        time: item['time']?.toString() ?? '',
        symbol: item['symbol']?.toString() ?? '',
        action: item['action']?.toString() ?? 'HOLD',
        score: item['score']?.toString() ?? '',
        reason: item['reason']?.toString() ?? '',
        risk: item['risk']?.toString() ?? '',
        blockReason: item['block_reason']?.toString(),
        nextCheck: item['next_check']?.toString(),
        orderSide: item['order_side']?.toString(),
        orderQuantity: item['order_quantity']?.toString(),
        orderNotional: item['order_notional']?.toString(),
        executionMode:
            item['execution_mode']?.toString().toUpperCase() ?? 'PAPER',
      );
    }).where((item) => item.symbol.isNotEmpty).toList();
  }

  static String latestSummary(String markdown) {
    const prefix = '> Cycle Summary:';
    String summary = '';
    for (final raw in markdown.split('\n')) {
      final line = raw.trim();
      if (line.startsWith(prefix)) {
        summary = line.substring(prefix.length).trim();
      }
    }
    return summary;
  }

  static List<_DecisionCardData> parse(String markdown) {
    final result = <_DecisionCardData>[];

    String cycleTime = '';
    String symbol = '';
    String action = '';
    String score = '';
    String reason = '';
    String risk = '';
    String? blockReason;
    String? nextCheck;
    String? orderSide;
    String? orderQuantity;
    String? orderNotional;
    String cycleMode = 'PAPER';

    void flush() {
      if (symbol.isEmpty) return;
      result.add(
        _DecisionCardData(
          time: cycleTime,
          symbol: symbol,
          action: action,
          score: score,
          reason: reason,
          risk: risk,
          blockReason: blockReason,
          nextCheck: nextCheck,
          orderSide: orderSide,
          orderQuantity: orderQuantity,
          orderNotional: orderNotional,
          executionMode: cycleMode,
        ),
      );
      symbol = '';
      action = '';
      score = '';
      reason = '';
      risk = '';
      blockReason = null;
      nextCheck = null;
      orderSide = null;
      orderQuantity = null;
      orderNotional = null;
    }

    for (final raw in markdown.split('\n')) {
      final line = raw.trim();

      if (line.startsWith('## ') && line.contains('Decision Cycle')) {
        flush();
        cycleTime =
            line.substring(3).replaceAll('Decision Cycle', '').trim();
        cycleMode = 'PAPER';
        continue;
      }

      if (line.startsWith('- Execution Mode:')) {
        cycleMode =
            line.substring('- Execution Mode:'.length).trim().toUpperCase();
        continue;
      }

      if (line.startsWith('### ')) {
        flush();
        symbol = line.substring(4).trim();
        continue;
      }

      if (line.startsWith('- Action:')) {
        action = line.substring('- Action:'.length).trim();
      } else if (line.startsWith('- Score:')) {
        score = line.substring('- Score:'.length).trim();
      } else if (line.startsWith('- Reason:')) {
        reason = line.substring('- Reason:'.length).trim();
      } else if (line.startsWith('- Risk Guard:')) {
        risk = line.substring('- Risk Guard:'.length).trim();
      } else if (line.startsWith('- Block Reason:')) {
        blockReason = line.substring('- Block Reason:'.length).trim();
      } else if (line.startsWith('- Next Check:')) {
        nextCheck = line.substring('- Next Check:'.length).trim();
      } else if (line.startsWith('- Order:')) {
        orderSide = line.substring('- Order:'.length).trim();
      } else if (line.startsWith('- Order Quantity:')) {
        orderQuantity = line.substring('- Order Quantity:'.length).trim();
      } else if (line.startsWith('- Order Notional:')) {
        orderNotional = line.substring('- Order Notional:'.length).trim();
      }
    }

    flush();
    return result;
  }
}


class _DecisionCard extends StatelessWidget {
  const _DecisionCard({required this.data});

  final _DecisionCardData data;

  Color get _actionColor {
    switch (data.action.toUpperCase()) {
      case 'BUY':
        return AppColors.primary;
      case 'SELL':
        return AppColors.negative;
      default:
        return AppColors.textSecondary;
    }
  }

  Color get _actionBackground {
    switch (data.action.toUpperCase()) {
      case 'BUY':
        return AppColors.primarySoft;
      case 'SELL':
        return AppColors.negativeSoft;
      default:
        return AppColors.chip;
    }
  }

  @override
  Widget build(BuildContext context) {
    final risk = data.risk.toUpperCase();
    final blocked = risk.contains('BLOCK');
    final pending = risk.contains('PENDING');
    final noOrder = risk.contains('NO_ORDER');

    return AppSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      data.symbol,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 3),
                    Text(
                      data.time.isEmpty ? '판단 사이클' : data.time,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
                decoration: BoxDecoration(
                  color: _actionBackground,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  data.action.isEmpty ? 'HOLD' : data.action,
                  style: TextStyle(
                    color: _actionColor,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              _Metric(
                label: '판단점수',
                value: data.score.isEmpty ? '-' : data.score,
              ),
              const SizedBox(width: 28),
              _Metric(
                label: 'Risk Guard',
                value: blocked
                    ? '차단'
                    : pending
                        ? '대기'
                        : noOrder
                            ? '주문없음'
                            : '통과',
                valueColor: blocked
                    ? AppColors.negative
                    : pending
                        ? AppColors.warning
                        : noOrder
                            ? AppColors.textSecondary
                            : AppColors.positive,
              ),
            ],
          ),
          if (data.reason.isNotEmpty) ...[
            const SizedBox(height: 18),
            const Divider(),
            const SizedBox(height: 14),
            Text(
              '판단 근거',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 6),
            Text(
              data.reason,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
          if (data.orderSide?.isNotEmpty == true) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.primarySoft,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.check_circle_outline_rounded,
                    color: AppColors.primary,
                    size: 19,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      (data.executionMode == 'LIVE'
                              ? 'Live 주문 · '
                              : 'Paper 주문 · ') +
                          (data.orderSide ?? '') +
                          ' · ' +
                          (data.orderQuantity ?? '-') +
                          ' · ' +
                          (data.orderNotional ?? '-') +
                          '원',
                      style: const TextStyle(
                        color: AppColors.primary,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          if (data.blockReason?.isNotEmpty == true) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.negativeSoft,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Text(
                '차단 사유 · ${data.blockReason}',
                style: const TextStyle(
                  color: AppColors.negative,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
          if (data.nextCheck?.isNotEmpty == true) ...[
            const SizedBox(height: 12),
            Text(
              '다음 판단 ${data.nextCheck}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ],
      ),
    );
  }
}


class _Metric extends StatelessWidget {
  const _Metric({
    required this.label,
    required this.value,
    this.valueColor,
  });

  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: valueColor,
              ),
        ),
      ],
    );
  }
}
