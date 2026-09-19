# AWS EC2 deployment

이 프로젝트는 현재 **단일 사용자 + 단일 Backend 프로세스**를 전제로 한다.

## 권장 형태

```text
Flutter App
    |
    | HTTPS
    v
Nginx / TLS
    |
    | 127.0.0.1:8000
    v
FastAPI container (1 worker)
    |
    +-- local persistent data/
    +-- OpenAI
    +-- Upbit
    +-- Toss Securities
    +-- Firebase Admin
```

EC2에는 Elastic IP를 연결하고, 해당 IP를 Upbit/Toss API 허용 IP로 등록한다.
모바일 앱은 가능한 경우 Elastic IP 자체가 아니라 도메인 + HTTPS로 Backend에 접근한다.

## 중요한 운영 제약

- Uvicorn worker는 **반드시 1개**로 시작한다.
- 현재 Scheduler와 JSON runtime state는 단일 프로세스 기준이다.
- `data/`는 Docker volume/bind mount로 영속화한다.
- `.env`와 Firebase Service Account는 이미지에 COPY하지 않는다.
- 외부에 8000 포트를 직접 개방하지 않고 reverse proxy만 공개하는 구성을 권장한다.
- Live 주문 관련 환경변수는 처음 배포할 때 모두 `false`로 둔다.

## 초기 배포

```bash
cp .env.example .env
mkdir -p secrets

# .env 수정
# APP_ENV=production
# API_TOKEN=<충분히 긴 랜덤 토큰>
# SCHEDULER_ENABLED=true
# LIVE_* / *_LIVE_ORDER_ENABLED 는 아직 false 유지

docker compose -f deploy/docker-compose.yml up -d --build

curl http://127.0.0.1:8000/health
```

Firebase Admin JSON을 사용할 경우:

```text
secrets/firebase-admin.json
```

에 저장하고:

```env
FIREBASE_CREDENTIALS_PATH=/app/secrets/firebase-admin.json
```

로 설정한다.

## Live 단계적 활성화

한 번에 Live 전체를 켜지 않는다.

```text
1. APP_ENV=production
2. TRADING_ENABLED=false
3. Toss/Upbit read-only 계좌와 시세 확인
4. Paper Scheduler 장기간 확인
5. Live mode 화면만 확인
6. TRADING_ENABLED=true
7. LIVE_MANUAL_ORDER_ENABLED=true
8. 한 broker의 *_LIVE_ORDER_ENABLED=true
9. 소액 수동 주문 검증
10. 자동 주문은 마지막에 LIVE_AUTO_ORDER_ENABLED=true
```

`Kill switch`는 별도의 runtime 안전장치이며, Live 테스트 시작 전까지 ON을 유지한다.

## Reverse proxy

`deploy/nginx.conf.example`을 참고한다. 실제 도메인과 인증서 경로는 서버 환경에 맞게 변경한다.
