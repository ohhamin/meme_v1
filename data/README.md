# Runtime Data

이 폴더는 서버가 실행 중 생성하는 개인용 런타임 데이터를 위한 구조다.

```text
data/
├─ news/                         # 하루 1개 경제/시장 뉴스 Markdown
├─ decisions/                    # 하루 1개 판단 Markdown
├─ algorithm/
│  ├─ current.md                 # 현재 Decision Engine 규칙
│  └─ proposals/
│     ├─ pending/                # 앱에 노출되는 대기 제안
│     ├─ applied/                # 적용된 제안 archive
│     └─ cancelled/              # 취소된 제안 archive
├─ state/                        # Paper/Live, Kill switch, idempotency state
└─ logs/                         # 주문/시스템 감사 JSONL
```

실제 런타임 파일은 개인 계좌/판단 정보가 포함될 수 있으므로 Git에 커밋하지 않는다.
디렉터리 골격만 `.gitkeep`으로 유지한다.
