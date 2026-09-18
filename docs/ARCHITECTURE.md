# Architecture

## 1. 방향

개인용 자동 매매 보조/실행 앱이다. 멀티유저/관리자 기능보다 **내 계좌 조회, 수동 매매, 자동 판단, 뉴스 확인, 푸시 알림**에 집중한다.

- Mobile: Flutter
- Push: Firebase Cloud Messaging
- Backend: FastAPI
- Scheduler: APScheduler 또는 cron + adaptive next-check
- Runtime: AWS EC2 1대 + Elastic IP
- Storage: 초기에는 Markdown + JSONL, 필요 시 SQLite 추가
- LLM: 매매 판단/근거/다음 판단 시점 제안
- Exchange/Broker: Adapter 패턴으로 분리

## 2. 전체 흐름

```text
[6-Hour News/Context Collector]
        |
        v
data/news/YYYY-MM-DD.md  (최근 7일)
        |
        +--------------------------+
                                   v
[Adaptive Decision Cycle: 30~120분]
        |
        +--> Market / Account Snapshot
        +--> 최근 7일 뉴스 Context
        |
        v
   LLM Decision
 BUY / SELL / HOLD
 + 판단점수
 + 판단근거
 + next_check_minutes
        |
        v
    Risk Guard
        |
        +--> blocked -> decision 기록 + FCM
        |
        v
  Broker Adapter
        |
        v
   Order Result
        |
        +--> JSONL audit log
        +--> FCM push
        +--> 당일 decision Markdown 갱신
```

LLM이 다음 판단 시점을 제안할 수 있지만 Backend가 반드시 **30분 이상, 120분 이하**로 제한한다.

중요: 이 주기는 **종목별 주기**가 아니라 **전체 매매 판단 사이클의 실행 주기**다. 한 번의 Decision Cycle이 시작되면 관심/보유 종목 전체를 한꺼번에 평가하며, 같은 시각에 여러 종목의 BUY/SELL/HOLD 카드와 여러 주문이 발생할 수 있다.

## 3. 하단 메뉴

앱 하단 탭은 아래 6개로 고정한다.

```text
[주식] [코인] [뉴스] [판단] [알고리즘] [세팅]
```

### 3.1 주식 탭

현재 보유 중인 국내주식 목록을 카드/리스트로 표시한다.

각 항목:

- 종목명
- 투자금
- 보유 수량(몇 주)
- 이익률
- 판단점수
- 사기 버튼
- 팔기 버튼

판단점수는 우선 **0~100**으로 정의한다.

- 0에 가까울수록 매도 쪽
- 50 전후는 중립/HOLD
- 100에 가까울수록 매수 쪽

#### 수동 매수/매도

사기/팔기 버튼 클릭 시 팝업을 띄운다.

```text
종목명
현재가
수량: [ 3 ] 주

[취소] [매수/매도]
```

- 입력 단위: 정수 주
- 주문 전 예상 주문금액 표시
- 최종 확인 후 Backend를 통해 주문
- 이 주문은 자동 판단과 별개의 **수동 매매**
- Paper mode에서는 실제 주문 대신 모의 주문으로 기록

### 3.2 코인 탭

주식 탭과 동일한 레이아웃을 사용한다.

각 항목:

- 코인명
- 투자금
- 보유 수량
- 이익률
- 판단점수
- 사기 버튼
- 팔기 버튼

#### 수동 매수/매도

코인은 사용자 입력 기준을 **원화 금액**으로 통일한다.

```text
코인명
현재가
금액: [ 100,000 ] 원

[취소] [매수/매도]
```

- 매수: 입력한 KRW 금액으로 주문
- 매도: 입력한 KRW 금액을 현재가 기준 예상 코인 수량으로 환산하여 주문
- 주문 직전 예상 수량/금액을 다시 표시
- Paper mode에서는 모의 주문으로 기록

## 3.3 UI 디자인 원칙

