import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../services/api_client.dart';
import '../theme/app_theme.dart';
import '../widgets/app_surface.dart';


class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}


class _SettingsScreenState extends State<SettingsScreen> {
  Map<String, dynamic>? _settings;
  Map<String, dynamic>? _status;
  Map<String, dynamic>? _paper;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([
        ApiClient.instance.getSettings(),
        ApiClient.instance.getStatus(),
        ApiClient.instance.getPaperPortfolio(),
      ]);

      if (!mounted) return;
      setState(() {
        _settings = results[0];
        _status = results[1];
        _paper = results[2];
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  Future<void> _setLive(bool live) async {
    if (live) {
      final confirmed = await showModalBottomSheet<bool>(
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
                    'Live mode로 바꿀까요?',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Live mode는 실제 주문이 가능한 모드예요. '
                    '서버의 TRADING_ENABLED와 Broker Adapter가 모두 준비되어야 실제 주문이 실행됩니다.',
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
                          child: const Text('취소'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: FilledButton(
                          onPressed: () => Navigator.pop(context, true),
                          child: const Text('Live 선택'),
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
      if (confirmed != true) return;
    }

    try {
      final value = await ApiClient.instance.setMode(live ? 'live' : 'paper');
      if (!mounted) return;
      setState(() => _settings = value);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _setKillSwitch(bool enabled) async {
    try {
      final value = await ApiClient.instance.setKillSwitch(enabled);
      if (!mounted) return;
      setState(() => _settings = value);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _resetPaper() async {
    final confirmed = await showModalBottomSheet<bool>(
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
                  'Paper 계좌를 초기화할까요?',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  '보유 종목과 Paper 주문 이력이 초기 상태로 돌아가요. '
                  '실제 계좌에는 아무 영향이 없습니다.',
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
                        child: const Text('취소'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: const Text('초기화'),
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

    if (confirmed != true) return;

    try {
      await ApiClient.instance.resetPaperPortfolio();
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Paper 계좌를 초기화했어요.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _resumeLlm() async {
    try {
      await ApiClient.instance.resumeLlm();
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('AI 판단을 다시 사용할 수 있게 열어뒀어요.')),
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
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return const AppEmptyState(
        icon: Icons.cloud_off_rounded,
        title: '설정을 불러오지 못했어요',
        description: '백엔드 연결 상태를 확인해 주세요.',
      );
    }

    final settings = _settings ?? <String, dynamic>{};
    final status = _status ?? <String, dynamic>{};
    final paper = _paper ?? <String, dynamic>{};
    final live = settings['mode'] == 'live';
    final killSwitch = settings['kill_switch'] == true;
    final liveAllowed = settings['live_order_allowed'] == true;

    final llmBudget =
        (status['llm_budget'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final llmRuntime =
        (status['llm_runtime'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};

    final budgetMode = llmBudget['mode']?.toString() ?? 'unknown';
    final runtimeMode = llmRuntime['mode']?.toString() ?? 'unknown';
    final usedTokens = (llmBudget['used_tokens'] as num?)?.toInt() ?? 0;
    final budgetTokens = (llmBudget['budget_tokens'] as num?)?.toInt() ?? 0;
    final remainingTokens =
        (llmBudget['remaining_tokens'] as num?)?.toInt() ?? 0;

    final progress = budgetTokens > 0
        ? (usedTokens / budgetTokens).clamp(0.0, 1.0).toDouble()
        : null;

    final number = NumberFormat('#,###');
    final paperEquity = num.tryParse(paper['equity']?.toString() ?? '0') ?? 0;
    final paperCash = num.tryParse(paper['cash']?.toString() ?? '0') ?? 0;
    final paperPnl =
        num.tryParse(paper['daily_pnl_pct']?.toString() ?? '0') ?? 0;
    final paperOrders = (paper['daily_order_count'] as num?)?.toInt() ?? 0;
    final aiBlocked = runtimeMode != 'normal' || budgetMode == 'paused';
    final aiConserve = budgetMode == 'conserve';

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
        children: [
          AppSurface(
            child: Row(
              children: [
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    color: live
                        ? AppColors.negativeSoft
                        : AppColors.positiveSoft,
                    borderRadius: BorderRadius.circular(15),
                  ),
                  child: Icon(
                    live ? Icons.bolt_rounded : Icons.science_outlined,
                    color: live ? AppColors.negative : AppColors.positive,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        live ? 'Live mode' : 'Paper mode',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 3),
                      Text(
                        live
                            ? (liveAllowed
                                ? '실제 주문이 가능한 상태예요'
                                : 'Live 선택됨 · 서버 안전장치로 실제 주문은 차단 중')
                            : '모의 주문으로 안전하게 테스트 중',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (!live) ...[
            const SizedBox(height: 20),
            const SectionTitle('Paper 계좌'),
            const SizedBox(height: 12),
            AppSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '평가금액',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 5),
                  Text(
                    number.format(paperEquity) + '원',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: _UsageMetric(
                          label: '현금',
                          value: number.format(paperCash) + '원',
                        ),
                      ),
                      Expanded(
                        child: _UsageMetric(
                          label: '오늘 손익률',
                          value: paperPnl.toStringAsFixed(2) + '%',
                        ),
                      ),
                      Expanded(
                        child: _UsageMetric(
                          label: '오늘 주문',
                          value: paperOrders.toString() + '회',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: _resetPaper,
                      icon: const Icon(Icons.restart_alt_rounded),
                      label: const Text('Paper 계좌 초기화'),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 20),
          const SectionTitle('AI 사용량'),
          const SizedBox(height: 12),
          AppSurface(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        color: aiBlocked
                            ? AppColors.negativeSoft
                            : aiConserve
                                ? const Color(0xFFFFF4E5)
                                : AppColors.primarySoft,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Icon(
                        aiBlocked
                            ? Icons.pause_circle_outline_rounded
                            : aiConserve
                                ? Icons.eco_outlined
                                : Icons.auto_awesome_rounded,
                        color: aiBlocked
                            ? AppColors.negative
                            : aiConserve
                                ? AppColors.warning
                                : AppColors.primary,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _aiStatusTitle(runtimeMode, budgetMode),
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 3),
                          Text(
                            _aiStatusDescription(
                              runtimeMode,
                              budgetMode,
                              llmRuntime,
                            ),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                if (progress != null) ...[
                  ClipRRect(
                    borderRadius: BorderRadius.circular(999),
                    child: LinearProgressIndicator(
                      minHeight: 8,
                      value: progress,
                      backgroundColor: AppColors.chip,
                      color: aiConserve
                          ? AppColors.warning
                          : aiBlocked
                              ? AppColors.negative
                              : AppColors.primary,
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
                Row(
                  children: [
                    Expanded(
                      child: _UsageMetric(
                        label: '오늘 사용',
                        value: number.format(usedTokens),
                      ),
                    ),
                    Expanded(
                      child: _UsageMetric(
                        label: '남은 내부 예산',
                        value: budgetTokens > 0
                            ? number.format(remainingTokens)
                            : '제한 없음',
                      ),
                    ),
                  ],
                ),
                if (runtimeMode == 'paused') ...[
                  const SizedBox(height: 18),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: _resumeLlm,
                      icon: const Icon(Icons.play_arrow_rounded),
                      label: const Text('AI 판단 재개'),
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 20),
          const SectionTitle('매매 설정'),
          const SizedBox(height: 12),
          AppSurface(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                SwitchListTile(
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                  title: Text(
                    'Live mode',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  subtitle: const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text('끄면 Paper mode로 동작해요.'),
                  ),
                  value: live,
                  onChanged: _setLive,
                ),
                const Divider(),
                SwitchListTile(
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                  title: Text(
                    'Kill switch',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  subtitle: const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text('켜면 자동·수동 신규 주문을 모두 막아요.'),
                  ),
                  value: killSwitch,
                  onChanged: _setKillSwitch,
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          if (killSwitch)
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.negativeSoft,
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.lock_rounded,
                    color: AppColors.negative,
                    size: 20,
                  ),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Kill switch가 켜져 있어 신규 주문이 차단되어 있어요.',
                      style: TextStyle(
                        color: AppColors.negative,
                        fontSize: 13,
                        height: 1.45,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  String _aiStatusTitle(String runtimeMode, String budgetMode) {
    if (runtimeMode == 'paused') return 'AI 판단 중지';
    if (runtimeMode == 'backoff') return 'AI 잠시 대기 중';
    if (budgetMode == 'paused') return '오늘 AI 예산 소진';
    if (budgetMode == 'conserve') return 'AI 절약 모드';
    if (budgetMode == 'disabled') return 'AI 사용 안 함';
    return 'AI 정상';
  }

  String _aiStatusDescription(
    String runtimeMode,
    String budgetMode,
    Map<String, dynamic> runtime,
  ) {
    if (runtimeMode == 'backoff') {
      final retryAt = runtime['retry_at']?.toString();
      return retryAt == null
          ? '일시적인 API 오류로 재시도를 기다리고 있어요.'
          : '일시적인 API 오류 · 재시도 예정 $retryAt';
    }
    if (runtimeMode == 'paused') {
      return 'API 키·quota·인증 상태를 확인한 뒤 재개해 주세요.';
    }
    if (budgetMode == 'paused') {
      return '내부 일일 토큰 예산을 모두 사용해 자동 판단을 멈췄어요.';
    }
    if (budgetMode == 'conserve') {
      return '남은 예산이 적어 과거 context를 더 짧게 사용하고 있어요.';
    }
    return '판단 사이클에서 토큰 예산을 확인하며 사용하고 있어요.';
  }
}


class _UsageMetric extends StatelessWidget {
  const _UsageMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium,
        ),
      ],
    );
  }
}
