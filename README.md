# meme_v1

개인용 주식 + 코인 자동 매매 보조/실행 앱.

## 앱

Flutter 앱 하단 탭:

```text
[주식] [코인] [뉴스] [판단] [알고리즘] [세팅]
```

- **주식**: 보유 종목, 투자금/수량/이익률/판단점수, 수동 매수·매도
- **코인**: 보유 코인, 투자금/수량/이익률/판단점수, KRW 금액 기준 수동 매수·매도
- **뉴스**: 6시간마다 수집한 경제/시장 뉴스 최근 7일
- **판단**: BUY/SELL/HOLD, 판단점수, 판단근거, Risk Guard 결과 최근 7일
- **알고리즘**: 현재 적용 규칙 확인 + 개선 제안 카드 적용/취소
- **세팅**: Paper/Live mode, Kill switch

## 자동 판단

판단 주기는 고정 1시간이 아니라 **30분~2시간 사이에서 유동적**으로 동작한다.

각 **전체 Decision Cycle** 후 다음 체크 시간을 정하고 Backend가 30~120분 범위로 제한한다.

한 사이클에서는 여러 종목을 동시에 판단할 수 있다. 즉 '1시간에 종목 1개'가 아니라 '약 30~120분마다 전체 대상 종목을 한 번 평가'하는 구조다.

## 데이터

```text
data/
├─ news/YYYY-MM-DD.md
├─ decisions/YYYY-MM-DD.md
└─ logs/*.jsonl
```

뉴스와 판단은 하루에 Markdown 파일 하나씩 만들고 앱에서는 최근 7일을 날짜별로 조회한다. 뉴스는 하루 파일 안에 6시간 간격의 여러 수집 배치를 누적한다.

## 기본 원칙

1. Paper mode가 기본값이다.
2. 수동 매매와 자동 매매 경로를 분리한다.
3. 모든 실제 주문은 Risk/잔고/시장 상태 검증을 거친다.
4. Kill switch가 켜지면 신규 주문을 차단한다.
5. API Key, 거래소 Secret, Firebase Service Account는 Git에 커밋하지 않는다.
6. FCM으로 체결/실패/차단/오류 알림을 보낸다.
7. 개인용 앱이므로 멀티테넌시와 복잡한 회원 관리 기능은 만들지 않는다.

## 구조

```text
meme_v1/
├─ backend/              # FastAPI + scheduler + broker adapters
├─ mobile/               # Flutter + Firebase/FCM
├─ data/
│  ├─ news/
│  ├─ decisions/
│  └─ logs/
├─ docs/
│  └─ ARCHITECTURE.md
├─ .env.example
└─ .gitignore
```

## 개발 순서

- [x] Backend foundation
- [x] Flutter 하단 6탭 UI 골격
- [ ] Firebase/FCM 연결
- [x] Upbit public market-data adapter
- [x] Upbit read-only account adapter
- [ ] Upbit Live order adapter
- [x] Toss OAuth/시세/계좌 read-only adapter
- [ ] Toss Live order adapter
- [x] 수동 매수/매도 API 골격
- [x] 6시간 간격 OpenAI web search news collector
- [x] adaptive 주식+코인 통합 Paper scheduler (30~120분)
- [x] LLM 판단 preview + 판단 Markdown 저장 골격
- [x] 일일 알고리즘 개선 review → 제안 MD 생성
- [x] Deterministic Risk Guard + preview API
- [x] Position Sizer + Paper 자동주문 엔진
- [ ] AWS EC2 + Elastic IP 배포

상세 설계는 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)를 기준으로 계속 발전시킨다.


## 알고리즘 변경 흐름

알고리즘 개선 제안은 `data/algorithm/proposals/pending/*.md`로 저장한다.
앱의 **알고리즘 > 제안**에서 사용자가 적용해야만 현재 규칙에 반영된다.
취소한 제안은 화면에서는 사라지고 감사 목적으로 cancelled archive로 이동한다.

현재 단계에서는 Broker/LLM을 실제 연결하지 않았으므로 Live 주문은 실행되지 않는다.


## LLM 비용 제어

매 판단마다 최근 7일 Markdown 전체를 보내지 않는다.

- 뉴스/판단 원본은 7일 보관
- 판단용 rolling context는 별도로 압축
- 한 Decision Cycle에서 여러 종목을 한 번의 LLM 호출로 처리
- 한 사이클 예상 입력 상한 적용
- 앱 자체 일일 token budget 적용
- 남은 예산이 적으면 conserve mode
- 예산 소진/API 장애 시 자동 신규 주문은 fail-closed
- 알고리즘 개선 review는 기본 24시간마다 별도로 수행

현재 초기 내부 한도는 `8000 tokens/cycle`, `200000 tokens/day`이며 환경변수로 조정한다.
실제 API 응답의 usage를 누적해 운영 후 적절한 값으로 조정한다.