전체 UI는 특정 앱을 그대로 복제하지 않고 **깔끔한 한국형 핀테크 앱 느낌**으로 간다.

- 배경은 아주 옅은 회색, 주요 정보는 흰색 surface 카드
- 큰 제목 + 굵은 핵심 숫자 + 충분한 여백
- 기본 포인트 컬러는 선명한 블루
- 수익/정상 상태는 그린, 손실/차단 상태는 레드
- 테두리보다 여백과 배경 차이로 영역을 구분
- 카드 radius는 크게, 그림자는 최소화
- 주문/Live 전환처럼 중요한 액션은 Bottom Sheet로 한 번 더 확인
- 빈 화면도 오류처럼 보이지 않도록 설명형 Empty State 제공
- 판단/알고리즘은 긴 문서보다 카드와 상태 chip을 우선 사용

## 4. 뉴스 탭

6시간마다 OpenAI Responses API의 web search로 수집한 경제/시장 뉴스를 최근 7일 동안 확인한다.

화면 상단:

```text
< 2026-09-18 v >
```

- 날짜 선택 가능
- 선택 가능 범위: 최근 7일
- 기본값: 오늘

본문은 해당 날짜의 Markdown을 읽어서 렌더링한다.

저장 위치:

```text
data/news/YYYY-MM-DD.md
```

한 날짜 파일에는 해당일의 여러 수집 배치를 함께 저장한다. 하루에 파일은 1개만 만들고, 6시간마다 같은 파일에 수집 시각별 섹션을 append 한다.

예:

```markdown
# 2026-09-18 News

## 00:00 Collection
- ...

## 06:00 Collection
- ...

## 12:00 Collection
- ...

## 18:00 Collection
- ...
```

즉 앱의 날짜 선택 UX는 그대로 유지하면서 하루 최대 4번 갱신된 뉴스 흐름을 한 화면에서 볼 수 있다.

## 5. 판단 탭

자동 판단 결과를 날짜별 카드 목록으로 보여준다.

화면 상단:

```text
< 2026-09-18 v >
```

- 최근 7일 선택 가능
- 기본값: 오늘

각 판단 카드:

- 판단 시각
- 시장: 주식 / 코인
- 종목명
- BUY / SELL / HOLD
- 판단점수
- 판단 근거
- Risk Guard 차단 여부
- 차단 사유(있는 경우)
- 다음 판단 예정 시각

### 판단 저장

**하루에 파일 하나**를 만들고 그날 발생한 여러 판단을 한 파일에 누적한다. 같은 Decision Cycle 시각에 여러 종목 카드가 있을 수 있다.

```text
data/decisions/YYYY-MM-DD.md
```

예:

```markdown
# 2026-09-18 Decisions

## 10:00 Decision Cycle

### BTC
- Action: HOLD
- Score: 54
- Reason: ...
- Risk Guard: PASS

### ETH
- Action: BUY
- Score: 73
- Reason: ...
- Risk Guard: PASS

- Next Check: 11:00

## 11:00 Decision Cycle

### 삼성전자
- Action: BUY
- Score: 72
- Reason: ...
- Risk Guard: BLOCKED
- Block Reason: ...

### SK하이닉스
- Action: HOLD
- Score: 58
- Reason: ...
- Risk Guard: PASS

- Next Check: 11:30
```

최근 7일치만 앱에서 기본 조회한다.

## 6. 알고리즘 탭

상단에 두 개의 탭을 둔다.

```text
[현재] [제안]
```

### 현재

현재 Decision Engine이 참조하는 알고리즘 규칙을 Markdown으로 보여준다.

저장 위치:

```text
data/algorithm/current.md
```

초기 알고리즘은 매수/매도 공식을 성급하게 고정하지 않고 아래의 공통 흐름부터 정의한다.

- 보유 포지션/손익 확인
- 시장 데이터 확인
- 최근 7일 뉴스 Context 참조
- BUY / SELL / HOLD 판단
- 판단점수 0~100
- 판단 근거 작성
- 전체 Decision Cycle의 다음 판단 시점 30~120분 제안
- Risk Guard 최종 검증

