from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging

from backend.app.core.config import get_settings
from backend.app.services.device_tokens import DeviceTokenService


class PushService:
    def __init__(self):
        self.config = get_settings()
        self.tokens = DeviceTokenService()

    @property
    def configured(self) -> bool:
        return bool(self.config.firebase_credentials_path)

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
            # Push configuration must not break trading/API flows.
            return False

    def send(
        self,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> str | None:
        if not self.initialize():
            return None

        targets = self.tokens.tokens()
        if self.config.fcm_device_token:
            targets.append(self.config.fcm_device_token)

        # Deduplicate rotated/manual tokens.
        targets = list(dict.fromkeys(targets))
        if not targets:
            return None

        first_id: str | None = None
        for token in targets:
            try:
                message = messaging.Message(
                    token=token,
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=data or {},
                )
                message_id = messaging.send(message)
                if first_id is None:
                    first_id = message_id
            except Exception:
                # Push failure after an order must never look like an order failure.
                continue

        return first_id
