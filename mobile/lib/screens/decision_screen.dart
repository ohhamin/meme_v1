import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../utils/decision_text.dart';
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

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = ApiClient.instance.getDailyMarkdown('decisions', _selected);
    _latestFuture = ApiClient.instance.getLatestDecision();
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
              final cards = _DecisionParser.parse(markdown);

              if (cards.isEmpty) {
                return Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                  child: AppSurface(
                    child: MarkdownBody(data: markdown),
                  ),
                );
              }

              final summaries = _DecisionParser.cycleSummaries(markdown);
              final grouped = <String, List<_DecisionCardData>>{};
              for (final card in cards) {
                grouped.putIfAbsent(card.time, () => <_DecisionCardData>[])
                    .add(card);
              }
              final cycles = grouped.entries.toList().reversed.toList();

              return RefreshIndicator(
                onRefresh: _refresh,
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
                  itemCount: cycles.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 16),
                  itemBuilder: (context, index) {
                    final cycle = cycles[index];
                    return _DecisionCycleCard(
                      time: cycle.key,
                      cards: cycle.value,
                      summary: summaries[cycle.key] ?? '',
                      cycleNumber: cycles.length - index,
                    );
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



class _DecisionCycleCard extends StatefulWidget {
  const _DecisionCycleCard({
    required this.time,
    required this.cards,
    required this.summary,
    required this.cycleNumber,
  });

  final String time;
  final List<_DecisionCardData> cards;
  final String summary;
  final int cycleNumber;

  @override
  State<_DecisionCycleCard> createState() => _DecisionCycleCardState();
}


class _DecisionCycleCardState extends State<_DecisionCycleCard> {
  bool _summaryExpanded = false;

  int _rank(String action) {
    switch (action.toUpperCase()) {
      case 'BUY':
        return 0;
      case 'SELL':
        return 1;
      default:
        return 2;
    }
  }

  @override
  Widget build(BuildContext context) {
    int count(String action) => widget.cards
        .where((item) => item.action.toUpperCase() == action)
        .length;
    final ordered = [...widget.cards]
      ..sort((a, b) {
        final byAction = _rank(a.action).compareTo(_rank(b.action));
        if (byAction != 0) return byAction;
        return a.symbol.compareTo(b.symbol);
      });

    return AppSurface(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '판단 #${widget.cycleNumber}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              Text(
                widget.time.isEmpty ? '-' : widget.time,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'BUY ${count('BUY')} · SELL ${count('SELL')} · HOLD ${count('HOLD')}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          if (widget.summary.isNotEmpty) ...[
            const SizedBox(height: 8),
            InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: () => setState(() {
                _summaryExpanded = !_summaryExpanded;
              }),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Expanded(
                      child: Text(
                        widget.summary,
                        maxLines: _summaryExpanded ? null : 2,
                        overflow: _summaryExpanded
                            ? TextOverflow.visible
                            : TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Icon(
                      _summaryExpanded
                          ? Icons.keyboard_arrow_up_rounded
                          : Icons.keyboard_arrow_down_rounded,
                      size: 20,
                      color: AppColors.textSecondary,
                    ),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 10),
          for (var i = 0; i < ordered.length; i++) ...[
            _DecisionCard(data: ordered[i]),
            if (i != ordered.length - 1) const SizedBox(height: 7),
          ],
        ],
      ),
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
              Expanded(child: _Metric(label: 'SELL', value: count('SELL').toString())),
              Expanded(child: _Metric(label: 'HOLD', value: count('HOLD').toString())),
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
    this.decisionSource = 'AI',
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
  final String decisionSource;
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
        decisionSource:
            item['decision_source']?.toString().toUpperCase() ?? 'AI',
      );
    }).where((item) => item.symbol.isNotEmpty).toList();
  }

  static Map<String, String> cycleSummaries(String markdown) {
    final result = <String, String>{};
    String time = '';
    for (final raw in markdown.split('\n')) {
      final line = raw.trim();
      if (line.startsWith('## ') && line.contains('Decision Cycle')) {
        time = line.substring(3).replaceAll('Decision Cycle', '').trim();
      } else if (time.isNotEmpty && line.startsWith('> Cycle Summary:')) {
        result[time] = line.substring('> Cycle Summary:'.length).trim();
      }
    }
    return result;
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
    String cycleSource = 'AI';

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
          decisionSource: cycleSource,
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
        cycleSource = 'AI';
        continue;
      }

      if (line.startsWith('- Execution Mode:')) {
        cycleMode =
            line.substring('- Execution Mode:'.length).trim().toUpperCase();
        continue;
      }

      if (line.startsWith('- Decision Source:')) {
        cycleSource =
            line.substring('- Decision Source:'.length).trim().toUpperCase();
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



class _DecisionCard extends StatefulWidget {
  const _DecisionCard({required this.data});

  final _DecisionCardData data;

  @override
  State<_DecisionCard> createState() => _DecisionCardState();
}


class _DecisionCardState extends State<_DecisionCard> {
  bool _expanded = false;

  _DecisionCardData get data => widget.data;

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

  String get _actionLabel {
    final action = data.action.isEmpty ? 'HOLD' : data.action;
    return data.decisionSource == 'RISK_MONITOR'
        ? '$action · 리스크 청산'
        : action;
  }

  @override
  Widget build(BuildContext context) {
    final risk = data.risk.toUpperCase();
    final blocked = risk.contains('BLOCK');
    final pending = risk.contains('PENDING');
    final noOrder = risk.contains('NO_ORDER');
    final forceExit = risk.contains('FORCE_EXIT');

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () => setState(() => _expanded = !_expanded),
      child: AppSurface(
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 11),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    data.symbol,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                if (data.score.isNotEmpty) ...[
                  Text(
                    data.score,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: AppColors.textSecondary,
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(width: 8),
                ],
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: _actionBackground,
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    _actionLabel,
                    style: TextStyle(
                      color: _actionColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                Icon(
                  _expanded
                      ? Icons.keyboard_arrow_up_rounded
                      : Icons.keyboard_arrow_down_rounded,
                  size: 20,
                  color: AppColors.textSecondary,
                ),
              ],
            ),
            if (_expanded) ...[
              const SizedBox(height: 12),
              const Divider(height: 1),
              const SizedBox(height: 12),
              Row(
                children: [
                  _Metric(
                    label: '판단점수',
                    value: data.score.isEmpty ? '-' : data.score,
                  ),
                  const SizedBox(width: 28),
                  _Metric(
                    label: 'Risk Guard',
                    value: riskGuardLabel(data.risk),
                    valueColor: blocked || forceExit
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
                const SizedBox(height: 14),
                Text(
                  '판단 근거',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 5),
                Text(
                  localizeDecisionReason(data.reason),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
              if (data.orderSide?.isNotEmpty == true) ...[
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(11),
                  decoration: BoxDecoration(
                    color: AppColors.primarySoft,
                    borderRadius: BorderRadius.circular(12),
                  ),
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
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
              if (data.blockReason?.isNotEmpty == true) ...[
                const SizedBox(height: 10),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(11),
                  decoration: BoxDecoration(
                    color: AppColors.negativeSoft,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '차단 사유 · ${localizeDecisionReason(data.blockReason!)}',
                    style: const TextStyle(
                      color: AppColors.negative,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ],
          ],
        ),
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