### 제안

실제 운영 데이터가 쌓인 뒤 알고리즘을 수정할 필요가 있다고 판단하면 **자동으로 적용하지 않고 제안 카드**를 생성한다.

예를 들어 다음과 같은 현상은 제안 검토의 입력이 될 수 있다.

- 비슷한 상황에서 판단이 지나치게 자주 뒤집힘
- Risk Guard에 동일한 이유로 반복 차단됨
- 판단 간격이 시장 변화에 비해 지나치게 빠르거나 느림
- 특정 규칙이 실제 주문 가능 조건과 계속 충돌함
- Paper 결과와 의도한 전략 동작이 지속적으로 어긋남

제안은 다음 위치에 Markdown 파일로 저장한다.

```text
data/algorithm/proposals/pending/{proposal_id}.md
```

각 카드에는 최소한 아래 내용을 포함한다.

- 제안 제목
- 제안 이유
- 바꾸려는 규칙
- 생성 시각
- 적용 버튼
- 취소 버튼

### 적용

사용자가 **적용** 버튼을 누르면 제안의 rule block만 현재 알고리즘 문서에 추가한다.

```text
pending proposal
      |
      v
사용자 Apply
      |
      +--> data/algorithm/current.md 갱신
      +--> proposals/applied/ 로 이동
      |
      v
다음 Decision Cycle부터 새 규칙 참조
```

알고리즘 제안은 Python/Dart 코드를 자동 수정하거나 임의 코드를 실행하지 않는다.
즉 **사람이 승인한 Markdown 기반 전략 규칙만 Decision Engine 입력에 반영**한다.

### 취소

취소하면 앱의 제안 목록에서는 즉시 사라진다.
감사 이력을 위해 파일은 `proposals/cancelled/`로 이동한다.

## 7. 세팅 탭

초기 버전에서는 두 가지 설정만 둔다.

### Paper / Live mode

- Paper: 모의 주문
- Live: 실제 주문
- 기본값은 Paper
- Live 전환 시 확인 팝업 표시

### Kill switch

- ON: 신규 주문 전부 차단
- OFF: 정상 동작
- 자동/수동 주문 모두 동일하게 적용
- 기존 보유 포지션을 자동 청산하지는 않음

## 8. Adaptive Decision Scheduler

판단 주기를 고정 1시간으로 두지 않는다.

허용 범위:

```text
30분 <= next_check_minutes <= 120분
```

기본 시작값은 60분으로 두고, 각 **전체 Decision Cycle**이 끝날 때 다음 체크 시간을 정한다.

고려 요소:

- 최근 가격 변동성
- 현재 포지션 보유 여부
- 손익 변화
- 뉴스 중요도
- 직전 판단의 확신도
- 시장 운영 시간

예시:

- 변동성이 크거나 중요한 뉴스 발생: 30~45분
- 일반 상태: 60분
- 변화가 적고 포지션도 안정적: 90~120분

LLM은 전체 사이클에 대해 하나의 `next_check_minutes`를 제안하고 Backend Scheduler가 범위를 검증한 뒤 `next_check_at`을 예약한다.

한 사이클에서는 종목 수 제한 없이 여러 종목을 평가할 수 있다. 예를 들어 10:00 사이클에서 BTC와 ETH 두 개 카드가 동시에 생성되고, 둘 다 주문 조건을 만족하면 둘 다 주문할 수 있다.

주식의 경우 장이 닫혀 있으면 Broker Adapter가 실제 주문을 차단하고 다음 유효 체크 시점을 조정한다.

## 9. 수동 매매와 자동 매매

두 경로를 명확하게 분리한다.

```text
[Flutter 사기/팔기]
      |
      v
Manual Order API
      |
      v
Risk / Mode / Balance Validation
      |
      v
Broker Adapter


[Scheduler]
      |
      v
Decision Engine
      |
      v
Risk Guard
      |
      v
Broker Adapter
```

