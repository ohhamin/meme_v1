String riskGuardLabel(String raw) {
  final value = raw.toUpperCase();
  if (value.contains('BLOCK')) return '차단';
  if (value.contains('PENDING')) return '대기';
  if (value.contains('NO_ORDER')) return '주문없음';
  if (value.contains('PASS')) return '통과';
  return raw;
}

String localizeDecisionReason(String raw) {
  final value = raw.trim();
  if (value.isEmpty) return '';

  final cooldown = RegExp(
    r'Automatic symbol cooldown is active \((\d+)s remaining\)\.',
    caseSensitive: false,
  ).firstMatch(value);
  if (cooldown != null) {
    final seconds = int.tryParse(cooldown.group(1) ?? '0') ?? 0;
    final minutes = seconds ~/ 60;
    final remainSeconds = seconds % 60;
    final remain = minutes > 0
        ? '${minutes}분 ${remainSeconds}초'
        : '${remainSeconds}초';
    return '동일 종목 자동 주문 대기시간이 남아 있어 차단됐어요. (남은 시간 $remain)';
  }

  final lower = value.toLowerCase();

  if (lower.contains('daily order') && lower.contains('limit')) {
    return '일일 최대 주문 횟수에 도달해 차단됐어요.';
  }
  if (lower.contains('daily loss')) {
    return '일일 손실 한도에 도달해 차단됐어요.';
  }
  if (lower.contains('cash reserve')) {
    return '최소 현금 보유 기준을 지키기 위해 차단됐어요.';
  }
  if (lower.contains('position') && lower.contains('limit')) {
    return '최대 보유 종목 수 제한 때문에 차단됐어요.';
  }
  if (lower.contains('market') && lower.contains('closed')) {
    return '현재 시장이 열려 있지 않아 주문이 차단됐어요.';
  }
  if (lower.contains('minimum') && lower.contains('order')) {
    return '최소 주문 금액 또는 수량 조건을 충족하지 못해 차단됐어요.';
  }
  if (lower.contains('insufficient') && lower.contains('cash')) {
    return '주문에 필요한 현금이 부족해 차단됐어요.';
  }
  if (lower.contains('insufficient') && lower.contains('position')) {
    return '매도 가능한 보유 수량이 부족해 차단됐어요.';
  }
  if (lower.contains('stale') && lower.contains('price')) {
    return '시세 정보가 오래되어 안전을 위해 주문을 차단했어요.';
  }
  if (lower.contains('duplicate')) {
    return '같은 판단 사이클에서 중복 주문이 감지되어 차단됐어요.';
  }
  if (lower.contains('kill switch')) {
    return 'Kill switch가 켜져 있어 주문이 차단됐어요.';
  }
  if (lower.contains('trading') && lower.contains('disabled')) {
    return '거래 기능이 비활성화되어 있어 주문이 차단됐어요.';
  }

  return value;
}
