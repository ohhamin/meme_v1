# Backend

FastAPI 기반 개인용 매매 앱 백엔드 골격입니다.

## 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

프로젝트 루트의 `.env.example`을 참고해 `.env`를 만듭니다.

현재 단계에서는 실제 Broker API와 LLM 판단 엔진을 연결하지 않았습니다.
Paper 주문만 로컬에서 시뮬레이션하며, Live 주문은 Adapter 구현 전까지 차단합니다.