수동 매매는 Scheduler의 판단 주기와 무관하게 사용자가 직접 실행한다.

다만 아래 공통 검증은 거친다.

- Paper / Live mode
- Kill switch
- 잔고/보유수량
- 최소 주문금액
- 시장 운영 가능 여부
- 중복 요청 방지(idempotency)

## 10. Push 알림

FCM으로 아래 이벤트를 푸시한다.

- 수동/자동 주문 체결 성공
- 주문 실패
- Risk Guard 차단
- 일일 손실 한도 도달
- 시스템 오류
- Kill switch 활성화
- 자동 매매 중단

단순 HOLD 판단은 기본적으로 푸시하지 않는다.

## 11. 안전장치

### Risk Guard 알고리즘

Risk Guard는 LLM이 아니다. **결정론적 hard-rule 엔진**으로 동작한다.
LLM/알고리즘이 BUY 또는 SELL을 제안하더라도 Risk Guard가 최종적으로
`PASS / BLOCK / NO_ORDER` 중 하나를 반환한다.

중요 원칙:

- Risk Guard는 종목이나 방향을 새로 고르지 않는다.
- 주문 수량/금액을 임의로 바꾸지 않는다.
- 조건을 넘으면 주문 전체를 BLOCK한다.
- HOLD는 `NO_ORDER`이며 차단으로 취급하지 않는다.
- 동일한 입력에는 동일한 결과가 나와야 한다.
- LLM 장애와 무관하게 로컬 코드에서 실행된다.

검사 순서:

1. Kill switch
2. 같은 Decision Cycle에서 동일 종목 중복 주문
3. 시장/계좌 snapshot freshness
4. 주식 장 운영 여부
5. 주문 데이터 유효성
6. SELL이면 보유수량 초과 여부
7. BUY이면 일일 손실 한도
8. BUY이면 일일 주문 횟수
9. BUY 후 한 종목 집중도
10. 신규 BUY이면 전체 보유종목 수 10개 초과 여부
11. BUY 후 해당 계좌의 현금 reserve

주식(Toss)과 코인(Upbit)은 **완전히 분리된 계좌**로 계산한다.
따라서 주식+코인을 합친 시장 노출도 제한은 두지 않는다.
주문금액 자체에도 별도의 최대금액 제한을 두지 않고,
최종적으로 해당 계좌 기준 종목 비중/현금/손실 제한을 만족하는지만 본다.

초기 Paper 운영용 기본값:

```text
RISK_MAX_POSITION_PCT=40
RISK_MAX_OPEN_POSITIONS=10
RISK_MAX_DAILY_LOSS_PCT=3
RISK_MAX_DAILY_ORDERS=20
RISK_MAX_DATA_AGE_SECONDS=300
RISK_MIN_CASH_RESERVE_PCT=10
```

이 숫자는 전략의 수익성을 의미하는 값이 아니라 초기 안전장치 기본값이다.
Paper 결과를 보고 변경한다.

### 0~10종목 / 현금 100% 허용

보유 종목 수에는 **최대 10개만 있고 최소 보유 종목 수는 없다.**
따라서 0개 보유도 정상 상태다.

```text
상승/기회 시장 -> 1~10종목 보유 가능
애매한 시장    -> 일부만 보유 가능
전면 매도 판단 -> 0종목 / 현금 100% 가능
```

10개를 이미 보유 중이면 새로운 11번째 종목 BUY는 BLOCK하지만,
기존 10개 종목 중 하나를 추가 매수하는 것은 40% 종목비중 제한 안에서 가능하다.

### BUY / SELL 비대칭

손실 한도나 주문 횟수 한도에 도달했을 때 **신규 BUY는 막지만,
기존 노출을 줄이는 SELL은 허용**한다.

예:

```text
daily PnL = -3.4%
limit = -3%

BUY  -> BLOCK
SELL -> PASS (보유수량/시장상태 등 다른 검사는 그대로 수행)
```

