import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../widgets/app_surface.dart';


class MarketScreen extends StatefulWidget {
  const MarketScreen({
    super.key,
    required this.isStock,
  });

  final bool isStock;

  @override
  State<MarketScreen> createState() => _MarketScreenState();
}


class _MarketScreenState extends State<MarketScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  String get _market => widget.isStock ? 'stocks' : 'crypto';
  String get _title => widget.isStock ? '주식' : '코인';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = ApiClient.instance.getPositions(_market);
  }

  Future<void> _refresh() async {
    setState(_reload);
    await _future;
  }

  Future<void> _openOrder(
    Map<String, dynamic> position,
    String side,
  ) async {
    final controller = TextEditingController();
    final symbol = position['symbol']?.toString() ?? '';
    final name = position['name']?.toString() ?? symbol;
    final isBuy = side == 'buy';

    final confirmed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        final bottomInset = MediaQuery.of(context).viewInsets.bottom;
        return Padding(
          padding: EdgeInsets.only(bottom: bottomInset),
          child: Container(
            decoration: const BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
            ),
            padding: const EdgeInsets.fromLTRB(22, 12, 22, 24),
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
                    name,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    isBuy ? '얼마나 살까요?' : '얼마나 팔까요?',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                  ),
                  const SizedBox(height: 18),
                  TextField(
                    controller: controller,
                    autofocus: true,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: InputDecoration(
                      hintText: widget.isStock ? '예: 3' : '예: 100000',
                      suffixText: widget.isStock ? '주' : '원',
                    ),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.pop(context, false),
                          child: const Text('취소'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: FilledButton(
                          onPressed: () => Navigator.pop(context, true),
                          child: Text(isBuy ? '매수' : '매도'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    try {
      if (widget.isStock) {
        final quantity = int.tryParse(controller.text.trim());
        if (quantity == null || quantity <= 0) {
          throw Exception('1주 이상의 수량을 입력해 주세요.');
        }
        await ApiClient.instance.manualStockOrder(
          symbol: symbol,
          side: side,
          quantity: quantity,
        );
      } else {
        final amount = num.tryParse(controller.text.replaceAll(',', '').trim());
        if (amount == null || amount <= 0) {
          throw Exception('0원보다 큰 금액을 입력해 주세요.');
        }
        await ApiClient.instance.manualCryptoOrder(
          symbol: symbol,
          side: side,
          amountKrw: amount,
        );
      }

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text((isBuy ? '매수' : '매도') + ' 요청을 처리했어요.'),
        ),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat('#,###');

    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<Map<String, dynamic>>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return ListView(
              padding: const EdgeInsets.only(top: 120),
              children: [
                AppEmptyState(
                  icon: Icons.cloud_off_rounded,
                  title: _title + ' 데이터를 불러오지 못했어요',
                  description: '백엔드 연결 상태를 확인한 뒤 다시 당겨서 새로고침해 주세요.',
                ),
              ],
            );
          }

          final items = snapshot.data ?? <Map<String, dynamic>>[];
          if (items.isEmpty) {
            return ListView(
              padding: const EdgeInsets.only(top: 110),
              children: [
                AppEmptyState(
                  icon: widget.isStock
                      ? Icons.show_chart_rounded
                      : Icons.currency_bitcoin_rounded,
                  title: '아직 보유한 ' + _title + '이 없어요',
                  description: 'Broker 연결이 완료되면 보유 종목이 여기에 표시됩니다.',
                ),
              ],
            );
          }

          final totalInvested = items.fold<num>(
            0,
            (sum, item) =>
                sum +
                (num.tryParse(item['invested_amount']?.toString() ?? '0') ?? 0),
          );

          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
            children: [
              AppSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '총 투자금',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      money.format(totalInvested) + '원',
                      style:
                          Theme.of(context).textTheme.headlineMedium?.copyWith(
                                fontSize: 30,
                              ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '보유 종목 ' + items.length.toString() + '개',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: AppColors.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              const SectionTitle('보유 종목'),
              const SizedBox(height: 12),
              ...items.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _PositionCard(
                    item: item,
                    isStock: widget.isStock,
                    money: money,
                    onBuy: () => _openOrder(item, 'buy'),
                    onSell: () => _openOrder(item, 'sell'),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}


class _PositionCard extends StatelessWidget {
  const _PositionCard({
    required this.item,
    required this.isStock,
    required this.money,
    required this.onBuy,
    required this.onSell,
  });

  final Map<String, dynamic> item;
  final bool isStock;
  final NumberFormat money;
  final VoidCallback onBuy;
  final VoidCallback onSell;

  @override
  Widget build(BuildContext context) {
    final invested =
        num.tryParse(item['invested_amount']?.toString() ?? '0') ?? 0;
    final quantity = item['quantity']?.toString() ?? '0';
    final returnRate =
        num.tryParse(item['return_rate']?.toString() ?? '0') ?? 0;
    final score = int.tryParse(item['decision_score']?.toString() ?? '');

    final returnColor = returnRate > 0
        ? AppColors.positive
        : returnRate < 0
            ? AppColors.negative
            : AppColors.textSecondary;

    return AppSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  item['name']?.toString() ??
                      item['symbol']?.toString() ??
                      '-',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              if (score != null)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.primarySoft,
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    '판단 ' + score.toString(),
                    style: const TextStyle(
                      color: AppColors.primary,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: _ValueBlock(
                  label: '투자금',
                  value: money.format(invested) + '원',
                ),
              ),
              Expanded(
                child: _ValueBlock(
                  label: isStock ? '보유 수량' : '보유 코인',
                  value: isStock ? quantity + '주' : quantity,
                ),
              ),
              Expanded(
                child: _ValueBlock(
                  label: '수익률',
                  value: returnRate.toStringAsFixed(2) + '%',
                  valueColor: returnColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: onBuy,
                  child: const Text('사기'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton(
                  onPressed: onSell,
                  child: const Text('팔기'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}


class _ValueBlock extends StatelessWidget {
  const _ValueBlock({
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
        const SizedBox(height: 5),
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: valueColor ?? AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
        ),
      ],
    );
  }
}
