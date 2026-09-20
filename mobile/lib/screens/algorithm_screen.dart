import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../widgets/app_surface.dart';


class AlgorithmScreen extends StatefulWidget {
  const AlgorithmScreen({super.key});

  @override
  State<AlgorithmScreen> createState() => _AlgorithmScreenState();
}


class _AlgorithmScreenState extends State<AlgorithmScreen> {
  late Future<String> _current;
  late Future<List<Map<String, dynamic>>> _proposals;
  bool _reviewing = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _current = ApiClient.instance.getCurrentAlgorithm();
    _proposals = ApiClient.instance.getAlgorithmProposals();
  }

  Future<void> _reviewNow() async {
    if (_reviewing) return;
    setState(() => _reviewing = true);
    try {
      final result = await ApiClient.instance.reviewAlgorithmNow();
      if (!mounted) return;
      setState(_reload);
      final created = result['proposal_created'] == true;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            created
                ? '성과를 바탕으로 새 알고리즘 제안을 만들었어요.'
                : '검토를 마쳤지만 지금은 변경 제안이 필요하지 않아요.',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    } finally {
      if (mounted) {
        setState(() => _reviewing = false);
      }
    }
  }

  Future<void> _apply(String id) async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          padding: const EdgeInsets.fromLTRB(22, 12, 22, 24),
          decoration: const BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
          ),
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
                  '이 제안을 적용할까요?',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  '다음 판단부터 AI의 보수적 검토 규칙에 반영돼요. 수학 점수식과 Risk Guard는 코드 테스트를 거쳐 별도 버전으로 변경해요.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
                const SizedBox(height: 22),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: const Text('돌아가기'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: const Text('적용'),
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

    if (ok != true) return;

    try {
      await ApiClient.instance.applyAlgorithmProposal(id);
      if (!mounted) return;
      setState(_reload);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('알고리즘 제안을 적용했어요.')),
      );
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
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('제안을 취소했어요.')),
      );
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
      length: 3,
      child: Column(
        children: [
          Container(
            margin: const EdgeInsets.fromLTRB(20, 4, 20, 18),
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: AppColors.chip,
              borderRadius: BorderRadius.circular(16),
            ),
            child: TabBar(
              dividerColor: Colors.transparent,
              indicatorSize: TabBarIndicatorSize.tab,
              labelColor: AppColors.textPrimary,
              unselectedLabelColor: AppColors.textSecondary,
              labelStyle: const TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 14,
              ),
              unselectedLabelStyle: const TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 14,
              ),
              indicator: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(12),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x10000000),
                    blurRadius: 8,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              tabs: const [
                Tab(text: '현재'),
                Tab(text: '검증'),
                Tab(text: '제안'),
              ],
            ),
          ),
          Expanded(
            child: TabBarView(
              children: [
                _CurrentAlgorithm(future: _current),
                const _QuantValidationTab(),
                Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
                      child: SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: _reviewing ? null : _reviewNow,
                          icon: _reviewing
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.analytics_outlined),
                          label: Text(
                            _reviewing ? '성과 검토 중...' : 'AI 검토 규칙 개선안 보기',
                          ),
                        ),
                      ),
                    ),
                    Expanded(
                      child: _ProposalList(
                        future: _proposals,
                        onApply: _apply,
                        onCancel: _cancel,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}


class _CurrentAlgorithm extends StatelessWidget {
  const _CurrentAlgorithm({required this.future});

  final Future<String> future;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }

        if (snapshot.hasError) {
          return const AppEmptyState(
            icon: Icons.account_tree_outlined,
            title: '알고리즘을 불러오지 못했어요',
            description: '백엔드 연결 상태를 확인해 주세요.',
          );
        }

        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
          children: [
            AppSurface(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.positiveSoft,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: const Text(
                      '현재 적용 중 · Quant v0.4',
                      style: TextStyle(
                        color: AppColors.positive,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    '쉽게 말하면',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 10),
                  Text(
                    '① 거래가 활발한 후보를 고르고\n'
                    '② 가격 흐름을 수학적으로 0~100점으로 계산한 뒤\n'
                    '③ AI가 뉴스·경제 상황을 보고 위험하면 HOLD로 보류하고\n'
                    '④ 변동성이 높으면 주문 금액을 줄인 다음\n'
                    '⑤ Risk Guard가 마지막으로 주문을 검사해요.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  const Divider(),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _AlgorithmMiniCard(
                          title: '주식',
                          value: '상승일 비율 + 추세',
                          description: '한국시장 반전 위험 보정',
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _AlgorithmMiniCard(
                          title: '코인',
                          value: '21일 + 7일',
                          description: '짧은 모멘텀 중심',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    '65점 이상 BUY 후보 · 35점 이하 SELL 후보 · 그 사이는 HOLD',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    'AI는 수학적 방향을 반대로 뒤집지 않고, 위험하다고 판단하면 HOLD로만 보류해요.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            AppSurface(
              padding: EdgeInsets.zero,
              child: ExpansionTile(
                tilePadding:
                    const EdgeInsets.symmetric(horizontal: 18, vertical: 4),
                childrenPadding:
                    const EdgeInsets.fromLTRB(18, 0, 18, 20),
                title: Text(
                  '상세 수식·규칙 보기',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                subtitle: const Text(
                  '점수 계산식, 주문 크기, Risk Guard 기준',
                ),
                children: [
                  MarkdownBody(
                    data: snapshot.data ?? '',
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
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}


class _AlgorithmMiniCard extends StatelessWidget {
  const _AlgorithmMiniCard({
    required this.title,
    required this.value,
    required this.description,
  });

  final String title;
  final String value;
  final String description;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: AppColors.chip,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 2),
          Text(
            description,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}


class _QuantValidationTab extends StatefulWidget {
  const _QuantValidationTab();

  @override
  State<_QuantValidationTab> createState() => _QuantValidationTabState();
}


class _QuantValidationTabState extends State<_QuantValidationTab> {
  final _stockController = TextEditingController(text: '005930');
  final _cryptoController = TextEditingController(text: 'KRW-BTC');

  Map<String, dynamic>? _stockResult;
  Map<String, dynamic>? _cryptoResult;
  bool _stockLoading = false;
  bool _cryptoLoading = false;

  @override
  void dispose() {
    _stockController.dispose();
    _cryptoController.dispose();
    super.dispose();
  }

  Future<void> _run(String market) async {
    final isStock = market == 'stock';
    final controller = isStock ? _stockController : _cryptoController;
    final symbol = controller.text.trim().toUpperCase();
    if (symbol.isEmpty) return;

    setState(() {
      if (isStock) {
        _stockLoading = true;
      } else {
        _cryptoLoading = true;
      }
    });

    try {
      final result = await ApiClient.instance.runQuantBacktest(
        market: market,
        symbol: symbol,
      );
      if (!mounted) return;
      setState(() {
        if (isStock) {
          _stockResult = result;
        } else {
          _cryptoResult = result;
        }
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    } finally {
      if (mounted) {
        setState(() {
          if (isStock) {
            _stockLoading = false;
          } else {
            _cryptoLoading = false;
          }
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
      children: [
        AppSurface(
          emphasized: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '과거 데이터로 수학 신호 점검',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                '미래 데이터를 미리 보지 않도록 오늘 종가로 신호를 만들고 '
                '다음 거래일 시가에 체결한 것으로 계산해요. '
                '비교를 위해 편도 수수료 0.05%와 슬리피지 0.05%를 '
                '보수적인 공통 가정으로 사용해요. 실제 비용은 시장별로 달라요.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 8),
              Text(
                '이 결과는 한 종목의 정량 방향 신호만 확인하는 도구예요. '
                'AI 보류 판단, 여러 종목 동시 운용, 실제 체결 지연은 포함하지 않아요.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        _BacktestCard(
          title: '주식 정량 신호',
          hint: '6자리 종목코드',
          controller: _stockController,
          loading: _stockLoading,
          result: _stockResult,
          onRun: () => _run('stock'),
        ),
        const SizedBox(height: 14),
        _BacktestCard(
          title: '코인 정량 신호',
          hint: '예: KRW-BTC',
          controller: _cryptoController,
          loading: _cryptoLoading,
          result: _cryptoResult,
          onRun: () => _run('crypto'),
        ),
      ],
    );
  }
}


class _BacktestCard extends StatelessWidget {
  const _BacktestCard({
    required this.title,
    required this.hint,
    required this.controller,
    required this.loading,
    required this.result,
    required this.onRun,
  });

  final String title;
  final String hint;
  final TextEditingController controller;
  final bool loading;
  final Map<String, dynamic>? result;
  final VoidCallback onRun;

  String _pct(Object? value) {
    final number = num.tryParse(value?.toString() ?? '');
    return number == null ? '-' : '${number.toStringAsFixed(2)}%';
  }

  @override
  Widget build(BuildContext context) {
    return AppSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          TextField(
            controller: controller,
            textCapitalization: TextCapitalization.characters,
            decoration: InputDecoration(
              labelText: hint,
              isDense: true,
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: loading ? null : onRun,
              icon: loading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.science_outlined),
              label: Text(loading ? '검증 중...' : '최근 200일 백테스트'),
            ),
          ),
          if (result != null) ...[
            const SizedBox(height: 14),
            const Divider(),
            const SizedBox(height: 8),
            if (result!['status'] != 'completed')
              Text(
                '데이터가 충분하지 않아요. '
                '현재 ${result!['samples'] ?? 0}개 / '
                '필요 ${result!['required_samples'] ?? '-'}개',
              )
            else ...[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _ValidationMetric(
                    label: '거래',
                    value: '${result!['trade_count'] ?? 0}회',
                  ),
                  _ValidationMetric(
                    label: '승률',
                    value: _pct(result!['win_rate_pct']),
                  ),
                  _ValidationMetric(
                    label: '복리수익',
                    value: _pct(
                      result!['compound_return_pct'],
                    ),
                  ),
                  _ValidationMetric(
                    label: 'Buy & Hold',
                    value: _pct(result!['buy_hold_return_pct']),
                  ),
                  _ValidationMetric(
                    label: '최대낙폭',
                    value: _pct(
                      result!['max_drawdown_pct'],
                    ),
                  ),
                  _ValidationMetric(
                    label: '평균보유',
                    value: '${result!['average_holding_days'] ?? '-'}일',
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                result!['note']?.toString() ?? '',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
            ],
          ],
        ],
      ),
    );
  }
}


class _ValidationMetric extends StatelessWidget {
  const _ValidationMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.chip,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        '$label $value',
        style: Theme.of(context).textTheme.bodySmall,
      ),
    );
  }
}


class _ProposalList extends StatelessWidget {
  const _ProposalList({
    required this.future,
    required this.onApply,
    required this.onCancel,
  });

  final Future<List<Map<String, dynamic>>> future;
  final ValueChanged<String> onApply;
  final ValueChanged<String> onCancel;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }

        if (snapshot.hasError) {
          return const AppEmptyState(
            icon: Icons.cloud_off_rounded,
            title: '제안을 불러오지 못했어요',
            description: '잠시 뒤 다시 확인해 주세요.',
          );
        }

        final items = snapshot.data ?? <Map<String, dynamic>>[];
        if (items.isEmpty) {
          return const AppEmptyState(
            icon: Icons.auto_awesome_outlined,
            title: '새로운 제안이 없어요',
            description: '매매 데이터가 쌓이고 개선 포인트가 발견되면 여기에 제안이 나타납니다.',
          );
        }

        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
          itemCount: items.length,
          separatorBuilder: (_, __) => const SizedBox(height: 12),
          itemBuilder: (context, index) {
            final item = items[index];
            final id = item['id']?.toString() ?? '';

            return AppSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.primarySoft,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: const Text(
                      '검토 필요',
                      style: TextStyle(
                        color: AppColors.primary,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    item['title']?.toString() ?? '알고리즘 개선 제안',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),
                  MarkdownBody(
                    data: item['markdown']?.toString() ?? '',
                    styleSheet: MarkdownStyleSheet(
                      h1: const TextStyle(fontSize: 0, height: 0),
                      h2: Theme.of(context).textTheme.titleMedium,
                      p: Theme.of(context).textTheme.bodyMedium,
                      listBullet:
                          Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: AppColors.primary,
                              ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton(
                          onPressed: () => onApply(id),
                          child: const Text('적용'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => onCancel(id),
                          child: const Text('취소'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}
