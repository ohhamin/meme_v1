# Backend

FastAPI 기반 개인용 주식 + 코인 자동 매매 Backend입니다.

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env

uvicorn backend.app.main:app --reload
```

기본 설정은 안전하게:

```text
Paper mode
Kill switch ON
TRADING_ENABLED=false
Live manual/auto broker gates=false
Scheduler=false
```

이다.

## 주요 파이프라인

```text
Toss / Upbit Market Data
        ↓
OpenAI Decision Cycle
        ↓
Position Sizer
        ↓
Risk Guard
        ↓
Paper Broker
or
Live Broker Safety Layer
```

Live 쪽은 주문 전 journal 저장, broker preflight, 결과 불명확 상태의 자동 재주문 금지,
주문 상태 reconciliation까지 구현되어 있다. 단, 환경변수 기본값에서는 실제 주문이 차단된다.

## Scheduler

- 뉴스: 기본 6시간
- 알고리즘 개선 review: 기본 24시간
- 매매 판단: 30~120분 adaptive
- Live 주문 상태 확인: 5분
- news/decisions 보존 정리: 매일
- 다음 adaptive 판단 시각은 재시작 후 복구

## Docker

프로젝트 루트에서:

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

운영 구조는 `deploy/README.md` 참고.

**Uvicorn worker는 1개만 사용한다.**
현재 Scheduler와 runtime JSON state가 단일 프로세스 기준이다.
