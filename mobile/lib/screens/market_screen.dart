import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../services/api_client.dart';


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

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(name + ' ' + (isBuy ? '사기' : '팔기')),
          content: TextField(
            controller: controller,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              labelText: widget.isStock ? '수량' : '금액',
              suffixText: widget.isStock ? '주' : '원',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(isBuy ? '매수' : '매도'),
            ),
          ],
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
          content: Text(
            (isBuy ? '매수' : '매도') + ' 요청이 처리되었습니다.',
          ),
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
              children: [
                const SizedBox(height: 120),
                Center(child: Text(_title + ' 데이터를 불러오지 못했습니다.')),
                const SizedBox(height: 8),
                Center(child: Text(snapshot.error.toString())),
              ],
            );
          }

          final items = snapshot.data ?? <Map<String, dynamic>>[];
          if (items.isEmpty) {
            return ListView(
              children: [
                const SizedBox(height: 160),
                Center(child: Text('현재 보유한 ' + _title + ' 종목이 없습니다.')),
              ],
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.all(12),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final item = items[index];
              final invested = num.tryParse(
                    item['invested_amount']?.toString() ?? '0',
                  ) ??
                  0;
              final quantity = item['quantity']?.toString() ?? '0';
              final returnRate = item['return_rate']?.toString() ?? '0';
              final score = item['decision_score']?.toString() ?? '-';

              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item['name']?.toString() ??
                            item['symbol']?.toString() ??
                            '-',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 10),
                      Text('투자금: ' + money.format(invested) + '원'),
                      Text(
                        widget.isStock
                            ? '보유: ' + quantity + '주'
                            : '보유 수량: ' + quantity,
                      ),
                      Text('이익률: ' + returnRate + '%'),
                      Text('판단점수: ' + score),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: FilledButton(
                              onPressed: () => _openOrder(item, 'buy'),
                              child: const Text('사기'),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () => _openOrder(item, 'sell'),
                              child: const Text('팔기'),
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
    );
  }
}
