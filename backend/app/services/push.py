from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging

from backend.app.core.config import get_settings


class PushService:
    def __init__(self):
        self.config = get_settings()

    @property
    def configured(self) -> bool:
        return bool(
            self.config.firebase_credentials_path
            and self.config.fcm_device_token
        )

    def initialize(self) -> bool:
        if not self.configured:
            return False

        try:
            firebase_admin.get_app()
            return True
        except ValueError:
            pass

        credential_path = Path(self.config.firebase_credentials_path)
        if not credential_path.exists():
            return False

        try:
            firebase_admin.initialize_app(
                credentials.Certificate(str(credential_path))
            )
            return True
        except Exception:
            # Push 설정 문제 때문에 주문/API 흐름 자체가 실패하면 안 된다.
            return False

    def send(
        self,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> str | None:
        if not self.initialize():
            return None

        try:
            message = messaging.Message(
                token=self.config.fcm_device_token,
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
            )
            return messaging.send(message)
        except Exception:
            # 주문 성공 후 알림 실패가 주문 실패로 보이지 않도록 fail-soft 한다.
            return None
