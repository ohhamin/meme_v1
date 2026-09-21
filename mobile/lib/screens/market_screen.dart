import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../utils/decision_text.dart';
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
  late Future<Map<String, dynamic>> _performanceFuture;
  int? _upbitUniverseCount;
  int? _tossUniverseCount;
  bool _refreshingPositions = false;

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
    _performanceFuture = ApiClient.instance.getMarketPerformance(_market);
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
    if (_refreshingPositions) return;
    setState(() => _refreshingPositions = true);
    try {
      await ApiClient.instance.refreshPositions(_market);
      if (!mounted) return;
      setState(_reload);
      await _future;
      if (widget.isStock) {
        await _loadTossUniverseCount();
      } else {
        await _loadUniverseCount();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('현재 시세 새로고침 실패: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _refreshingPositions = false);
      }
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
    final currentPrice =
        num.tryParse(position['current_price']?.toString() ?? '0') ?? 0;
    final money = NumberFormat('#,###');

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
                    currentPrice > 0
                        ? '현재가 약 ${money.format(currentPrice)}원'
                        : (isBuy ? '얼마나 살까요?' : '얼마나 팔까요?'),
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
                      labelText: widget.isStock ? '주문 수량' : '주문 금액',
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
                          child: const Text('주문 확인'),
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
      controller.dispose();
      return;
    }

    try {
      int? stockQuantity;
      num? cryptoAmount;
      String orderSummary;

      if (widget.isStock) {
        stockQuantity = int.tryParse(controller.text.trim());
        if (stockQuantity == null || stockQuantity <= 0) {
          throw Exception('1주 이상의 수량을 입력해 주세요.');
        }
        final estimated =
            currentPrice > 0 ? currentPrice * stockQuantity : null;
        orderSummary = estimated == null
            ? '$stockQuantity주'
            : '$stockQuantity주 · 약 ${money.format(estimated)}원';
      } else {
        cryptoAmount =
            num.tryParse(controller.text.replaceAll(',', '').trim());
        if (cryptoAmount == null || cryptoAmount <= 0) {
          throw Exception('0원보다 큰 금액을 입력해 주세요.');
        }
        orderSummary = '${money.format(cryptoAmount)}원';
      }

      final settings = await ApiClient.instance.getSettings();
      final isLive = settings['mode'] == 'live';

      if (isLive && mounted) {
        final finalConfirmed = await showDialog<bool>(
          context: context,
          builder: (context) {
            return AlertDialog(
              title: const Text('실제 주문을 제출할까요?'),
              content: Text(
                '$name\n'
                '${isBuy ? '매수' : '매도'} · $orderSummary\n\n'
                'Live mode에서는 실제 계좌에 주문이 제출될 수 있어요.',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: const Text('실제 주문 제출'),
                ),
              ],
            );
          },
        );
        if (finalConfirmed != true) return;
      }

      if (widget.isStock) {
        await ApiClient.instance.manualStockOrder(
          symbol: symbol,
          side: side,
          quantity: stockQuantity!,
        );
      } else {
        await ApiClient.instance.manualCryptoOrder(
          symbol: symbol,
          side: side,
          amountKrw: cryptoAmount!,
        );
      }

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            (isLive ? 'Live ' : 'Paper ') +
                (isBuy ? '매수' : '매도') +
                ' 요청을 처리했어요.',
          ),
        ),
      );
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    } finally {
      controller.dispose();
    }
  }

  Future<void> _openTossUniverse() async {
    try {
      final current = await ApiClient.instance.getTossUniverse();
      final results = await Future.wait([
        ApiClient.instance.getTossUniverseStatus(),
        ApiClient.instance.getTossStocks(current),
      ]);
      if (!mounted) return;

      final status =
          (results[0] as Map).cast<String, dynamic>();
      var currentStocks =
          (results[1] as List<Map<String, dynamic>>);
      final controller = TextEditingController(
        text: current.join(', '),
      );
      var selectionMode =
          status['selection_mode']?.toString() ?? 'manual';
      var ranking = (status['ranking'] as List<dynamic>? ?? <dynamic>[])
          .whereType<Map>()
          .map((item) => item.cast<String, dynamic>())
          .where((item) => item['selected'] == true)
          .toList();
      var refreshedAt = status['refreshed_at']?.toString();
      var autoRunning = false;

      final saved = await showModalBottomSheet<bool>(
        context: context,
        isScrollControlled: true,
        // Keep this stateful sheet alive until its own buttons close it.
        // Dismissing it with a downward drag while async auto-selection is
        // rebuilding the sheet can dispose inherited dependencies mid-frame.
        enableDrag: false,
        isDismissible: false,
        backgroundColor: Colors.transparent,
        builder: (context) {
          final bottomInset = MediaQuery.of(context).viewInsets.bottom;
          return StatefulBuilder(
            builder: (context, setSheetState) {
              return Padding(
                padding: EdgeInsets.only(bottom: bottomInset),
                child: Container(
                  constraints: BoxConstraints(
                    maxHeight: MediaQuery.of(context).size.height * 0.88,
                  ),
                  decoration: const BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.vertical(
                      top: Radius.circular(26),
                    ),
                  ),
                  padding: const EdgeInsets.fromLTRB(22, 12, 22, 24),
                  child: SafeArea(
                    top: false,
                    child: SingleChildScrollView(
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
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                '주식 판단 대상',
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 5,
                              ),
                              decoration: BoxDecoration(
                                color: selectionMode == 'auto'
                                    ? AppColors.primarySoft
                                    : AppColors.chip,
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: Text(
                                selectionMode == 'auto' ? '자동선정' : '수동',
                                style: TextStyle(
                                  color: selectionMode == 'auto'
                                      ? AppColors.primary
                                      : AppColors.textSecondary,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          selectionMode == 'auto'
                              ? '유동성·추세·거래활성도·변동성을 합산해 최대 15개 후보를 자동 갱신해요.'
                              : '국내주식 6자리 종목코드를 직접 입력할 수 있어요.',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: AppColors.textSecondary,
                              ),
                        ),
                        const SizedBox(height: 16),
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            onPressed: autoRunning
                                ? null
                                : () async {
                                    setSheetState(() => autoRunning = true);
                                    try {
                                      final symbols = await ApiClient.instance
                                          .autoSelectTossUniverse(limit: 15);
                                      controller.text = symbols.join(', ');
                                      selectionMode = 'auto';
                                      final latest = await ApiClient.instance
                                          .getTossUniverseStatus();
                                      ranking = (latest['ranking']
                                                  as List<dynamic>? ??
                                              <dynamic>[])
                                          .whereType<Map>()
                                          .map(
                                            (item) =>
                                                item.cast<String, dynamic>(),
                                          )
                                          .where(
                                            (item) =>
                                                item['selected'] == true,
                                          )
                                          .toList();
                                      currentStocks = ranking
                                          .map(
                                            (item) => <String, dynamic>{
                                              'symbol': item['symbol'],
                                              'name': item['name'],
                                            },
                                          )
                                          .toList();
                                      refreshedAt =
                                          latest['refreshed_at']?.toString();
                                      if (mounted) {
                                        setState(() {
                                          _tossUniverseCount = symbols.length;
                                        });
                                      }
                                      setSheetState(() {});
                                      if (context.mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(
                                            content: Text(
                                              '자동으로 ${symbols.length}개 후보를 선정했어요.',
                                            ),
                                          ),
                                        );
                                      }
                                    } catch (e) {
                                      if (context.mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(content: Text(e.toString())),
                                        );
                                      }
                                    } finally {
                                      if (context.mounted) {
                                        setSheetState(() => autoRunning = false);
                                      }
                                    }
                                  },
                            icon: autoRunning
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Icon(Icons.auto_awesome_rounded),
                            label: Text(
                              autoRunning
                                  ? '후보 분석 중...'
                                  : '알고리즘으로 15개 자동 선정',
                            ),
                          ),
                        ),
                        if (selectionMode == 'auto' && ranking.isNotEmpty) ...[
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  '자동선정 근거',
                                  style: Theme.of(context)
                                      .textTheme
                                      .titleMedium,
                                ),
                              ),
                              if (refreshedAt != null)
                                Text(
                                  _formatUniverseRefresh(refreshedAt!),
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '점수는 후보 풀 안에서의 상대점수예요. 높은 점수 자체가 매수 신호는 아닙니다.',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 10),
                          SizedBox(
                            height: 220,
                            child: ListView.separated(
                              itemCount: ranking.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 8),
                              itemBuilder: (context, index) {
                                return _StockUniverseRankCard(
                                  item: ranking[index],
                                );
                              },
                            ),
                          ),
                        ],
                        if (ranking.isNotEmpty) ...[
                          const SizedBox(height: 10),
                          SizedBox(
                            width: double.infinity,
                            child: TextButton.icon(
                              onPressed: () => _showStockRanking(ranking),
                              icon: const Icon(Icons.leaderboard_rounded),
                              label: const Text('자동선정 점수·근거 보기'),
                            ),
                          ),
                        ],
                        const SizedBox(height: 14),
                        Text(
                          '현재 판단 대상',
                          style: Theme.of(context).textTheme.titleSmall,
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: currentStocks.isEmpty
                              ? current
                                  .map(
                                    (symbol) => Chip(
                                      label: Text(symbol),
                                    ),
                                  )
                                  .toList()
                              : currentStocks
                                  .map(
                                    (item) => Chip(
                                      label: Text(
                                        item['name']?.toString() ??
                                            item['symbol']?.toString() ??
                                            '-',
                                      ),
                                    ),
                                  )
                                  .toList(),
                        ),
                        const SizedBox(height: 14),
                        TextField(
                          controller: controller,
                          autofocus: false,
                          minLines: 2,
                          maxLines: 4,
                          decoration: const InputDecoration(
                            hintText: '005930, 000660',
                            labelText: '수동 편집용 종목코드',
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '직접 저장하면 자동선정이 해제되고 수동 모드로 전환돼요.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: 18),
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () => Navigator.pop(context, false),
                                child: const Text('닫기'),
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
                                child: const Text('수동 저장'),
                              ),
                            ),
                          ],
                        ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            },
          );
        },
      );

      controller.dispose();

      if (saved == true && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('주식 판단 대상을 수동 저장했어요.')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }
  String _formatUniverseRefresh(String raw) {
    try {
      final dt = DateTime.parse(raw).toLocal();
      return DateFormat('MM/dd HH:mm').format(dt);
    } catch (_) {
      return raw;
    }
  }

  Future<void> _showStockRanking(
    List<Map<String, dynamic>> ranking,
  ) async {
    final selected = ranking
        .where((item) => item['selected'] == true)
        .toList();

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          height: MediaQuery.of(context).size.height * 0.82,
          decoration: const BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
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
                  padding: const EdgeInsets.fromLTRB(20, 18, 20, 10),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          '자동선정 Top ${selected.length}',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ),
                      Text(
                        '후보 점수 ≠ 매수 점수',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 20),
                  child: Text(
                    '유동성 35% · 60일 상승빈도 25% · 20일 상승빈도 20% · '
                    '안정성 10% · 20일 수익흐름 5% · 거래활성 5%',
                  ),
                ),
                const SizedBox(height: 10),
                Expanded(
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(20, 6, 20, 28),
                    itemCount: selected.length,
                    separatorBuilder: (_, __) =>
                        const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final item = selected[index];
                      final score =
                          num.tryParse(item['score']?.toString() ?? '0') ?? 0;
                      final turnover = num.tryParse(
                            item['avg_turnover_20d']?.toString() ?? '0',
                          ) ??
                          0;
                      final return5 = num.tryParse(
                            item['return_5d_pct']?.toString() ?? '0',
                          ) ??
                          0;
                      final return20 = num.tryParse(
                            item['return_20d_pct']?.toString() ?? '0',
                          ) ??
                          0;
                      final return60 = num.tryParse(
                            item['return_60d_pct']?.toString() ?? '0',
                          ) ??
                          0;
                      final volatility = num.tryParse(
                            item['volatility_20d_pct']?.toString() ?? '0',
                          ) ??
                          0;
                      final penalty =
                          num.tryParse(item['penalty']?.toString() ?? '0') ?? 0;
                      final reasons = (
                        item['penalty_reasons'] as List<dynamic>? ??
                            <dynamic>[]
                      ).map((value) => value.toString()).toList();
                      final money = NumberFormat.compact(locale: 'ko_KR');

                      return AppSurface(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Container(
                                  width: 28,
                                  height: 28,
                                  alignment: Alignment.center,
                                  decoration: BoxDecoration(
                                    color: AppColors.primarySoft,
                                    borderRadius: BorderRadius.circular(9),
                                  ),
                                  child: Text(
                                    '${item['rank'] ?? index + 1}',
                                    style: const TextStyle(
                                      color: AppColors.primary,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        item['name']?.toString() ??
                                            item['symbol']?.toString() ??
                                            '-',
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleMedium,
                                      ),
                                      Text(
                                        item['symbol']?.toString() ?? '',
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodySmall,
                                      ),
                                    ],
                                  ),
                                ),
                                Text(
                                  score.toStringAsFixed(1),
                                  style: Theme.of(context)
                                      .textTheme
                                      .titleLarge
                                      ?.copyWith(color: AppColors.primary),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                _SelectorMetric(
                                  label: '유동성',
                                  value: item['liquidity_score'],
                                ),
                                _SelectorMetric(
                                  label: '60일상승빈도',
                                  value: item['sign_60d_score'],
                                ),
                                _SelectorMetric(
                                  label: '20일상승빈도',
                                  value: item['sign_20d_score'],
                                ),
                                _SelectorMetric(
                                  label: '거래활성',
                                  value: item['activity_score'],
                                ),
                                _SelectorMetric(
                                  label: '안정성',
                                  value: item['stability_score'],
                                ),
                              ],
                            ),
                            const Divider(height: 24),
                            Text(
                              '20일 평균 거래대금 ${money.format(turnover)}원'
                              ' · 5일 ${return5 >= 0 ? '+' : ''}${return5.toStringAsFixed(1)}%'
                              ' · 20일 ${return20 >= 0 ? '+' : ''}${return20.toStringAsFixed(1)}%'
                              ' · 60일 ${return60 >= 0 ? '+' : ''}${return60.toStringAsFixed(1)}%'
                              ' · 변동성 ${volatility.toStringAsFixed(1)}%',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                            if (penalty > 0) ...[
                              const SizedBox(height: 8),
                              Text(
                                '감점 -${penalty.toStringAsFixed(0)}'
                                '${reasons.isEmpty ? '' : ' · ${reasons.join(' · ')}'}',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(color: AppColors.warning),
                              ),
                            ],
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
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
      var autoRunning = false;

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
                        child: SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            onPressed: autoRunning
                                ? null
                                : () async {
                                    setSheetState(() => autoRunning = true);
                                    try {
                                      final markets = await ApiClient.instance
                                          .autoSelectUpbitUniverse(limit: 10);
                                      if (!context.mounted) return;
                                      setSheetState(() {
                                        selected
                                          ..clear()
                                          ..addAll(markets);
                                        autoRunning = false;
                                      });
                                      if (mounted) {
                                        setState(() {
                                          _upbitUniverseCount = markets.length;
                                        });
                                      }
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(
                                          content: Text(
                                            '거래대금 기준으로 ${markets.length}개 코인을 자동 선정했어요.',
                                          ),
                                        ),
                                      );
                                    } catch (e) {
                                      if (!context.mounted) return;
                                      setSheetState(() => autoRunning = false);
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text(e.toString())),
                                      );
                                    }
                                  },
                            icon: autoRunning
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Icon(Icons.auto_awesome_rounded),
                            label: Text(
                              autoRunning
                                  ? '후보 분석 중...'
                                  : '거래대금 기준 10개 자동 선정',
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
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
                                  ? '판단 대상 없이 수동 저장'
                                  : '${selected.length}개 수동 저장',
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

  Future<void> _showLatestPositionDecision(
    Map<String, dynamic> position,
  ) async {
    final symbol = position['symbol']?.toString() ?? '';
    final action =
        position['decision_action']?.toString().toUpperCase() ?? 'HOLD';
    final score = position['decision_score']?.toString() ?? '-';
    final reason = position['decision_reason']?.toString().trim() ?? '';
    final risk = position['decision_risk']?.toString() ?? '';
    final blockReason =
        position['decision_block_reason']?.toString().trim() ?? '';
    final time = position['decision_time']?.toString() ?? '-';
    final name = position['name']?.toString() ?? symbol;

    if (position['decision_action'] == null &&
        position['decision_reason'] == null &&
        position['decision_time'] == null) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('이 종목의 최근 판단 기록을 찾지 못했어요.'),
        ),
      );
      return;
    }

    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('$name · $action'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                time,
                style: Theme.of(dialogContext).textTheme.bodySmall,
              ),
              const SizedBox(height: 14),
              Text(
                '판단점수 $score',
                style: Theme.of(dialogContext).textTheme.titleMedium,
              ),
              if (risk.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  'Risk Guard · ${riskGuardLabel(risk)}',
                  style: Theme.of(dialogContext).textTheme.bodyMedium,
                ),
              ],
              const SizedBox(height: 12),
              Text(
                reason.isEmpty
                    ? '저장된 판단 근거가 없어요.'
                    : localizeDecisionReason(reason),
                style: Theme.of(dialogContext).textTheme.bodyMedium,
              ),
              if (blockReason.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  '차단 사유 · ${localizeDecisionReason(blockReason)}',
                  style: Theme.of(dialogContext).textTheme.bodySmall?.copyWith(
                        color: AppColors.negative,
                      ),
                ),
              ],
            ],
          ),
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
                _PerformanceSummary(
                  future: _performanceFuture,
                  isStock: widget.isStock,
                ),
                const SizedBox(height: 12),
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
              _PerformanceSummary(
                future: _performanceFuture,
                isStock: widget.isStock,
              ),
              const SizedBox(height: 12),
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
              Row(
                children: [
                  const Expanded(child: SectionTitle('보유 종목')),
                  IconButton(
                    tooltip: '현재 시세 새로고침',
                    onPressed: _refreshingPositions ? null : _refresh,
                    icon: _refreshingPositions
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.refresh_rounded),
                  ),
                ],
              ),
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
                    onDecisionTap: () => _showLatestPositionDecision(item),
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


