import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../widgets/app_surface.dart';


class PaperDashboardScreen extends StatefulWidget {
  const PaperDashboardScreen({super.key});

  @override
  State<PaperDashboardScreen> createState() => _PaperDashboardScreenState();
}


class _PaperDashboardScreenState extends State<PaperDashboardScreen> {
  late Future<Map<String, dynamic>> _future;
  final NumberFormat _money = NumberFormat('#,###');

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = ApiClient.instance.getPaperDashboard();
  }

  Future<void> _refresh() async {
    setState(_load);
    await _future;
  }

  num _number(dynamic value) =>
      num.tryParse(value?.toString() ?? '0') ?? 0;

  Color _pnlColor(num value) {
    if (value > 0) return AppColors.positive;
    if (value < 0) return AppColors.negative;
    return AppColors.textPrimary;
  }

  String _signedPct(dynamic value) {
    final number = _number(value);
    final prefix = number > 0 ? '+' : '';
    return '$prefix${number.toStringAsFixed(2)}%';
  }

  String _signedMoney(dynamic value) {
    final number = _number(value);
    final prefix = number > 0 ? '+' : '';
    return '$prefix${_money.format(number)}원';
  }


  void _showOrderDecision(
    BuildContext context,
    Map<String, dynamic> order,
  ) {
    final side = order['side']?.toString().toUpperCase() ?? '-';
    final symbol = order['symbol']?.toString() ?? '-';
    final score = order['decision_score'] ?? order['entry_score'];
    final reason = order['decision_reason']?.toString().trim() ?? '';
    final createdAt = DateTime.tryParse(order['created_at']?.toString() ?? '');
    final time = createdAt == null
        ? '-'
        : DateFormat('yyyy.MM.dd HH:mm').format(createdAt.toLocal());

    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('$symbol · $side'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(time, style: Theme.of(dialogContext).textTheme.bodySmall),
            const SizedBox(height: 14),
            Text(
              '판단점수 ${score ?? '-'}',
              style: Theme.of(dialogContext).textTheme.titleMedium,
            ),
            const SizedBox(height: 10),
            Text(
              reason.isEmpty
                  ? '이 체결에는 저장된 판단 근거가 없어요. 앞으로 자동 체결은 당시 판단 근거를 함께 저장해요.'
                  : reason,
              style: Theme.of(dialogContext).textTheme.bodyMedium,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('닫기'),
          ),
        ],
      ),
    );
  }

  void _showOrdersSheet(
    BuildContext context,
    List<Map<String, dynamic>> orders,
  ) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.background,
      builder: (_) => _OrderHistorySheet(
        orders: orders,
        money: _money,
        onOrderTap: (order) {
          Navigator.of(context).pop();
          Future<void>.delayed(
            Duration.zero,
            () => _showOrderDecision(context, order),
          );
        },
      ),
    );
  }

  void _showPositionsSheet(
    BuildContext context,
    List<Map<String, dynamic>> positions,
  ) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.background,
      builder: (_) => _PositionHistorySheet(
        positions: positions,
        money: _money,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }

        if (snapshot.hasError || snapshot.data == null) {
          return AppEmptyState(
            icon: Icons.insights_outlined,
            title: 'Paper 성과를 불러오지 못했어요',
            description: snapshot.error?.toString() ?? '잠시 후 다시 시도해 주세요.',
          );
        }

        final data = snapshot.data!;
        final combined =
            (data['combined'] as Map?)?.cast<String, dynamic>() ??
                <String, dynamic>{};
        final accounts =
            (data['accounts'] as Map?)?.cast<String, dynamic>() ??
                <String, dynamic>{};
        final positions = (data['positions'] as List<dynamic>? ??
                <dynamic>[])
            .map((item) => (item as Map).cast<String, dynamic>())
            .toList();
        final trading =
            (data['trading_7d'] as Map?)?.cast<String, dynamic>() ??
                <String, dynamic>{};
        final recentOrders = (data['recent_orders'] as List<dynamic>? ??
                <dynamic>[])
            .map((item) => (item as Map).cast<String, dynamic>())
            .toList();
        final scorePerformance =
            (data['score_performance_7d'] as List<dynamic>? ??
                    <dynamic>[])
                .map((item) => (item as Map).cast<String, dynamic>())
                .toList();
        final candidatePerformance =
            (data['candidate_score_performance_7d'] as List<dynamic>? ??
                    <dynamic>[])
                .map((item) => (item as Map).cast<String, dynamic>())
                .toList();

        final equity = _number(combined['equity']);
        final cash = _number(combined['cash']);
        final invested = _number(combined['invested']);
        final cumulative = _number(combined['cumulative_return_pct']);
        final dailyPnl = _number(combined['daily_pnl']);
        final dailyPnlPct = _number(combined['daily_pnl_pct']);
        final mdd = combined['max_drawdown_7d_pct'];
        final orders =
            (combined['daily_order_count'] as num?)?.toInt() ?? 0;
        final positionCount =
            (combined['position_count'] as num?)?.toInt() ?? 0;

        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
            children: [
              AppSurface(
                emphasized: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Paper 총자산',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${_money.format(equity)}원',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '누적 ${_signedPct(cumulative)}',
                      style: TextStyle(
                        color: _pnlColor(cumulative),
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 20),
                    Row(
                      children: [
                        Expanded(
                          child: _Metric(
                            label: '현금',
                            value: '${_money.format(cash)}원',
                          ),
                        ),
                        Expanded(
                          child: _Metric(
                            label: '투자중',
                            value: '${_money.format(invested)}원',
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        Expanded(
                          child: _Metric(
                            label: '오늘 손익',
                            value: _signedMoney(dailyPnl),
                            valueColor: _pnlColor(dailyPnl),
                            subValue: _signedPct(dailyPnlPct),
                          ),
                        ),
                        Expanded(
                          child: _Metric(
                            label: '7일 MDD',
                            value: mdd == null
                                ? '-'
                                : '${_number(mdd).toStringAsFixed(2)}%',
                            valueColor: mdd == null
                                ? null
                                : _pnlColor(_number(mdd)),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        Expanded(
                          child: _Metric(
                            label: '오늘 주문',
                            value: '$orders회',
                          ),
                        ),
                        Expanded(
                          child: _Metric(
                            label: '보유 종목',
                            value: '$positionCount개',
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              const SectionTitle('계좌별 성과'),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _AccountCard(
                      title: '주식',
                      data: (accounts['stock'] as Map?)
                              ?.cast<String, dynamic>() ??
                          <String, dynamic>{},
                      money: _money,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _AccountCard(
                      title: '코인',
                      data: (accounts['crypto'] as Map?)
                              ?.cast<String, dynamic>() ??
                          <String, dynamic>{},
                      money: _money,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              const SectionTitle('최근 7일 매매 성과'),
              const SizedBox(height: 12),
              AppSurface(
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _Metric(
                            label: '매도 승률',
                            value:
                                '${_number(trading['win_rate_pct']).toStringAsFixed(1)}%',
                          ),
                        ),
                        Expanded(
                          child: _Metric(
                            label: '실현손익',
                            value: _signedMoney(trading['realized_pnl']),
                            valueColor:
                                _pnlColor(_number(trading['realized_pnl'])),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        Expanded(
                          child: _Metric(
                            label: '익절',
                            value: '${trading['win_count'] ?? 0}회',
                          ),
                        ),
                        Expanded(
                          child: _Metric(
                            label: '손절',
                            value: '${trading['loss_count'] ?? 0}회',
                          ),
                        ),
                        Expanded(
                          child: _Metric(
                            label: '체결',
                            value: '${trading['order_count'] ?? 0}회',
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      '승률은 실현손익이 기록된 매도 체결 기준이에요.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              const SectionTitle('BUY 점수별 성과'),
              const SizedBox(height: 12),
              if (scorePerformance.isEmpty)
                const AppSurface(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: Text(
                      '점수별 성과 데이터가 아직 없어요.',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                  ),
                )
              else
                ...scorePerformance.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _ScorePerformanceCard(data: item),
                  ),
                ),
              const SizedBox(height: 8),
              Text(
                '매수 당시 점수와 이후 매도 실현성과를 연결한 최근 7일 통계예요.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 24),
              const SectionTitle('주식 후보점수별 성과'),
              const SizedBox(height: 12),
              if (candidatePerformance.every(
                (item) => (item['closed_trades'] as num? ?? 0) == 0,
              ))
                const AppSurface(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: Text(
                      '후보점수와 연결된 청산 데이터가 아직 없어요.',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                  ),
                )
              else
                ...candidatePerformance.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _CandidatePerformanceCard(data: item),
                  ),
                ),
              const SizedBox(height: 8),
              Text(
                '주식 자동선정 당시 후보점수와 이후 매도 실현성과를 연결한 최근 7일 통계예요.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 24),
              SectionTitle(
                '최근 체결',
                trailing: Text(
                  '${recentOrders.length}건',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              const SizedBox(height: 12),
              if (recentOrders.isEmpty)
                const AppSurface(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: Text(
                      '새 주문 원장에 기록된 체결이 아직 없어요.',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                  ),
                )
              else ...[
                ...recentOrders.take(5).map(
                  (order) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _OrderCard(
                      data: order,
                      money: _money,
                      onTap: () => _showOrderDecision(context, order),
                    ),
                  ),
                ),
                if (recentOrders.length > 5)
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: () => _showOrdersSheet(context, recentOrders),
                      icon: const Icon(Icons.keyboard_arrow_up_rounded),
                      label: const Text('최근 체결 더보기'),
                    ),
                  ),
              ],
              const SizedBox(height: 24),
              SectionTitle(
                '보유 종목',
                trailing: Text(
                  '${positions.length}개',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              const SizedBox(height: 12),
              if (positions.isEmpty)
                const AppSurface(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 18),
                    child: Text(
                      '아직 보유 중인 Paper 포지션이 없어요.',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                  ),
                )
              else ...[
                ...positions.take(5).map(
                  (position) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _PositionCard(
                      data: position,
                      money: _money,
                    ),
                  ),
                ),
                if (positions.length > 5)
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: () => _showPositionsSheet(context, positions),
                      icon: const Icon(Icons.keyboard_arrow_up_rounded),
                      label: const Text('보유 종목 더보기'),
                    ),
                  ),
              ],
            ],
          ),
        );
      },
    );
  }
}


class _Metric extends StatelessWidget {
  const _Metric({
    required this.label,
    required this.value,
    this.valueColor,
    this.subValue,
  });

  final String label;
  final String value;
  final Color? valueColor;
  final String? subValue;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 5),
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: valueColor,
              ),
        ),
        if (subValue != null) ...[
          const SizedBox(height: 2),
          Text(
            subValue!,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: valueColor ?? AppColors.textSecondary,
                ),
          ),
        ],
      ],
    );
  }
}


