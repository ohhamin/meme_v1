# meme_v1

개인용 자동 매매 보조/실행 앱 프로젝트.

## 목표

- 코인 + 국내주식 운용
- 서버가 정해진 주기로 시장/계좌 상태를 점검하고 **매수 / 매도 / 보유** 판단
- 경제/시장 컨텍스트는 하루 1회 수집하여 Markdown으로 보관하고 최근 7일치를 의사결정에 사용
- 판단 주기는 기본 1시간
- 한 종목당 1시간에 최대 1회 주문
- 모바일 앱에서 포트폴리오, 판단 기록, 주문 결과 확인
- Firebase Cloud Messaging(FCM)으로 판단/체결/오류 푸시 알림
- 개인용이므로 멀티테넌시, 회원 관리, 복잡한 관리자 기능은 만들지 않음

## 기본 원칙

1. **Paper mode가 기본값**이며 명시적으로 켜기 전에는 실제 주문을 보내지 않는다.
2. 실제 주문에는 종목별/일별 한도와 중복 주문 방지(idempotency)를 둔다.
3. LLM은 판단 근거를 만들 수 있지만 주문 가능 여부는 별도의 Risk Guard가 최종 검증한다.
4. API Key, 거래소 Secret, Firebase Service Account는 Git에 커밋하지 않는다.
5. 경제/시장 원문은 data/context/의 Markdown, 판단/주문 감사 로그는 JSONL로 남긴다.
6. 개인 앱이므로 서버 API는 단일 사용자 인증만 지원한다.

## 구조

```text
meme_v1/
├─ backend/              # FastAPI + scheduler + broker adapters
├─ mobile/               # Flutter + Firebase/FCM
├─ data/
│  ├─ context/           # 최근 7일 시장/경제 Markdown
│  └─ logs/              # decision/order JSONL (gitignore)
├─ docs/
│  └─ ARCHITECTURE.md
├─ .env.example
└─ .gitignore
```

## 1차 개발 순서

- [ ] Backend foundation
- [ ] Firebase/FCM 연결
- [ ] Flutter 개인용 앱
- [ ] Upbit adapter
- [ ] 국내주식 broker adapter
- [ ] 하루 1회 context collector
- [ ] 1시간 decision cycle
- [ ] Risk Guard / kill switch / paper trading
- [ ] AWS EC2 + Elastic IP 배포

자세한 설계는 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 참고.
