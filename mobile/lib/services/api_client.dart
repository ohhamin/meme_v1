import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;


class ApiClient {
  ApiClient._();

  static final ApiClient instance = ApiClient._();

  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  static const String apiToken = String.fromEnvironment(
    'API_TOKEN',
    defaultValue: '',
  );

  Map<String, String> get _headers {
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (apiToken.isNotEmpty) {
      headers['Authorization'] = 'Bearer $apiToken';
    }
    return headers;
  }

  Future<dynamic> _request(
    String method,
    String path, {
    Map<String, dynamic>? body,
    Duration timeout = const Duration(seconds: 20),
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    late http.Response response;

    try {
      if (method == 'GET') {
        response = await http
            .get(uri, headers: _headers)
            .timeout(timeout);
      } else if (method == 'POST') {
        response = await http
            .post(
              uri,
              headers: _headers,
              body: jsonEncode(body ?? <String, dynamic>{}),
            )
            .timeout(timeout);
      } else if (method == 'PUT') {
        response = await http
            .put(
              uri,
              headers: _headers,
              body: jsonEncode(body ?? <String, dynamic>{}),
            )
            .timeout(timeout);
      } else {
        throw UnsupportedError('Unsupported HTTP method: $method');
      }
    } on TimeoutException {
      throw Exception(
        '서버 응답 시간이 초과됐어요. Backend 연결 상태를 확인해 주세요.',
      );
    } on http.ClientException catch (e) {
      throw Exception('Backend 연결에 실패했어요: ${e.message}');
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      String message = response.body;
      try {
        final decoded = jsonDecode(response.body);
        message = decoded['detail']?.toString() ?? response.body;
      } catch (_) {}
      throw Exception(message);
    }

    if (response.body.isEmpty) {
      return null;
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Future<List<Map<String, dynamic>>> getPositions(String market) async {
    final data = await _request('GET', '/$market/positions') as List<dynamic>;
    return data.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> manualStockOrder({
    required String symbol,
    required String side,
    required int quantity,
  }) async {
    return (await _request(
      'POST',
      '/stocks/orders/manual',
      body: {
        'symbol': symbol,
        'side': side,
        'quantity': quantity,
        'idempotency_key': _idempotencyKey(symbol, side),
      },
    )) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> manualCryptoOrder({
    required String symbol,
    required String side,
    required num amountKrw,
  }) async {
    return (await _request(
      'POST',
      '/crypto/orders/manual',
      body: {
        'symbol': symbol,
        'side': side,
        'amount_krw': amountKrw,
        'idempotency_key': _idempotencyKey(symbol, side),
      },
    )) as Map<String, dynamic>;
  }

  Future<String> getDailyMarkdown(String kind, DateTime date) async {
    final day = _dateString(date);
    final data = await _request('GET', '/$kind/$day') as Map<String, dynamic>;
    return data['markdown']?.toString() ?? '';
  }

  Future<Map<String, dynamic>?> getLatestDecision({String? mode}) async {
    final suffix = mode == null
        ? ''
        : '?mode=${Uri.encodeQueryComponent(mode)}';
    final data = await _request('GET', '/decisions/latest$suffix');
    if (data == null) {
      return null;
    }
    return (data as Map).cast<String, dynamic>();
  }

  Future<String> getCurrentAlgorithm() async {
    final data =
        await _request('GET', '/algorithm/current') as Map<String, dynamic>;
    return data['markdown']?.toString() ?? '';
  }

  Future<Map<String, dynamic>> reviewAlgorithmNow() async {
    return (await _request(
      'POST',
      '/algorithm/review',
      timeout: const Duration(seconds: 90),
    )) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getAlgorithmProposals() async {
    final data =
        await _request('GET', '/algorithm/proposals') as Map<String, dynamic>;
    final items = data['items'] as List<dynamic>? ?? <dynamic>[];
    return items.cast<Map<String, dynamic>>();
  }

  Future<void> applyAlgorithmProposal(String id) async {
    await _request('POST', '/algorithm/proposals/$id/apply');
  }

  Future<void> cancelAlgorithmProposal(String id) async {
    await _request('POST', '/algorithm/proposals/$id/cancel');
  }

  Future<Map<String, dynamic>> getSettings() async {
    return (await _request('GET', '/settings')) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getStatus() async {
    return (await _request('GET', '/status')) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getSchedulerStatus() async {
    return (await _request('GET', '/scheduler/status'))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> setSchedulerEnabled(bool enabled) async {
    return (await _request(
      'PUT',
      '/settings/scheduler',
      body: {'enabled': enabled},
    )) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getReadiness() async {
    return (await _request('GET', '/readiness'))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getExternalReadiness() async {
    return (await _request('GET', '/readiness/external'))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getUnresolvedLiveOrders() async {
    final data = await _request(
      'GET',
      '/live-orders/unresolved?limit=50',
    ) as Map<String, dynamic>;
    final items = data['items'] as List<dynamic>? ?? <dynamic>[];
    return items.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> reconcileLiveOrders({
    String? intentId,
  }) async {
    final suffix = intentId == null
        ? '?limit=50'
        : '?intent_id=${Uri.encodeQueryComponent(intentId)}&limit=50';
    return (await _request(
      'POST',
      '/live-orders/reconcile$suffix',
    )) as Map<String, dynamic>;
  }

  Future<void> registerPushToken({
    required String token,
    required String platform,
  }) async {
    await _request(
      'PUT',
      '/devices/push',
      body: {
        'token': token,
        'platform': platform,
      },
    );
  }

  Future<Map<String, dynamic>> runPaperMarketCycle() async {
    return (await _request(
      'POST',
      '/decisions/market-paper-cycle',
      timeout: const Duration(seconds: 90),
    )) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getPaperPortfolio() async {
    return (await _request('GET', '/paper/portfolio'))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getPaperDashboard() async {
    return (await _request('GET', '/paper/dashboard'))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getMarketPerformance(String market) async {
    return (await _request('GET', '/$market/performance'))
        as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getUpbitMarkets() async {
    final data =
        await _request('GET', '/crypto/upbit/markets') as List<dynamic>;
    return data.cast<Map<String, dynamic>>();
  }

  Future<List<String>> getUpbitUniverse() async {
    final data = await _request(
      'GET',
      '/crypto/upbit/universe',
    ) as Map<String, dynamic>;
    final markets = data['markets'] as List<dynamic>? ?? <dynamic>[];
    return markets.map((item) => item.toString()).toList();
  }

  Future<List<String>> updateUpbitUniverse(List<String> markets) async {
    final data = await _request(
      'PUT',
      '/crypto/upbit/universe',
      body: {'markets': markets},
    ) as Map<String, dynamic>;
    final values = data['markets'] as List<dynamic>? ?? <dynamic>[];
    return values.map((item) => item.toString()).toList();
  }

  Future<List<String>> getTossUniverse() async {
    final data = await _request(
      'GET',
      '/stocks/toss/universe',
    ) as Map<String, dynamic>;
    final symbols = data['symbols'] as List<dynamic>? ?? <dynamic>[];
    return symbols.map((item) => item.toString()).toList();
  }

  Future<List<String>> updateTossUniverse(List<String> symbols) async {
    final data = await _request(
      'PUT',
      '/stocks/toss/universe',
      body: {'symbols': symbols},
    ) as Map<String, dynamic>;
    final values = data['symbols'] as List<dynamic>? ?? <dynamic>[];
    return values.map((item) => item.toString()).toList();
  }

  Future<Map<String, dynamic>> resetPaperPortfolio({
    String market = 'all',
    num? initialCash,
  }) async {
    return (await _request(
      'POST',
      '/paper/reset',
      body: {
        'market': market,
        'initial_cash': initialCash,
      },
    )) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> resumeLlm() async {
    return (await _request('POST', '/settings/llm/resume'))
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> setMode(String mode) async {
    return (await _request(
      'PUT',
      '/settings/mode',
      body: {'mode': mode},
    )) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> setKillSwitch(bool enabled) async {
    return (await _request(
      'PUT',
      '/settings/kill-switch',
      body: {'enabled': enabled},
    )) as Map<String, dynamic>;
  }

  String _idempotencyKey(String symbol, String side) {
    return '$symbol-$side-${DateTime.now().microsecondsSinceEpoch}';
  }

  String _dateString(DateTime date) {
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '${date.year}-$month-$day';
  }
}
