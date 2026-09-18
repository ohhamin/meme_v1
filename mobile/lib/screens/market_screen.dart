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
  int? _upbitUniverseCount;
  int? _tossUniverseCount;

  String get _market => widget.isStock ? 'stocks' : 'crypto';
  String get _title => widget.isStock ? '주식' : '코인';

  @override
  void initState() {
    super.initState();
    _reload();
    if (widget.isStock) {
      _loadTossUniverseCount();
    } else {
      _loadUniverseCount();
    }
  }

  void _reload() {
    _future = ApiClient.instance.getPositions(_market);
  }

  Future<void> _loadUniverseCount() async {
    try {
      final markets = await ApiClient.instance.getUpbitUniverse();
      if (!mounted) return;
      setState(() => _upbitUniverseCount = markets.length);
    } catch (_) {
      // Positions should still be usable even when universe loading fails.
    }
  }

  Future<void> _loadTossUniverseCount() async {
    try {
      final symbols = await ApiClient.instance.getTossUniverse();
      if (!mounted) return;
      setState(() => _tossUniverseCount = symbols.length);
    } catch (_) {
      // Positions should still be usable even when universe loading fails.
    }
  }

  Future<void> _refresh() async {
    setState(_reload);
    await _future;
    if (widget.isStock) {
      await _loadTossUniverseCount();
    } else {
      await _loadUniverseCount();
    }
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

  Future<void> _openTossUniverse() async {
    try {
      final current = await ApiClient.instance.getTossUniverse();
      if (!mounted) return;

      final controller = TextEditingController(
        text: current.join(', '),
      );

      final saved = await showModalBottomSheet<bool>(
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
                borderRadius: BorderRadius.vertical(
                  top: Radius.circular(26),
                ),
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
                      '주식 판단 대상',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '국내주식 6자리 종목코드를 쉼표로 입력해 주세요. '
                      '판단 대상 수와 실제 보유 0~10종목은 별개예요.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: AppColors.textSecondary,
                          ),
                    ),
                    const SizedBox(height: 18),
                    TextField(
                      controller: controller,
                      autofocus: true,
                      minLines: 2,
                      maxLines: 4,
                      decoration: const InputDecoration(
                        hintText: '005930, 000660',
                        labelText: '종목코드',
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
                            onPressed: () async {
                              final values = controller.text
                                  .split(RegExp(r'[,\s]+'))
                                  .map((value) => value.trim())
                                  .where((value) => value.isNotEmpty)
                                  .toSet()
                                  .toList();

                              final invalid = values.where(
                                (value) =>
                                    value.length != 6 ||
                                    int.tryParse(value) == null,
                              );

                              if (invalid.isNotEmpty) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text(
                                      '국내주식 종목코드는 6자리 숫자로 입력해 주세요.',
                                    ),
                                  ),
                                );
                                return;
                              }

                              try {
                                final result = await ApiClient.instance
                                    .updateTossUniverse(values);
                                if (!context.mounted) return;
                                Navigator.pop(context, true);
                                if (mounted) {
                                  setState(() {
                                    _tossUniverseCount = result.length;
                                  });
                                }
                              } catch (e) {
                                if (!context.mounted) return;
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text(e.toString())),
                                );
                              }
                            },
                            child: const Text('저장'),
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

      controller.dispose();

      if (saved == true && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('주식 판단 대상을 저장했어요.')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _openUpbitUniverse() async {
    try {
      final results = await Future.wait([
        ApiClient.instance.getUpbitMarkets(),
        ApiClient.instance.getUpbitUniverse(),
      ]);

      if (!mounted) return;

      final allMarkets =
          (results[0] as List<Map<String, dynamic>>);
      final selected = <String>{
        ...(results[1] as List<String>),
      };
      final searchController = TextEditingController();

      final saved = await showModalBottomSheet<bool>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) {
          return StatefulBuilder(
            builder: (context, setSheetState) {
              final query = searchController.text.trim().toLowerCase();
              final filtered = allMarkets.where((item) {
                if (query.isEmpty) return true;
                final market =
                    item['market']?.toString().toLowerCase() ?? '';
                final korean =
                    item['korean_name']?.toString().toLowerCase() ?? '';
                final english =
                    item['english_name']?.toString().toLowerCase() ?? '';
                return market.contains(query) ||
                    korean.contains(query) ||
                    english.contains(query);
              }).toList();

              return Container(
                height: MediaQuery.of(context).size.height * 0.84,
                decoration: const BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.vertical(
                    top: Radius.circular(26),
                  ),
                ),
                child: SafeArea(
                  top: false,
                  child: Column(
                    children: [
                      const SizedBox(height: 10),
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
                      Padding(
                        padding: const EdgeInsets.fromLTRB(20, 18, 20, 12),
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '코인 판단 대상',
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleLarge,
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    '선택 ${selected.length}개 · 보유 종목 수 0~10개와는 별개예요.',
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodySmall,
                                  ),
                                ],
                              ),
                            ),
                            TextButton(
                              onPressed: () {
                                setSheetState(selected.clear);
                              },
                              child: const Text('전체 해제'),
                            ),
                          ],
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: TextField(
                          controller: searchController,
                          onChanged: (_) => setSheetState(() {}),
                          decoration: const InputDecoration(
                            hintText: '비트코인, BTC, KRW-BTC 검색',
                            prefixIcon: Icon(Icons.search_rounded),
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Expanded(
                        child: ListView.builder(
                          itemCount: filtered.length,
                          itemBuilder: (context, index) {
                            final item = filtered[index];
                            final market =
                                item['market']?.toString() ?? '';
                            final korean =
                                item['korean_name']?.toString() ?? market;
                            final warning = item['warning'] == true;
                            final caution = item['caution'] == true;
                            final checked = selected.contains(market);

                            return CheckboxListTile(
                              value: checked,
                              onChanged: (value) {
                                setSheetState(() {
                                  if (value == true) {
                                    selected.add(market);
                                  } else {
                                    selected.remove(market);
                                  }
                                });
                              },
                              controlAffinity:
                                  ListTileControlAffinity.trailing,
                              title: Row(
                                children: [
                                  Flexible(
                                    child: Text(
                                      korean,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  if (warning || caution) ...[
                                    const SizedBox(width: 8),
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 7,
                                        vertical: 3,
                                      ),
                                      decoration: BoxDecoration(
                                        color: AppColors.negativeSoft,
                                        borderRadius:
                                            BorderRadius.circular(999),
                                      ),
                                      child: const Text(
                                        '주의',
                                        style: TextStyle(
                                          color: AppColors.negative,
                                          fontSize: 10,
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                              subtitle: Text(market),
                            );
                          },
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(20, 10, 20, 20),
                        child: SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: () async {
                              try {
                                final savedMarkets =
                                    await ApiClient.instance
                                        .updateUpbitUniverse(
                                  selected.toList(),
                                );
                                if (!context.mounted) return;
                                Navigator.pop(context, true);
                                if (mounted) {
                                  setState(() {
                                    _upbitUniverseCount =
                                        savedMarkets.length;
                                  });
                                }
                              } catch (e) {
                                if (!context.mounted) return;
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text(e.toString())),
                                );
                              }
                            },
                            child: Text(
                              selected.isEmpty
                                  ? '판단 대상 없이 저장'
                                  : '${selected.length}개 저장',
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      );

      searchController.dispose();

      if (saved == true && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('코인 판단 대상을 저장했어요.')),
        );
      }
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
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
              children: [
                _UniverseBanner(
                  count: widget.isStock
                      ? _tossUniverseCount
                      : _upbitUniverseCount,
                  isStock: widget.isStock,
                  onManage: widget.isStock
                      ? _openTossUniverse
                      : _openUpbitUniverse,
                ),
                const SizedBox(height: 90),
                AppEmptyState(
                  icon: widget.isStock
                      ? Icons.show_chart_rounded
                      : Icons.currency_bitcoin_rounded,
                  title: '아직 보유한 ' + _title + '이 없어요',
                  description: widget.isStock
                      ? 'Toss 연동 또는 Paper 매매가 시작되면 여기에 표시됩니다.'
                      : '판단 대상은 있어도 보유 종목이 0개일 수 있어요. 현금 100%도 정상 상태입니다.',
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
              _UniverseBanner(
                count: widget.isStock
                    ? _tossUniverseCount
                    : _upbitUniverseCount,
                isStock: widget.isStock,
                onManage: widget.isStock
                    ? _openTossUniverse
                    : _openUpbitUniverse,
              ),
              const SizedBox(height: 12),
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


class _UniverseBanner extends StatelessWidget {
  const _UniverseBanner({
    required this.count,
    required this.isStock,
    required this.onManage,
  });

  final int? count;
  final bool isStock;
  final VoidCallback onManage;

  @override
  Widget build(BuildContext context) {
    return AppSurface(
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppColors.primarySoft,
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(
              Icons.radar_rounded,
              color: AppColors.primary,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'AI 판단 대상',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 3),
                Text(
                  count == null
                      ? '불러오는 중'
                      : count == 0
                          ? '선택 없음 · 자동 판단은 대기'
                          : isStock
                              ? '$count개 주식을 현재가 기준으로 판단'
                              : '$count개 코인을 현재가 기준으로 판단',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          TextButton(
            onPressed: onManage,
            child: const Text('관리'),
          ),
        ],
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
