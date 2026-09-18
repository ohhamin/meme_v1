import 'package:flutter/material.dart';

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
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final settings = await ApiClient.instance.getSettings();
      if (!mounted) return;
      setState(() {
        _settings = settings;
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
    final live = settings['mode'] == 'live';
    final killSwitch = settings['kill_switch'] == true;
    final liveAllowed = settings['live_order_allowed'] == true;

    return ListView(
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
    );
  }
}