즉 손실 제한 때문에 오히려 위험을 줄이는 주문까지 막히는 상황을 피한다.

### Risk Preview

`POST /risk/preview`에 정규화된 주문 의도를 넣으면 실제 주문 없이
Risk Guard 결과를 테스트할 수 있다.

`GET /risk/policy`에서는 현재 서버에 적용된 hard limit을 확인한다.


- 기본 PAPER_TRADING=true
- LIVE 전환은 환경변수 + 앱 설정을 모두 만족해야 함
- Kill switch 활성화 시 모든 신규 주문 차단
- 자동 주문은 동일 종목에 대해 같은 판단 사이클에서 1회만 허용
- 하나의 판단 사이클에서 여러 종목 주문 가능
- 최소 자동 재판단 간격 30분
- 일일 총 주문 횟수 제한
- 종목별 최대 투자금 제한
- 일일 최대 손실 한도
- 동일 idempotency key 재주문 금지
- API 오류/LLM 파싱 오류 시 자동 주문 금지(fail closed)
- 수동 주문도 잔고/보유수량/시장 상태 검증

## 12. 저장 전략

DB 없이 시작하되 성격을 분리한다.

```text
data/
├─ news/
│  └─ YYYY-MM-DD.md
├─ decisions/
│  └─ YYYY-MM-DD.md
├─ algorithm/
│  ├─ current.md
│  └─ proposals/
│     ├─ pending/*.md
│     ├─ applied/*.md
│     └─ cancelled/*.md
├─ state/
│  ├─ settings.json
│  └─ idempotency.json
└─ logs/
   ├─ orders-YYYY-MM-DD.jsonl
   └─ system-YYYY-MM-DD.jsonl
```

- news: 하루 1개 Markdown, 최근 7일. 파일 안에는 6시간 간격 수집 배치를 누적
- decisions: 하루 1개 Markdown, 그날의 판단들을 누적, 최근 7일
- algorithm/current.md: 현재 Decision Engine이 읽는 승인된 전략 규칙
- algorithm/proposals: 대기/적용/취소된 알고리즘 제안 Markdown
- state: Paper/Live, Kill switch, idempotency 등 로컬 런타임 상태
- orders/system logs: 주문/알고리즘 변경 감사 및 장애 분석용 JSONL

Markdown 파일은 앱 표시용이자 LLM Context로 사용한다.

주문 감사 로그는 Git에 커밋하지 않는다.

### Decision Preview

Broker/Risk Guard를 실제 주문에 연결하기 전에 `POST /decisions/preview`로
시장/계좌 snapshot을 직접 넣어 LLM 판단 파이프라인을 검증할 수 있다.
preview는 절대로 주문을 생성하지 않는다.

## 13. API 초안

```text
GET  /health
GET  /status

GET  /stocks/positions
POST /stocks/orders/manual

GET  /crypto/positions
POST /crypto/orders/manual

GET  /news/dates
GET  /news/{date}

GET  /decisions/dates
GET  /decisions/{date}
POST /decisions/preview

GET  /algorithm/current
GET  /algorithm/proposals
POST /algorithm/proposals
POST /algorithm/proposals/{id}/apply
POST /algorithm/proposals/{id}/cancel

GET  /risk/policy
POST /risk/preview

GET  /settings
PUT  /settings/mode
PUT  /settings/kill-switch
POST /settings/llm/resume
```

## 14. Adapter 인터페이스

```text
BrokerAdapter
  get_balance()
  get_positions()
  get_price(symbol)
  validate_order(...)
  place_order(...)
  get_order(order_id)
  is_market_open()
```

코인은 Upbit adapter, 주식은 Toss 증권 연동 adapter를 목표로 각각 구현한다. 실제 Live 연동 방식은 해당 서비스의 지원 API를 확인한 뒤 확정한다.

## 15. 스케줄

