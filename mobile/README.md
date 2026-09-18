# Mobile

Flutter 개인용 앱 골격입니다.

하단 탭:

```text
[주식] [코인] [뉴스] [판단] [알고리즘] [세팅]
```

## 최초 생성

이 저장소에는 핵심 Dart 소스만 먼저 넣었습니다. 로컬에서 `mobile/`로 이동한 뒤
Android/iOS 네이티브 폴더가 없다면 한 번 실행합니다.

```bash
flutter create .
flutter pub get
```

기존 `lib/` 파일은 덮어쓰지 않도록 확인하세요.

## 실행

Android Emulator 기준:

```bash
flutter run \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000 \
  --dart-define=API_TOKEN=change-me
```

실기기에서는 API_BASE_URL을 EC2 또는 같은 네트워크의 Backend 주소로 변경합니다.

## Firebase

FlutterFire CLI 설치 후:

```bash
flutterfire configure
```

생성되는 Firebase 설정과 Android/iOS 프로젝트 설정을 완료한 뒤
`PushService.initialize()`를 앱 시작 시 연결합니다.

Firebase credential/설정 파일은 저장소에 커밋하지 않습니다.


## 디자인

초기 UI는 깔끔한 핀테크 앱 스타일로 구성합니다.

- 옅은 회색 배경 + 흰색 surface
- 큰 제목과 굵은 핵심 숫자
- 블루 포인트 컬러
- 초록: 수익/정상, 빨강: 손실/차단
- 주문과 Live 전환은 Bottom Sheet 확인
- 판단은 Markdown 원문 대신 가능한 경우 종목별 카드로 렌더링
- 알고리즘은 현재/제안 segmented tab으로 분리
