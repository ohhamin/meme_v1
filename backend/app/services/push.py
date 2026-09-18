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
        if firebase_admin._apps:
            return True

        credential_path = Path(self.config.firebase_credentials_path)
        if not credential_path.exists():
            return False

        firebase_admin.initialize_app(
            credentials.Certificate(str(credential_path))
        )
        return True

    def send(
        self,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> str | None:
        if not self.initialize():
            return None

        message = messaging.Message(
            token=self.config.fcm_device_token,
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
        )
        return messaging.send(message)
