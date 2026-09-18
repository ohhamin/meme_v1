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

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = ApiClient.instance.getDailyMarkdown('decisions', _selected);
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
                return const AppEmptyState(
                  icon: Icons.psychology_alt_outlined,
                  title: '이 날짜의 판단이 없어요',
                  description: '판단 사이클이 실행되면 종목별 카드가 여기에 쌓입니다.',
                );
              }

              final markdown = snapshot.data ?? '';
              final cards = _DecisionParser.parse(markdown);

              if (cards.isEmpty) {
                return Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                  child: AppSurface(
                    child: MarkdownBody(data: markdown),
                  ),
                );
              }

              return ListView.separated(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
                itemCount: cards.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  return _DecisionCard(data: cards[index]);
                },
              );
            },
          ),
        ),
      ],
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