- 6시간마다: 경제/시장 뉴스 수집
- 판단: 30~120분 사이에서 **전체 Decision Cycle** 단위 adaptive scheduling
- 서버 부팅 시: 헬스체크 + Scheduler 복구 + FCM 시작 알림
- 매일: 7일보다 오래된 news/decisions 파일 정리

기본 뉴스 수집 간격은 6시간이며 `NEWS_COLLECTION_INTERVAL_HOURS=6`으로 설정한다. 수집 주기와 매매 판단 주기는 서로 독립적이다.


## 16. 알고리즘 변경 안전 원칙

- 제안 생성과 적용을 분리한다.
- 제안은 절대로 자동 적용하지 않는다.
- Apply는 전략 문서만 변경하며 실행 코드를 수정하지 않는다.
- 새 규칙은 다음 Decision Cycle부터 읽힌다.
- Live 주문은 별도의 Trading/Risk Guard 안전장치를 계속 통과해야 한다.
- 제안 생성/적용/취소 이벤트는 추후 system audit log에 남긴다.


## 17. LLM 토큰/장애 운영 정책

매 판단 사이클마다 최근 7일의 뉴스/판단 Markdown 원문 전체를 모델에 다시 보내지 않는다.

### Context 계층

```text
원본 보관
data/news/YYYY-MM-DD.md
data/decisions/YYYY-MM-DD.md
        |
        v
Rolling Context
data/context/news_rolling.md
data/context/decision_rolling.md
        |
        v
현재 알고리즘 + 계좌/시장 snapshot
        |
        v
1회 Decision Cycle API 호출
```

원본 Markdown은 앱에서 조회하거나 사후 분석할 때 보관한다.
LLM 판단 시에는 rolling context를 우선 사용하고, rolling 파일이 아직 없을 때만 최근 원문에서 정해진 최대 길이만 읽는다.

초기 제한값:

- `LLM_CYCLE_INPUT_TOKEN_LIMIT=8000`: 한 Decision Cycle의 예상 입력 토큰 상한
- `LLM_DAILY_TOKEN_BUDGET=200000`: 앱 자체 일일 총 토큰 예산
- `LLM_CONTEXT_NEWS_CHARS=12000`: 판단에 포함할 뉴스 context 최대 문자 수
- `LLM_CONTEXT_DECISION_CHARS=6000`: 과거 판단 context 최대 문자 수
- `LLM_CONSERVE_THRESHOLD_PCT=20`: 일일 예산이 20% 이하이면 conserve mode
- `ALGORITHM_REVIEW_INTERVAL_HOURS=24`: 알고리즘 개선 검토는 판단 사이클마다 하지 않고 기본 하루 1회

위 값은 OpenAI 계정 자체의 한도가 아니라 **meme_v1 내부 비용/사용량 제어용 초기값**이며 운영 데이터를 보고 조정한다.

### 1회 사이클 호출

대상 종목마다 LLM을 따로 호출하지 않는다.

한 사이클에서 여러 종목을 한 번에 입력하고 결과도 배열 형태로 한 번에 받는 구조를 사용한다.

```text
10:00 cycle
  BTC
  ETH
  삼성전자
  SK하이닉스
       |
       v
  LLM API 1회
       |
       v
  [BTC 결과, ETH 결과, 삼성전자 결과, SK하이닉스 결과]
```

이렇게 해야 알고리즘/뉴스 context가 종목마다 반복 전송되는 비용을 줄일 수 있다.

### Algorithm Proposal 호출 분리

알고리즘 수정 제안은 매 Decision Cycle마다 생성하지 않는다.

- 기본: 24시간마다 최대 1회 review
- 동일 Risk Guard 반복 차단 등 명확한 trigger가 있을 때 별도 review 가능
- review에는 7일 원문 전체가 아니라 집계/rolling summary를 사용
- 제안이 없으면 Markdown을 만들지 않는다
- 생성된 제안은 절대로 자동 적용하지 않는다

