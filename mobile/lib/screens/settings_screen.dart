import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

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
  Map<String, dynamic>? _readiness;
  Map<String, dynamic>? _scheduler;
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
        ApiClient.instance.getReadiness(),
        ApiClient.instance.getSchedulerStatus(),
      ]);

      if (!mounted) return;
      setState(() {
        _settings = results[0];
        _status = results[1];
        _paper = results[2];
        _readiness = results[3];
        _scheduler = results[4];
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
                    '전환하면 Kill switch가 자동으로 다시 켜지고, '
                    '준비 상태를 확인한 뒤 별도로 꺼야 실제 주문이 가능해요.',
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
      await ApiClient.instance.setMode(live ? 'live' : 'paper');
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _setKillSwitch(bool enabled) async {
    try {
      await ApiClient.instance.setKillSwitch(enabled);
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _setSchedulerEnabled(bool enabled) async {
    try {
      await ApiClient.instance.setSchedulerEnabled(enabled);
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _resetPaper(String market, String label) async {
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
                  '$label Paper 계좌를 초기화할까요?',
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
      await ApiClient.instance.resetPaperPortfolio(market: market);
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$label Paper 계좌를 초기화했어요.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _openUnresolvedLiveOrders() async {
    try {
      final items = await ApiClient.instance.getUnresolvedLiveOrders();
      if (!mounted) return;

      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) {
          return Container(
            height: MediaQuery.of(context).size.height * 0.72,
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
                          child: Text(
                            '확인 필요한 Live 주문',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                        ),
                        Text(
                          '${items.length}건',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: items.isEmpty
                        ? const Center(
                            child: Text('확인 필요한 주문이 없어요.'),
                          )
                        : ListView.separated(
                            padding: const EdgeInsets.symmetric(horizontal: 20),
                            itemCount: items.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 10),
                            itemBuilder: (context, index) {
                              final item = items[index];
                              final broker =
                                  item['broker']?.toString().toUpperCase() ??
                                      '-';
                              final symbol =
                                  item['symbol']?.toString() ?? '-';
                              final side =
                                  item['side']?.toString().toUpperCase() ?? '-';
                              final state =
                                  item['status']?.toString() ?? 'UNKNOWN';
                              final reason =
                                  item['reason']?.toString() ?? '';

                              return AppSurface(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            '$symbol · $side',
                                            style: Theme.of(context)
                                                .textTheme
                                                .titleMedium,
                                          ),
                                        ),
                                        Text(
                                          state,
                                          style: const TextStyle(
                                            color: AppColors.warning,
                                            fontWeight: FontWeight.w800,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 5),
                                    Text(
                                      broker,
                                      style:
                                          Theme.of(context).textTheme.bodySmall,
                                    ),
                                    if (reason.isNotEmpty) ...[
                                      const SizedBox(height: 8),
                                      Text(
                                        reason,
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodySmall,
                                      ),
                                    ],
                                  ],
                                ),
                              );
                            },
                          ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 10, 20, 20),
                    child: SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: () async {
                          try {
                            await ApiClient.instance.reconcileLiveOrders();
                            if (!context.mounted) return;
                            Navigator.pop(context);
                            await _load();
                          } catch (e) {
                            if (!context.mounted) return;
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text(e.toString())),
                            );
                          }
                        },
                        icon: const Icon(Icons.sync_rounded),
                        label: const Text('Broker 상태 다시 확인'),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _checkExternalConnections() async {
    try {
      final result = await ApiClient.instance.getExternalReadiness();
      if (!mounted) return;

      const labels = <String, String>{
        'openai': 'OpenAI 설정',
        'firebase': 'Firebase',
        'upbit_public_market': 'Upbit 공개 시세',
        'upbit_account': 'Upbit 계좌',
        'toss_account': 'Toss 계좌',
        'krx_market': 'KRX 지수 API',
      };

      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) {
          return Container(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.75,
            ),
            decoration: const BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.vertical(
                top: Radius.circular(26),
              ),
            ),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 22),
            child: SafeArea(
              top: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
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
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          '외부 연동 점검',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ),
                      const Icon(
                        Icons.verified_user_outlined,
                        color: AppColors.primary,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '조회 API만 호출해 연결 상태를 확인해요. '
                    '이 점검은 실제 주문을 만들지 않아요.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 16),
                  Flexible(
                    child: ListView.separated(
                      shrinkWrap: true,
                      itemCount: labels.length,
                      separatorBuilder: (_, __) =>
                          const Divider(height: 20),
                      itemBuilder: (context, index) {
                        final entry = labels.entries.elementAt(index);
                        final raw =
                            (result[entry.key] as Map?)?.cast<String, dynamic>() ??
                                <String, dynamic>{};
                        final state =
                            raw['status']?.toString() ?? 'unknown';
                        final detail = raw['detail']?.toString();
                        final ok = state == 'ok' || state == 'configured';

                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              ok
                                  ? Icons.check_circle_rounded
                                  : state == 'not_configured'
                                      ? Icons.remove_circle_outline_rounded
                                      : Icons.error_outline_rounded,
                              color: ok
                                  ? AppColors.positive
                                  : state == 'not_configured'
                                      ? AppColors.textSecondary
                                      : AppColors.negative,
                              size: 20,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    entry.value,
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleMedium,
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    detail ??
                                        (state == 'not_configured'
                                            ? '아직 설정되지 않았어요.'
                                            : state),
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodySmall,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('확인'),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _runPaperCycleNow() async {
    final confirmed = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          padding: const EdgeInsets.fromLTRB(22, 12, 22, 24),
          decoration: const BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.vertical(
              top: Radius.circular(26),
            ),
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
                  'Paper 판단을 지금 실행할까요?',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  '저장된 Toss/Upbit 판단 대상을 실제 시세로 조회한 뒤 '
                  'AI 판단 → Position Sizer → Risk Guard → Paper 체결을 1회 실행해요.',
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
                        child: const Text('실행'),
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
      final result = await ApiClient.instance.runPaperMarketCycle();
      await _load();
      if (!mounted) return;

      final status = result['status']?.toString() ?? 'unknown';
      final items = result['items'] as List<dynamic>? ?? <dynamic>[];
      final orderCount = items.where((item) {
        if (item is! Map) return false;
        return item['order'] != null;
      }).length;
      final reason = result['reason']?.toString();

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            status == 'completed'
                ? 'Paper 판단 완료 · ${items.length}개 판단 · $orderCount개 주문'
                : 'Paper 판단 대기 · ${reason ?? '실행 조건을 확인해 주세요.'}',
          ),
        ),
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

  Future<void> _editDailyTokenLimit(int current) async {
    final controller = TextEditingController(text: current.toString());
    final value = await showDialog<int>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('하루 토큰 제한'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: '토큰',
            helperText: '50,000 ~ 100,000,000',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () {
              final parsed = int.tryParse(
                controller.text.replaceAll(',', '').trim(),
              );
              if (parsed == null || parsed < 50000 || parsed > 100000000) {
                return;
              }
              Navigator.pop(context, parsed);
            },
            child: const Text('저장'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (value == null) return;

    try {
      await ApiClient.instance.setLlmDailyTokenBudget(value);
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('하루 토큰 제한을 변경했어요.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _openOpenAiBilling() async {
    final uri = Uri.parse(
      'https://platform.openai.com/settings/organization/billing/overview',
    );
    final opened = await launchUrl(
      uri,
      mode: LaunchMode.externalApplication,
    );
    if (!opened && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('OpenAI API 결제 페이지를 열지 못했어요.'),
        ),
      );
    }
  }

  Future<void> _refreshOpenAiUsage() async {
    try {
      await ApiClient.instance.refreshOpenAiUsage();
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('OpenAI 사용량을 최신화했어요.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _openFlutterErrors() async {
    try {
      var items = await ApiClient.instance.getClientErrors();
      if (!mounted) return;

      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (sheetContext) {
          return StatefulBuilder(
            builder: (sheetContext, setSheetState) {
              return Container(
                height: MediaQuery.of(sheetContext).size.height * 0.82,
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
                              child: Text(
                                'Flutter 오류 기록',
                                style: Theme.of(sheetContext)
                                    .textTheme
                                    .titleLarge,
                              ),
                            ),
                            Text(
                              '${items.length}건',
                              style:
                                  Theme.of(sheetContext).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        child: items.isEmpty
                            ? const Center(
                                child: Text('수집된 Flutter 오류가 없어요.'),
                              )
                            : ListView.separated(
                                padding:
                                    const EdgeInsets.fromLTRB(20, 0, 20, 28),
                                itemCount: items.length,
                                separatorBuilder: (_, __) =>
                                    const Divider(height: 1),
                                itemBuilder: (context, index) {
                                  final item = items[index];
                                  final improved =
                                      item['improved'] == true;
                                  final message =
                                      item['message']?.toString() ?? '-';
                                  return ListTile(
                                    contentPadding:
                                        const EdgeInsets.symmetric(
                                      vertical: 6,
                                    ),
                                    title: Text(
                                      message,
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    subtitle: Text(
                                      '발생 ${item['count'] ?? 1}회 · '
                                      '개선여부 ${improved ? 'Y' : 'N'}',
                                    ),
                                    trailing: Icon(
                                      improved
                                          ? Icons.check_circle_rounded
                                          : Icons.error_outline_rounded,
                                      color: improved
                                          ? AppColors.positive
                                          : AppColors.warning,
                                    ),
                                    onTap: () async {
                                      final id =
                                          item['id']?.toString() ?? '';
                                      final stack =
                                          item['stack']?.toString() ?? '';
                                      final mark = await showDialog<bool>(
                                        context: sheetContext,
                                        builder: (dialogContext) {
                                          return AlertDialog(
                                            title: Text(
                                              '개선여부 ${improved ? 'Y' : 'N'}',
                                            ),
                                            content: SingleChildScrollView(
                                              child: SelectableText(
                                                '$message\n\n$stack',
                                              ),
                                            ),
                                            actions: [
                                              TextButton(
                                                onPressed: () =>
                                                    Navigator.pop(
                                                  dialogContext,
                                                  false,
                                                ),
                                                child: const Text('닫기'),
                                              ),
                                              if (!improved && id.isNotEmpty)
                                                FilledButton(
                                                  onPressed: () =>
                                                      Navigator.pop(
                                                    dialogContext,
                                                    true,
                                                  ),
                                                  child:
                                                      const Text('개선 완료(Y)'),
                                                ),
                                            ],
                                          );
                                        },
                                      );
                                      if (mark == true && id.isNotEmpty) {
                                        await ApiClient.instance
                                            .markClientErrorImproved(
                                          id,
                                          true,
                                        );
                                        items = await ApiClient.instance
                                            .getClientErrors();
                                        setSheetState(() {});
                                      }
                                    },
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
        },
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  Future<void> _openBackendErrors() async {
    try {
      var items = await ApiClient.instance.getBackendErrors();
      if (!mounted) return;

      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (sheetContext) {
          return StatefulBuilder(
            builder: (sheetContext, setSheetState) {
              return Container(
                height: MediaQuery.of(sheetContext).size.height * 0.82,
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
                              child: Text(
                                '백엔드 오류 기록',
                                style: Theme.of(sheetContext)
                                    .textTheme
                                    .titleLarge,
                              ),
                            ),
                            Text(
                              '${items.length}건',
                              style:
                                  Theme.of(sheetContext).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        child: items.isEmpty
                            ? const Center(
                                child: Text('수집된 백엔드 오류가 없어요.'),
                              )
                            : ListView.separated(
                                padding:
                                    const EdgeInsets.fromLTRB(20, 0, 20, 28),
                                itemCount: items.length,
                                separatorBuilder: (_, __) =>
                                    const Divider(height: 1),
                                itemBuilder: (context, index) {
                                  final item = items[index];
                                  final improved =
                                      item['improved'] == true;
                                  final type =
                                      item['error_type']?.toString() ?? '오류';
                                  final message =
                                      item['message']?.toString() ?? '-';
                                  final source =
                                      item['source']?.toString() ?? '';
                                  return ListTile(
                                    contentPadding:
                                        const EdgeInsets.symmetric(
                                      vertical: 6,
                                    ),
                                    title: Text(
                                      '$type · $message',
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    subtitle: Text(
                                      '${source.isEmpty ? '백엔드' : source} · '
                                      '발생 ${item['count'] ?? 1}회 · '
                                      '개선여부 ${improved ? 'Y' : 'N'}',
                                    ),
                                    trailing: Icon(
                                      improved
                                          ? Icons.check_circle_rounded
                                          : Icons.error_outline_rounded,
                                      color: improved
                                          ? AppColors.positive
                                          : AppColors.warning,
                                    ),
                                    onTap: () async {
                                      final id =
                                          item['id']?.toString() ?? '';
                                      final stack =
                                          item['stack']?.toString() ?? '';
                                      final contextText =
                                          item['context']?.toString() ?? '';
                                      final mark = await showDialog<bool>(
                                        context: sheetContext,
                                        builder: (dialogContext) {
                                          return AlertDialog(
                                            title: Text(
                                              '개선여부 ${improved ? 'Y' : 'N'}',
                                            ),
                                            content: SingleChildScrollView(
                                              child: SelectableText(
                                                '$type\n$message'
                                                '${source.isEmpty ? '' : '\n\n발생 위치: $source'}'
                                                '${contextText.isEmpty ? '' : '\n상황: $contextText'}'
                                                '${stack.isEmpty ? '' : '\n\n$stack'}',
                                              ),
                                            ),
                                            actions: [
                                              TextButton(
                                                onPressed: () =>
                                                    Navigator.pop(
                                                  dialogContext,
                                                  false,
                                                ),
                                                child: const Text('닫기'),
                                              ),
                                              if (!improved && id.isNotEmpty)
                                                FilledButton(
                                                  onPressed: () =>
                                                      Navigator.pop(
                                                    dialogContext,
                                                    true,
                                                  ),
                                                  child:
                                                      const Text('개선 완료(Y)'),
                                                ),
                                            ],
                                          );
                                        },
                                      );
                                      if (mark == true && id.isNotEmpty) {
                                        await ApiClient.instance
                                            .markBackendErrorImproved(
                                          id,
                                          true,
                                        );
                                        items = await ApiClient.instance
                                            .getBackendErrors();
                                        setSheetState(() {});
                                      }
                                    },
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
        },
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
    final readiness = _readiness ?? <String, dynamic>{};
    final live = settings['mode'] == 'live';
    final killSwitch = settings['kill_switch'] == true;
    final liveAllowed = settings['live_order_allowed'] == true;

    final llmBudget =
        (status['llm_budget'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final llmRuntime =
        (status['llm_runtime'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final liveOrders =
        (status['live_orders'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final liveEnablement =
        (liveOrders['enablement'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final unresolvedLiveOrders =
        (liveOrders['unresolved_count'] as num?)?.toInt() ?? 0;
    final pushStatus =
        (status['push'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final pushRegistered = pushStatus['registered'] == true;
    final scheduler = _scheduler ?? <String, dynamic>{};
    final schedulerEnabled = scheduler['enabled'] == true;
    final schedulerRunning = scheduler['running'] == true;
    final nextDecisionAt = scheduler['next_decision_at']?.toString() ??
        status['next_decision_at']?.toString();
    final lastRun =
        (scheduler['last_run'] as Map?)?.cast<String, dynamic>();
    final paperReadiness =
        (readiness['paper_auto'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final liveManualReadiness =
        (readiness['live_manual'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final liveAutoReadiness =
        (readiness['live_auto'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};

    final budgetMode = llmBudget['mode']?.toString() ?? 'unknown';
    final runtimeMode = llmRuntime['mode']?.toString() ?? 'unknown';

    final dailyBudget =
        (llmBudget['daily'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final openaiUsage =
        (status['openai_usage'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final openaiSynced = openaiUsage['status'] == 'ok';
    final dailyUsed = openaiSynced
        ? (openaiUsage['total_tokens'] as num?)?.toInt() ?? 0
        : (dailyBudget['used_tokens'] as num?)?.toInt() ??
            (llmBudget['used_tokens'] as num?)?.toInt() ??
            0;
    final dailyLimit = (dailyBudget['budget_tokens'] as num?)?.toInt() ??
        (settings['llm_daily_token_budget'] as num?)?.toInt() ??
        0;
    final dailyRemaining =
        (dailyBudget['remaining_tokens'] as num?)?.toInt() ??
            (dailyLimit > 0
                ? (dailyLimit - dailyUsed).clamp(0, dailyLimit)
                : 0);
    final dailyProgress = dailyLimit > 0
        ? (dailyUsed / dailyLimit).clamp(0.0, 1.0).toDouble()
        : null;
    final todayCostUsd = (openaiUsage['cost_usd'] as num?)?.toDouble();
    final creditBalanceAvailable =
        openaiUsage['credit_balance_available'] == true;
    final creditBalanceUsd =
        (openaiUsage['credit_balance_usd'] as num?)?.toDouble();
    final usageSyncStatus = openaiUsage['status']?.toString() ?? 'unavailable';
    final usageSyncedAt = openaiUsage['last_synced_at']?.toString();

    final number = NumberFormat('#,###');
    final stockPaper =
        (paper['stock'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
    final cryptoPaper =
        (paper['crypto'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{};
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
          const SizedBox(height: 20),
          const SectionTitle('준비 상태'),
          const SizedBox(height: 12),
          AppSurface(
            child: Column(
              children: [
                _ReadinessRow(
                  label: 'Paper 자동매매',
                  data: paperReadiness,
                ),
                const Divider(height: 24),
                _ReadinessRow(
                  label: 'Live 수동매매',
                  data: liveManualReadiness,
                ),
                const Divider(height: 24),
                _ReadinessRow(
                  label: 'Live 자동매매',
                  data: liveAutoReadiness,
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _checkExternalConnections,
                    icon: const Icon(Icons.cable_rounded),
                    label: const Text('외부 연동 읽기 점검'),
                  ),
                ),
              ],
            ),
          ),
          if (live) ...[
            const SizedBox(height: 20),
            const SectionTitle('Live 안전 상태'),
            const SizedBox(height: 12),
            AppSurface(
              child: Column(
                children: [
                  _SafetyRow(
                    label: '전체 거래 게이트',
                    enabled: liveEnablement['trading_enabled'] == true,
                  ),
                  const Divider(height: 24),
                  _SafetyRow(
                    label: '수동 Live 주문',
                    enabled:
                        liveEnablement['live_manual_order_enabled'] == true,
                  ),
                  const Divider(height: 24),
                  _SafetyRow(
                    label: '자동 Live 주문',
                    enabled:
                        liveEnablement['live_auto_order_enabled'] == true,
                  ),
                  const Divider(height: 24),
                  _SafetyRow(
                    label: 'Upbit Live 주문',
                    enabled:
                        liveEnablement['upbit_live_order_enabled'] == true,
                  ),
                  const Divider(height: 24),
                  _SafetyRow(
                    label: 'Toss Live 주문',
                    enabled:
                        liveEnablement['toss_live_order_enabled'] == true,
                  ),
                  const Divider(height: 24),
                  InkWell(
                    onTap: unresolvedLiveOrders > 0
                        ? _openUnresolvedLiveOrders
                        : null,
                    borderRadius: BorderRadius.circular(12),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: _SafetyRow(
                        label: '확인 필요한 주문',
                        enabled: unresolvedLiveOrders == 0,
                        enabledText: '없음',
                        disabledText: '$unresolvedLiveOrders건 · 보기',
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          if (!live) ...[
            const SizedBox(height: 20),
            SectionTitle(
              'Paper 계좌',
              trailing: TextButton(
                onPressed: () => _resetPaper('all', '전체'),
                child: const Text('전체 초기화'),
              ),
            ),
            const SizedBox(height: 12),
            _PaperAccountCard(
              title: '주식 · Toss',
              data: stockPaper,
              number: number,
              onReset: () => _resetPaper('stock', '주식'),
            ),
            const SizedBox(height: 12),
            _PaperAccountCard(
              title: '코인 · Upbit',
              data: cryptoPaper,
              number: number,
              onReset: () => _resetPaper('crypto', '코인'),
            ),
          ],
          const SizedBox(height: 20),
          const SectionTitle('자동 판단'),
          const SizedBox(height: 12),
          AppSurface(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.schedule_rounded,
                      color: AppColors.primary,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '다음 판단 예정',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 3),
                          Text(
                            nextDecisionAt == null
                                ? 'Scheduler가 꺼져 있거나 아직 예약되지 않았어요.'
                                : _formatDateTime(nextDecisionAt),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                _SafetyRow(
                  label: 'Scheduler',
                  enabled: schedulerRunning,
                  enabledText: '실행 중',
                  disabledText: '중지',
                ),
                if (lastRun != null) ...[
                  const Divider(height: 24),
                  Text(
                    '마지막 자동 판단',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 5),
                  Text(
                    [
                      lastRun['finished_at'] == null
                          ? null
                          : _formatDateTime(lastRun['finished_at'].toString()),
                      lastRun['status']?.toString(),
                      '판단 ${lastRun['decision_count'] ?? 0}개',
                      '주문 ${lastRun['order_count'] ?? 0}건',
                    ].whereType<String>().join(' · '),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  if (lastRun['reason'] != null) ...[
                    const SizedBox(height: 5),
                    Text(
                      lastRun['reason'].toString(),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppColors.negative,
                          ),
                    ),
                  ],
                ],
                if (!live) ...[
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: _runPaperCycleNow,
                      icon: const Icon(Icons.play_arrow_rounded),
                      label: const Text('Paper 판단 지금 1회 실행'),
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 20),
          const SectionTitle('알림'),
          const SizedBox(height: 12),
          AppSurface(
            child: _SafetyRow(
              label: 'FCM 기기 등록',
              enabled: pushRegistered,
              enabledText: '연결됨',
              disabledText: '미등록',
            ),
          ),
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
                                ? AppColors.warningSoft
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
                            openaiSynced
                                ? 'OpenAI 공식 Usage/Costs 기준'
                                : _aiStatusDescription(
                                    runtimeMode,
                                    budgetMode,
                                    llmRuntime,
                                  ),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: 'OpenAI 사용량 새로고침',
                      onPressed: _refreshOpenAiUsage,
                      icon: const Icon(Icons.refresh_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                if (dailyProgress != null) ...[
                  ClipRRect(
                    borderRadius: BorderRadius.circular(999),
                    child: LinearProgressIndicator(
                      minHeight: 8,
                      value: dailyProgress,
                      backgroundColor: AppColors.chip,
                      color: aiBlocked
                          ? AppColors.negative
                          : aiConserve
                              ? AppColors.warning
                              : AppColors.primary,
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
                Row(
                  children: [
                    Expanded(
                      child: _UsageMetric(
                        label: '오늘 사용 토큰',
                        value: number.format(dailyUsed),
                      ),
                    ),
                    Expanded(
                      child: InkWell(
                        borderRadius: BorderRadius.circular(12),
                        onTap: () => _editDailyTokenLimit(dailyLimit),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: _UsageMetric(
                            label: '하루 토큰 제한 · 변경',
                            value: dailyLimit > 0
                                ? number.format(dailyLimit)
                                : '제한 없음',
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
                      child: _UsageMetric(
                        label: '오늘 사용 크레딧',
                        value: todayCostUsd == null
                            ? '확인 필요'
                            : '\$${todayCostUsd.toStringAsFixed(4)}',
                      ),
                    ),
                    Expanded(
                      child: _UsageMetric(
                        label: 'API 잔여 크레딧',
                        value: creditBalanceAvailable &&
                                creditBalanceUsd != null
                            ? '\$${creditBalanceUsd.toStringAsFixed(2)}'
                            : '공식 API 미지원',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  openaiSynced
                      ? '오늘 남은 내부 토큰 ${number.format(dailyRemaining)}'
                          '${usageSyncedAt == null ? '' : ' · 최근 동기화 ${_formatDateTime(usageSyncedAt)}'}'
                      : usageSyncStatus == 'admin_key_required'
                          ? 'OpenAI Admin key를 연결하면 공식 토큰 사용량과 비용을 자동 동기화해요.'
                          : 'OpenAI 사용량 동기화 상태: $usageSyncStatus',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 6),
                Text(
                  'OpenAI는 선불 잔여 크레딧을 조회하는 공식 API를 제공하지 않아 '
                  '잔액은 추정하지 않고 대시보드에서 확인하도록 표시해요.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
                const SizedBox(height: 8),
                TextButton.icon(
                  onPressed: _openOpenAiBilling,
                  icon: const Icon(Icons.open_in_new_rounded, size: 18),
                  label: const Text('OpenAI API 크레딧 확인'),
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
          const SectionTitle('앱 오류'),
          const SizedBox(height: 12),
          AppSurface(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                ListTile(
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                  leading: const Icon(
                    Icons.bug_report_outlined,
                    color: AppColors.warning,
                  ),
                  title: Text(
                    'Flutter 오류 기록',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  subtitle: const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text(
                      '렌더링·프레임워크 오류를 모아두고 개선 여부를 Y/N으로 관리해요.',
                    ),
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: _openFlutterErrors,
                ),
                const Divider(height: 1),
                ListTile(
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                  leading: const Icon(
                    Icons.dns_outlined,
                    color: AppColors.warning,
                  ),
                  title: Text(
                    '백엔드 오류 기록',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  subtitle: const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text(
                      'Scheduler와 API 예외를 자동 저장하고 같은 오류는 발생 횟수로 묶어요.',
                    ),
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: _openBackendErrors,
                ),
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
                const Divider(),
                SwitchListTile(
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                  title: Text(
                    'AI Scheduler',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  subtitle: const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text(
                      '끄면 뉴스 수집·시장 컨텍스트·AI 매매 판단·알고리즘 검토를 모두 멈춰요.',
                    ),
                  ),
                  value: schedulerEnabled,
                  onChanged: _setSchedulerEnabled,
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

  String _formatDateTime(String raw) {
    try {
      final value = DateTime.parse(raw).toLocal();
      return DateFormat('MM/dd HH:mm').format(value);
    } catch (_) {
      return raw;
    }
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


class _ReadinessRow extends StatelessWidget {
  const _ReadinessRow({
    required this.label,
    required this.data,
  });

  final String label;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final ready = data['ready'] == true;
    final missing = (data['missing'] as List<dynamic>? ?? <dynamic>[])
        .map((item) => item.toString())
        .toList();

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              if (!ready && missing.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  '남은 조건: ' + missing.join(', '),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ],
          ),
        ),
        const SizedBox(width: 12),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: 9,
            vertical: 5,
          ),
          decoration: BoxDecoration(
            color: ready
                ? AppColors.positiveSoft
                : AppColors.negativeSoft,
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(
            ready ? '준비됨' : '대기',
            style: TextStyle(
              color: ready
                  ? AppColors.positive
                  : AppColors.negative,
              fontSize: 12,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      ],
    );
  }
}


class _SafetyRow extends StatelessWidget {
  const _SafetyRow({
    required this.label,
    required this.enabled,
    this.enabledText = 'ON',
    this.disabledText = 'OFF',
  });

  final String label;
  final bool enabled;
  final String enabledText;
  final String disabledText;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: 9,
            vertical: 5,
          ),
          decoration: BoxDecoration(
            color: enabled
                ? AppColors.positiveSoft
                : AppColors.negativeSoft,
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(
            enabled ? enabledText : disabledText,
            style: TextStyle(
              color: enabled
                  ? AppColors.positive
                  : AppColors.negative,
              fontSize: 12,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      ],
    );
  }
}


class _PaperAccountCard extends StatelessWidget {
  const _PaperAccountCard({
    required this.title,
    required this.data,
    required this.number,
    required this.onReset,
  });

  final String title;
  final Map<String, dynamic> data;
  final NumberFormat number;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) {
    final equity =
        num.tryParse(data['equity']?.toString() ?? '0') ?? 0;
    final cash =
        num.tryParse(data['cash']?.toString() ?? '0') ?? 0;
    final pnl =
        num.tryParse(data['daily_pnl_pct']?.toString() ?? '0') ?? 0;
    final orders =
        (data['daily_order_count'] as num?)?.toInt() ?? 0;
    final positions = (data['positions'] as List?)?.length ?? 0;

    return AppSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          Text(
            '평가금액',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 5),
          Text(
            number.format(equity) + '원',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _UsageMetric(
                  label: '현금',
                  value: number.format(cash) + '원',
                ),
              ),
              Expanded(
                child: _UsageMetric(
                  label: '보유',
                  value: positions.toString() + '개',
                ),
              ),
              Expanded(
                child: _UsageMetric(
                  label: '오늘 손익',
                  value: pnl.toStringAsFixed(2) + '%',
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '오늘 주문 ' + orders.toString() + '회',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: onReset,
              icon: const Icon(Icons.restart_alt_rounded),
              label: const Text('이 계좌 초기화'),
            ),
          ),
        ],
      ),
    );
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