class _SelectorMetric extends StatelessWidget {
  const _SelectorMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final dynamic value;

  @override
  Widget build(BuildContext context) {
    final score = num.tryParse(value?.toString() ?? '0') ?? 0;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.chip,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        '$label ${score.toStringAsFixed(0)}',
        style: Theme.of(context).textTheme.bodySmall,
      ),
    );
  }
}

class _PerformanceSummary extends StatelessWidget {
  const _PerformanceSummary({
    required this.future,
    required this.isStock,
  });

  final Future<Map<String, dynamic>> future;
  final bool isStock;

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat('#,###');
    return FutureBuilder<Map<String, dynamic>>(
      future: future,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const AppSurface(
            child: SizedBox(
              height: 74,
              child: Center(child: CircularProgressIndicator()),
            ),
          );
        }

        final data = snapshot.data!;
        final mode = data['mode']?.toString().toUpperCase() ?? '-';
        final returnPct =
            num.tryParse(data['return_pct']?.toString() ?? '0') ?? 0;
        final unrealized =
            num.tryParse(data['unrealized_pnl']?.toString() ?? '0') ?? 0;
        final realized =
            num.tryParse(data['realized_pnl_7d']?.toString() ?? '');
        final winRate =
            num.tryParse(data['win_rate_7d_pct']?.toString() ?? '');
        final returnColor = returnPct > 0
            ? AppColors.positive
            : returnPct < 0
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
                      '${isStock ? '주식' : '코인'} 성과 요약',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  Text(mode, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                '${returnPct >= 0 ? '+' : ''}${returnPct.toStringAsFixed(2)}%',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: returnColor,
                    ),
              ),
              const SizedBox(height: 5),
              Text(
                '평가손익 ${money.format(unrealized)}원 · 보유 ${data['position_count'] ?? 0}개',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              if (realized != null) ...[
                const SizedBox(height: 8),
                Text(
                  '최근 7일 실현손익 ${money.format(realized)}원'
                  '${winRate == null ? '' : ' · 승률 ${winRate.toStringAsFixed(1)}%'}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _StockUniverseRankCard extends StatelessWidget {
  const _StockUniverseRankCard({required this.item});

  final Map<String, dynamic> item;

  double _number(String key) =>
      double.tryParse(item[key]?.toString() ?? '0') ?? 0;

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.compact(locale: 'ko_KR');
    final score = _number('score');
    final penalty = _number('penalty');
    final reasons =
        (item['penalty_reasons'] as List<dynamic>? ?? <dynamic>[])
            .map((value) => value.toString())
            .toList();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SizedBox(
                width: 28,
                child: Text(
                  '#${item['rank'] ?? '-'}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              Expanded(
                child: Text(
                  '${item['name'] ?? item['symbol']} · ${item['symbol'] ?? ''}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ),
              Text(
                score.toStringAsFixed(1),
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 9),
          Wrap(
            spacing: 10,
            runSpacing: 5,
            children: [
              _UniverseMetric(label: '유동성', value: _number('liquidity_score')),
              _UniverseMetric(label: '60일상승빈도', value: _number('sign_60d_score')),
              _UniverseMetric(label: '20일상승빈도', value: _number('sign_20d_score')),
              _UniverseMetric(label: '거래활성', value: _number('activity_score')),
              _UniverseMetric(label: '안정성', value: _number('stability_score')),
            ],
          ),
          const SizedBox(height: 7),
          Text(
            '20일 평균 거래대금 ${money.format(_number('avg_turnover_20d'))}원'
            ' · 5일 ${_number('return_5d_pct').toStringAsFixed(1)}%'
            ' · 20일 ${_number('return_20d_pct').toStringAsFixed(1)}%',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          if (penalty > 0) ...[
            const SizedBox(height: 5),
            Text(
              '감점 -${penalty.toStringAsFixed(0)}'
              '${reasons.isEmpty ? '' : ' · ${reasons.join(', ')}'}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.warning,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}

class _UniverseMetric extends StatelessWidget {
  const _UniverseMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final double value;

  @override
  Widget build(BuildContext context) {
    return Text(
      '$label ${value.toStringAsFixed(0)}',
      style: Theme.of(context).textTheme.bodySmall,
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
    required this.onDecisionTap,
  });

  final Map<String, dynamic> item;
  final bool isStock;
  final NumberFormat money;
  final VoidCallback onBuy;
  final VoidCallback onSell;
  final VoidCallback onDecisionTap;

  @override
  Widget build(BuildContext context) {
    final invested =
        num.tryParse(item['invested_amount']?.toString() ?? '0') ?? 0;
    final quantity = item['quantity']?.toString() ?? '0';
    final marketValue =
        num.tryParse(item['market_value']?.toString() ?? '0') ?? 0;
    final averagePrice =
        num.tryParse(item['average_price']?.toString() ?? '0') ?? 0;
    final currentPrice =
        num.tryParse(item['current_price']?.toString() ?? '0') ?? 0;
    final returnRate =
        num.tryParse(item['return_rate']?.toString() ?? '0') ?? 0;
    final priceFormat = NumberFormat('#,##0.########');
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
                InkWell(
                  borderRadius: BorderRadius.circular(999),
                  onTap: onDecisionTap,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
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
                  label: '현재 가치',
                  value: money.format(marketValue) + '원',
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
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _ValueBlock(
                  label: '평균매수가',
                  value: priceFormat.format(averagePrice) + '원',
                ),
              ),
              Expanded(
                child: _ValueBlock(
                  label: isStock ? '현재 주당가격' : '현재 코인가격',
                  value: priceFormat.format(currentPrice) + '원',
                ),
              ),
              Expanded(
                child: _ValueBlock(
                  label: '보유 수량',
                  value: isStock ? quantity + '주' : quantity,
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