### 실제 사용량 기록

모델 호출이 성공하면 API 응답의 실제 input/output token usage를
`data/state/llm_usage.json`에 누적한다.

API 호출 전에는 로컬에서 예상 입력 토큰을 계산하여:

1. 사이클 입력 상한 초과 여부
2. 앱 일일 토큰 예산 초과 여부

를 먼저 검사한다.

### 예산 단계

```text
NORMAL
  |
  | 남은 예산 <= 20%
  v
CONSERVE
  - news/decision context를 더 짧게 사용
  - 알고리즘 review 연기
  |
  | 일일 예산 소진
  v
PAUSED
  - LLM 신규 판단 중지
  - 자동 신규 주문 중지
  - 수동 주문/계좌 조회/앱 사용은 유지
```

Conserve/Paused 상태에서도 기존 Markdown, 계좌 조회, 뉴스 조회, 수동 매매 API는 계속 사용할 수 있다.

### API 장애 및 한도 초과

LLM 호출 실패 시 **기존 판단을 재사용해 새 자동 주문을 만들지 않는다.**

- 일시적 rate limit / timeout / overload:
  - 해당 사이클 자동 주문 중지
  - Retry-After가 있으면 해당 시간 이후 재시도
  - 없으면 backoff 후 재시도
- 앱 내부 일일 토큰 예산 소진:
  - 당일 LLM 자동 판단 pause
  - 다음 날짜에 로컬 사용량 예산 reset
- quota / billing / auth 등 자동 재시도로 해결되지 않는 오류:
  - LLM을 paused 상태로 유지
  - FCM으로 사용자에게 알림
  - 설정/한도 문제가 해결된 뒤 resume
- 어떤 경우에도 LLM 장애 자체 때문에 임의의 신규 자동 주문을 만들지 않는다.

향후 별도로 사용자가 승인한 로컬 hard-risk rule(예: 긴급 손실 제한)을 만들 수 있지만,
이는 LLM fallback 매매전략과 분리하여 Risk Guard 영역에서 관리한다.

### 상태 확인

`GET /status`에서 다음을 확인한다.

- 현재 일일 LLM token 사용량
- 남은 내부 예산
- normal / conserve / paused 상태
- API backoff 여부 및 재시도 시각


## 18. Position Sizer + Paper Broker

자동 매매의 첫 end-to-end 경로는 Live Broker가 아니라 Paper Broker로 완성한다.

```text
Market Snapshot
      +
Paper Account Snapshot
      |
      v
LLM Decision (여러 종목)
      |
      v
Position Sizer
      |
      v
Risk Guard
      |
  PASS / BLOCK
      |
      v
Paper Broker
      |
      +--> paper_portfolio.json
      +--> orders JSONL
      +--> decisions Markdown
      +--> FCM
```

### Position Sizer

Position Sizer도 LLM이 아니라 deterministic rule이다.
LLM은 BUY/SELL/HOLD와 방향성 점수만 만들고, Sizer가 주문 후보 금액/수량을 계산한다.

초기 BUY sizing:

```text
BUY score < 60   -> NO_ORDER
60~69            -> 현재 평가금액의 1%
70~79            -> 2%
80~89            -> 3%
90~100           -> 4%
```

초기 SELL sizing:

```text
SELL score > 40  -> NO_ORDER
31~40            -> 현재 보유수량의 25%
21~30            -> 40%
0~20             -> 60%
```

주식은 정수 주 단위로 내림하고, 코인은 8자리까지 계산한다.
Sizer가 만든 주문 후보는 항상 Risk Guard를 다시 통과해야 한다.

Sizer는 Risk Guard limit에 맞추기 위해 주문을 몰래 축소하지 않는다.
즉 Sizer 결과가 hard limit을 넘으면 Risk Guard가 BLOCK한다.

### Paper Broker

Paper Broker도 실제 운영 계좌 구조처럼 주식/코인을 분리한다.