## 현재 LLM 파이프라인

- 판단 모델: `OPENAI_DECISION_MODEL=gpt-5.6-terra`
- 뉴스 수집/요약 모델: `OPENAI_SUMMARY_MODEL=gpt-5.6-luna`
- 뉴스는 Responses API의 `web_search`를 사용해 6시간마다 수집
- `POST /decisions/preview`로 주문 없이 전체 종목 판단 파이프라인 테스트 가능
- 판단 결과는 한 사이클에 여러 종목을 함께 반환
- 실제 주문/Risk Guard 연결 전에는 기록 시 Risk Guard를 `PENDING`으로 표시
- 알고리즘 review는 기본 24시간마다 실행되며 제안이 필요한 경우에만 pending Markdown 생성
- pending 제안은 앱에서 사용자가 적용해야만 현재 알고리즘에 반영


## Risk Guard

LLM 판단과 별개의 deterministic hard-rule 계층이다.

```text
LLM Decision
    ↓
Order Intent
    ↓
Risk Guard
 PASS / BLOCK / NO_ORDER
    ↓
Broker
```

초기 규칙은 Kill switch, stale data, 장 운영 여부, 중복 주문,
일일 손실, 주문 횟수, 종목 집중도, 최대 보유종목 수, 현금 reserve를 검사한다.

- 주식(Toss)과 코인(Upbit)은 계좌를 합산하지 않는다.
- 별도 "한 주문 최대 금액" 제한은 두지 않는다.
- 한 종목은 해당 계좌 평가금액의 최대 40%까지 허용한다.
- 보유 종목은 전체 0~10개이며 0개, 즉 현금 100% 상태도 정상이다.

SELL은 기존 노출을 줄이는 주문이므로 일일 손실/신규 노출 제한보다
보유수량/시장상태 같은 핵심 검사를 우선 적용한다.


## Paper 자동매매

현재 Paper 모드에서는 다음 파이프라인이 연결되어 있다.

```text
LLM 전체종목 판단
→ deterministic Position Sizer
→ deterministic Risk Guard
→ Paper Broker
→ 앱 보유종목/판단 화면 반영
```

초기 sizing은 BUY 점수에 따라 평가금액의 1~4%, SELL 점수에 따라
보유수량의 25~60%를 주문 후보로 만든다. 최종 실행 여부는 항상 Risk Guard가 결정한다.

Paper 계좌도 주식(Toss 역할)과 코인(Upbit 역할)을 분리한다. 각각 기본 1,000,000원으로 시작하며 세팅 화면에서 평가금액/현금/일일손익/주문횟수를 따로 확인하고 개별 또는 전체 초기화할 수 있다.


## Upbit 연동

현재 Upbit 연동은 안전하게 단계별로 분리되어 있다.

1. **Public 시세**
   - API Key 없이 KRW 마켓 목록/현재가 조회
   - 코인 탭에서 AI 판단 대상 universe 선택
   - 선택값은 `data/state/upbit_universe.json`에 저장
2. **Read-only 계좌**
   - `UPBIT_ACCESS_KEY / UPBIT_SECRET_KEY`가 있으면 잔고 조회
   - Live mode의 코인 보유종목 화면은 실제 Upbit 잔고 + 현재가를 읽어 표시
   - 주문 API는 호출하지 않음
3. **Live 주문**
   - 아직 구현하지 않음
   - 현재 Live 수동/자동 주문 요청은 계속 fail-closed

자동 Paper 코인 사이클은 선택한 universe의 Upbit 실제 현재가를 읽은 뒤:

```text
Upbit public quote
→ LLM 전체 판단
→ Position Sizer
→ Risk Guard
→ Upbit 역할의 Paper 계좌
```

로 동작한다.

보유종목 수 0~10과 **판단 대상 universe 개수는 별개**다.
예를 들어 20개 코인을 관찰하더라도 실제 보유는 0~10개만 가능하다.


## Toss 증권 연동

토스증권 Open API의 OAuth2 Client Credentials 기반 read-only 연동을 추가했다.

현재 구현:

- OAuth access token 발급/캐시/401 시 1회 갱신
- 국내주식 현재가 조회
- 국내주식 기본정보 조회
- 국내 장 운영 캘린더 조회
- 계좌 목록 조회
- 국내주식 보유종목 조회
- KRW 매수가능금액 조회
- 주식 판단 universe 저장
- Live mode에서 실제 Toss 보유종목 read-only 표시
- 실제 Toss 시세를 이용한 Paper 판단/체결
- 주식+코인을 한 번의 LLM Decision Cycle에 함께 전달

실제 주문 endpoint는 아직 연결하지 않았고 계속 fail-closed 상태다.

주식 판단 대상은 앱 주식 탭에서 6자리 종목코드로 관리하며
`data/state/toss_universe.json`에 저장한다.
