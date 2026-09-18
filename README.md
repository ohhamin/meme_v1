# meme_v1

개인용 주식 + 코인 자동 매매 보조/실행 앱.

## 앱

Flutter 앱 하단 탭:

```text
[주식] [코인] [뉴스] [판단] [알고리즘] [세팅]
```

- **주식**: 보유 종목, 투자금/수량/이익률/판단점수, 수동 매수·매도
- **코인**: 보유 코인, 투자금/수량/이익률/판단점수, KRW 금액 기준 수동 매수·매도
- **뉴스**: 하루 1회 수집한 경제/시장 뉴스 최근 7일
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

뉴스와 판단은 하루에 Markdown 파일 하나씩 만들고 앱에서는 최근 7일을 날짜별로 조회한다.

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
- [ ] Upbit adapter
- [ ] 국내주식 broker adapter
- [x] 수동 매수/매도 API 골격
- [ ] 하루 1회 news collector
- [ ] adaptive decision scheduler (30~120분)
- [ ] 판단 Markdown 저장/조회
- [ ] Risk Guard / kill switch / paper trading
- [ ] AWS EC2 + Elastic IP 배포

상세 설계는 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)를 기준으로 계속 발전시킨다.


## 알고리즘 변경 흐름

알고리즘 개선 제안은 `data/algorithm/proposals/pending/*.md`로 저장한다.
앱의 **알고리즘 > 제안**에서 사용자가 적용해야만 현재 규칙에 반영된다.
취소한 제안은 화면에서는 사라지고 감사 목적으로 cancelled archive로 이동한다.

현재 단계에서는 Broker/LLM을 실제 연결하지 않았으므로 Live 주문은 실행되지 않는다.