class _AccountCard extends StatelessWidget {
  const _AccountCard({
    required this.title,
    required this.data,
    required this.money,
  });

  final String title;
  final Map<String, dynamic> data;
  final NumberFormat money;

  num _number(dynamic value) =>
      num.tryParse(value?.toString() ?? '0') ?? 0;

  @override
  Widget build(BuildContext context) {
    final equity = _number(data['equity']);
    final cumulative = _number(data['cumulative_return_pct']);
    final positions = (data['position_count'] as num?)?.toInt() ?? 0;
    final color = cumulative > 0
        ? AppColors.positive
        : cumulative < 0
            ? AppColors.negative
            : AppColors.textSecondary;
    final prefix = cumulative > 0 ? '+' : '';

    return AppSurface(
      padding: const EdgeInsets.all(15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 10),
          Text(
            '${money.format(equity)}원',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 4),
          Text(
            '$prefix${cumulative.toStringAsFixed(2)}%',
            style: TextStyle(
              color: color,
              fontSize: 13,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '보유 $positions개',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}


class _PositionCard extends StatelessWidget {
  const _PositionCard({
    required this.data,
    required this.money,
  });

  final Map<String, dynamic> data;
  final NumberFormat money;

  num _number(dynamic value) =>
      num.tryParse(value?.toString() ?? '0') ?? 0;

  @override
  Widget build(BuildContext context) {
    final returnRate = _number(data['return_rate']);
    final color = returnRate > 0
        ? AppColors.positive
        : returnRate < 0
            ? AppColors.negative
            : AppColors.textSecondary;
    final prefix = returnRate > 0 ? '+' : '';
    final name = data['name']?.toString() ?? '';
    final symbol = data['symbol']?.toString() ?? '';
    final market = data['market']?.toString() == 'stock' ? '주식' : '코인';
    final marketValue = _number(data['market_value']);
    final invested = _number(data['invested_amount']);
    final score = data['decision_score'];

    return AppSurface(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name.isEmpty ? symbol : name,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 3),
                Text(
                  '$market · $symbol',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                Text(
                  '평가 ${money.format(marketValue)}원 · 투자 ${money.format(invested)}원',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                if (score != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    '최근 판단점수 $score',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            '$prefix${returnRate.toStringAsFixed(2)}%',
            style: TextStyle(
              color: color,
              fontSize: 16,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}




class _OrderCard extends StatelessWidget {
  const _OrderCard({
    required this.data,
    required this.money,
    this.onTap,
  });

  final Map<String, dynamic> data;
  final NumberFormat money;
  final VoidCallback? onTap;

  num _number(dynamic value) =>
      num.tryParse(value?.toString() ?? '0') ?? 0;

  @override
  Widget build(BuildContext context) {
    final side = data['side']?.toString().toUpperCase() ?? '-';
    final symbol = data['symbol']?.toString() ?? '-';
    final market = data['market']?.toString() == 'stock' ? '주식' : '코인';
    final notional = _number(data['notional']);
    final realizedRaw = data['realized_pnl'];
    final realized = realizedRaw == null ? null : _number(realizedRaw);
    final sideColor =
        side == 'BUY' ? AppColors.primary : AppColors.negative;

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: AppSurface(
        padding: const EdgeInsets.all(15),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '$symbol · $side',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: sideColor,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '$market · ${money.format(notional)}원',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            if (realized != null)
              Text(
                '${realized > 0 ? '+' : ''}${money.format(realized)}원',
                style: TextStyle(
                  color: realized > 0
                      ? AppColors.positive
                      : realized < 0
                          ? AppColors.negative
                          : AppColors.textSecondary,
                  fontWeight: FontWeight.w800,
                ),
              ),
          ],
        ),
      ),
    );
  }
}


class _OrderHistorySheet extends StatelessWidget {
  const _OrderHistorySheet({
    required this.orders,
    required this.money,
    required this.onOrderTap,
  });

  final List<Map<String, dynamic>> orders;
  final NumberFormat money;
  final ValueChanged<Map<String, dynamic>> onOrderTap;

  @override
  Widget build(BuildContext context) {
    final entries = <Object>[];
    String? lastDay;
    for (final order in orders) {
      final parsed = DateTime.tryParse(order['created_at']?.toString() ?? '');
      final day = parsed == null
          ? '날짜 미상'
          : DateFormat('yyyy.MM.dd').format(parsed.toLocal());
      if (day != lastDay) {
        entries.add(day);
        lastDay = day;
      }
      entries.add(order);
    }

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.82,
      minChildSize: 0.45,
      maxChildSize: 0.95,
      builder: (context, controller) => SafeArea(
        top: false,
        child: Column(
          children: [
            const SizedBox(height: 10),
            Container(
              width: 42,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.divider,
                borderRadius: BorderRadius.circular(999),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 18, 20, 10),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      '최근 체결',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  Text(
                    '${orders.length}건',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView.builder(
                controller: controller,
                padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
                itemCount: entries.length,
                itemBuilder: (context, index) {
                  final item = entries[index];
                  if (item is String) {
                    return Padding(
                      padding: const EdgeInsets.fromLTRB(2, 14, 2, 9),
                      child: Text(
                        item,
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                    );
                  }
                  final order = item as Map<String, dynamic>;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _OrderCard(
                      data: order,
                      money: money,
                      onTap: () => onOrderTap(order),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}


class _PositionHistorySheet extends StatelessWidget {
  const _PositionHistorySheet({
    required this.positions,
    required this.money,
  });

  final List<Map<String, dynamic>> positions;
  final NumberFormat money;

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.82,
      minChildSize: 0.45,
      maxChildSize: 0.95,
      builder: (context, controller) => SafeArea(
        top: false,
        child: Column(
          children: [
            const SizedBox(height: 10),
            Container(
              width: 42,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.divider,
                borderRadius: BorderRadius.circular(999),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 18, 20, 10),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      '보유 종목',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  Text(
                    '${positions.length}개',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView.separated(
                controller: controller,
                padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
                itemCount: positions.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, index) => _PositionCard(
                  data: positions[index],
                  money: money,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}


class _CandidatePerformanceCard extends StatelessWidget {
  const _CandidatePerformanceCard({required this.data});

  final Map<String, dynamic> data;

  num _number(dynamic value) =>
      num.tryParse(value?.toString() ?? '0') ?? 0;

  @override
  Widget build(BuildContext context) {
    final bucket = data['bucket']?.toString() ?? '-';
    final trades = (data['closed_trades'] as num?)?.toInt() ?? 0;
    final winRate = _number(data['win_rate_pct']);
    final avgReturn = _number(data['average_return_pct']);
    final pnl = _number(data['realized_pnl']);
    final sufficient = data['sample_sufficient'] == true;
    final avgColor = avgReturn > 0
        ? AppColors.positive
        : avgReturn < 0
            ? AppColors.negative
            : AppColors.textSecondary;

    return AppSurface(
      padding: const EdgeInsets.all(15),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '후보점수 $bucket',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 5),
                Text(
                  '청산 $trades회 · 승률 ${winRate.toStringAsFixed(1)}%',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 4),
                Text(
                  sufficient
                      ? '표본 충분'
                      : '표본 부족 · 10회 이상부터 해석 권장',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: sufficient
                            ? AppColors.positive
                            : AppColors.warning,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${avgReturn > 0 ? '+' : ''}${avgReturn.toStringAsFixed(2)}%',
                style: TextStyle(
                  color: avgColor,
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                '실현손익 ${pnl > 0 ? '+' : ''}${NumberFormat('#,###').format(pnl)}원',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ScorePerformanceCard extends StatelessWidget {
  const _ScorePerformanceCard({required this.data});

  final Map<String, dynamic> data;

  num _number(dynamic value) =>
      num.tryParse(value?.toString() ?? '0') ?? 0;

  @override
  Widget build(BuildContext context) {
    final bucket = data['bucket']?.toString() ?? '-';
    final trades = (data['closed_trades'] as num?)?.toInt() ?? 0;
    final winRate = _number(data['win_rate_pct']);
    final avgReturn = _number(data['average_return_pct']);
    final pnl = _number(data['realized_pnl']);
    final avgColor = avgReturn > 0
        ? AppColors.positive
        : avgReturn < 0
            ? AppColors.negative
            : AppColors.textSecondary;

    return AppSurface(
      padding: const EdgeInsets.all(15),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '점수 $bucket',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 5),
                Text(
                  '청산 $trades회 · 승률 ${winRate.toStringAsFixed(1)}%',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${avgReturn > 0 ? '+' : ''}${avgReturn.toStringAsFixed(2)}%',
                style: TextStyle(
                  color: avgColor,
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                '실현손익 ${pnl > 0 ? '+' : ''}${NumberFormat('#,###').format(pnl)}원',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