```text
data/state/paper_stock_portfolio.json   # Toss 주식 계좌 역할
data/state/paper_crypto_portfolio.json  # Upbit 코인 계좌 역할
```

각 계좌의 현금/평가금액/손익/주문횟수는 서로 섞지 않는다.

기본 초기 현금은 각각:

```text
PAPER_STOCK_INITIAL_CASH_KRW=1000000
PAPER_CRYPTO_INITIAL_CASH_KRW=1000000
```

이며 테스트용 값이므로 환경변수로 독립 조정할 수 있다.

Paper Broker는:

- 현금
- 종목별 수량
- 평균단가
- 최근 가격
- 최근 가격 시각
- 평가금액
- 수익률
- 실현손익
- 일일 주문 횟수

를 로컬 JSON에 보존한다.

시장 snapshot이 새로 들어오면 보유종목을 mark-to-market 한다.

### Paper 자동 사이클

`POST /decisions/paper-cycle`은 현재 단계의 전체 자동매매 테스트 API다.

입력은 여러 종목의 최신 market snapshot이며:

1. Paper 계좌 가격 갱신
2. Paper 계좌 상태를 LLM context에 포함
3. LLM이 전체 종목을 한 번에 판단
4. Position Sizer가 종목별 주문 후보 계산
5. Risk Guard 검증
6. PASS 주문만 Paper Broker 체결
7. 판단 MD와 주문 로그 저장
8. 최종 Paper 포트폴리오 반환

순서로 동작한다.

Kill switch가 켜져 있으면 토큰을 낭비하지 않도록 LLM 호출 전 사이클 자체를 차단한다.

### Paper 수동 주문

Paper 모드의 앱 사기/팔기 버튼도 Paper Broker + Risk Guard를 거친다.

수동 주문은 마지막으로 저장된 시장가격을 사용하며,
가격 데이터가 `RISK_MAX_DATA_AGE_SECONDS`보다 오래되었으면 차단한다.

현재 UI는 보유 종목 카드에서 추가 매수/매도하는 흐름까지 지원한다.
보유하지 않은 새 종목을 수동으로 처음 매수하는 기능은 watchlist/search 화면을 추가할 때 연결한다.

### API

```text
GET  /paper/portfolio
POST /paper/reset
GET  /paper/position-sizing-policy

POST /decisions/paper-cycle
```


## 19. Upbit 시세/계좌 연동

Upbit 연동은 시세 조회, 계좌 조회, 주문 실행을 분리한다.

```text
Upbit Public Quotation
  -> KRW 마켓 목록 / 현재가
  -> Decision Universe
  -> LLM 판단
  -> Position Sizer
  -> Risk Guard
  -> Crypto Paper Account

Upbit Private Read-only
  -> 잔고 조회
  -> Live mode 코인 보유 화면

Upbit Live Order
  -> 아직 미구현 / fail-closed
```

코인 탭에서 사용자가 선택한 판단 대상은
`data/state/upbit_universe.json`에 저장한다.

판단 대상 수와 실제 보유 종목 수는 별개다.
판단 대상이 여러 개여도 Risk Guard가 허용하는 실제 보유는 전체 0~10개다.
Universe가 0개인 것도 정상이며 이 경우 자동 코인 판단을 대기한다.

### Adaptive Crypto Paper Cycle

Scheduler가 활성화되면 기본 판단 간격 뒤 첫 사이클을 예약한다.
각 사이클 결과의 `next_check_minutes`를 30~120분 범위로 제한한 뒤
다음 one-shot job을 예약한다. 실패하거나 차단된 사이클은 기본 간격으로 재시도한다.

### API

```text
GET  /crypto/upbit/markets
GET  /crypto/upbit/quotes?markets=KRW-BTC,KRW-ETH
GET  /crypto/upbit/universe
PUT  /crypto/upbit/universe
POST /crypto/upbit/paper-run
GET  /crypto/upbit/accounts
```

현재 실제 주문 API는 연결하지 않는다.
