import 'package:flutter/material.dart';

import '../services/api_client.dart';


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
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Live mode 전환'),
          content: const Text(
            'Live mode는 실제 주문이 가능한 모드입니다. '
            '서버의 TRADING_ENABLED와 Broker Adapter가 모두 준비된 경우에만 '
            '실제 주문이 허용됩니다.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Live 선택'),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
    }

    final value = await ApiClient.instance.setMode(live ? 'live' : 'paper');
    if (!mounted) return;
    setState(() => _settings = value);
  }

  Future<void> _setKillSwitch(bool enabled) async {
    final value = await ApiClient.instance.setKillSwitch(enabled);
    if (!mounted) return;
    setState(() => _settings = value);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(child: Text(_error!));
    }

    final settings = _settings ?? <String, dynamic>{};
    final live = settings['mode'] == 'live';
    final killSwitch = settings['kill_switch'] == true;
    final liveAllowed = settings['live_order_allowed'] == true;

    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Card(
          child: SwitchListTile(
            title: const Text('Live mode'),
            subtitle: Text(
              live
                  ? (liveAllowed
                      ? '실제 주문 허용 상태'
                      : 'Live 선택됨 · 서버 안전장치로 실제 주문은 아직 차단됨')
                  : 'Paper mode · 모의 주문',
            ),
            value: live,
            onChanged: _setLive,
          ),
        ),
        Card(
          child: SwitchListTile(
            title: const Text('Kill switch'),
            subtitle: const Text('켜면 자동/수동 신규 주문을 모두 차단합니다.'),
            value: killSwitch,
            onChanged: _setKillSwitch,
          ),
        ),
      ],
    );
  }
}
