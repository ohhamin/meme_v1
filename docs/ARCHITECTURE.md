# Architecture

## 1. 방향

개인용 앱이므로 서비스 운영 복잡도를 최소화한다.

- Mobile: Flutter
- Push: Firebase Cloud Messaging
- Backend: FastAPI
- Scheduler: APScheduler 또는 cron
- Runtime: AWS EC2 1대 + Elastic IP
- Storage: 초기에는 파일 기반(Markdown/JSONL), 필요 시 SQLite 추가
- LLM: 매매 판단 보조
- Exchange/Broker: Adapter 패턴으로 분리

## 2. 전체 흐름

```text
[Daily Context Collector]
        |
        v
data/context/YYYY-MM-DD.md (최근 7일)
        |
        +--------------------+
                             v
[Hourly Decision Cycle] --> Market/Account Snapshot
        |
        v
   LLM Decision
 BUY / SELL / HOLD
        |
        v
    Risk Guard
        |
        +--> blocked -> log + FCM
        |
        v
  Broker Adapter
        |
        v
   Order Result
        |
        +--> JSONL audit log
        +--> FCM push
```

## 3. 앱 화면 최소 구성

개인용이므로 화면은 우선 4개만 만든다.

1. Dashboard
   - 총 평가금액
   - 코인/국내주식 비중
   - 금일 손익
   - 자동매매 ON/OFF
2. Positions
   - 보유 종목
   - 평균단가 / 현재가 / 수익률
3. Decisions
   - 최근 BUY/SELL/HOLD 판단
   - 판단 근거
   - Risk Guard 차단 여부
4. Settings
   - Paper/Live mode
   - Kill switch
   - FCM token 상태

## 4. Push 알림

우선순위:

- 주문 체결 성공
- 주문 실패
- Risk Guard 차단
- 일일 손실 한도 도달
- 시스템 오류
- 자동매매 중단

단순 HOLD 판단은 기본적으로 푸시하지 않는다.

## 5. 안전장치

- 기본 PAPER_TRADING=true
- LIVE 전환은 환경변수 + 앱 토글을 모두 만족해야 함
- 종목별 1시간 1주문
- 일일 총 주문 횟수 제한
- 종목별 최대 투자금 제한
- 일일 최대 손실 한도
- 동일 idempotency key 재주문 금지
- API 오류/LLM 파싱 오류 시 주문 금지(fail closed)
- Kill switch 활성화 시 신규 주문 즉시 차단

## 6. 저장 전략

DB 없이 시작하되 성격을 분리한다.

- data/context/*.md : 경제/시장 컨텍스트
- data/logs/decisions-YYYY-MM-DD.jsonl : 판단 이력
- data/logs/orders-YYYY-MM-DD.jsonl : 주문 이력

로그는 서버 로컬에 남기고 Git에는 커밋하지 않는다.

향후 조회 성능이나 집계가 필요해지면 SQLite로 옮긴다.

## 7. Adapter 인터페이스

```text
BrokerAdapter
  get_balance()
  get_positions()
  get_price(symbol)
  place_order(symbol, side, quantity_or_amount)
  get_order(order_id)
```

Upbit와 국내주식 증권사는 이 인터페이스를 각각 구현한다.

## 8. 스케줄

- 매일 07:00 KST: 경제/시장 컨텍스트 수집
- 매 정시: 매매 판단 사이클
- 서버 부팅 시: 헬스체크 + FCM 시작 알림

실제 주식 주문은 장 운영시간 여부를 Broker Adapter에서 추가 검증한다.
