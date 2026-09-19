# Mobile

Flutter 개인용 앱 골격입니다.

하단 탭:

```text
[주식] [코인] [뉴스] [판단] [알고리즘] [세팅]
```

## Android 네이티브 프로젝트 생성

저장소의 핵심 Dart 소스는 유지하면서 Android 폴더만 안전하게 생성하려면:

```bash
cd mobile
bash tool/bootstrap_android.sh
flutter pub get
```

스크립트는 임시 Flutter 프로젝트에서 `android/`만 가져오기 때문에
기존 `lib/`와 `pubspec.yaml`을 덮어쓰지 않습니다.

GitHub Actions의 `android-build` workflow도 동일한 방식으로 매번
깨끗한 Android scaffold를 만든 뒤 실제 debug APK까지 빌드합니다.
성공한 workflow에는 `meme-v1-debug-apk` artifact가 7일 동안 저장됩니다.

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


## 현재 로컬 Flutter가 없어도

GitHub의 `android-build` workflow가 성공하면 로컬에서 Flutter 설치를 끝내기 전에도
실제 Android debug APK가 생성되는지 확인할 수 있습니다.

CI용 APK에는 실제 운영 API 주소/토큰을 넣지 않습니다.
실기기 검증용 빌드는 본인 Backend 주소와 API token을 `--dart-define`으로 넣어 다시 빌드합니다.
