import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import 'api_client.dart';


class PushRegistrationService {
  PushRegistrationService._();

  static final PushRegistrationService instance =
      PushRegistrationService._();

  StreamSubscription<String>? _tokenSubscription;

  Future<void> initialize() async {
    try {
      if (Firebase.apps.isEmpty) {
        await Firebase.initializeApp();
      }

      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission();

      final token = await messaging.getToken();
      if (token != null && token.isNotEmpty) {
        await _register(token);
      }

      await _tokenSubscription?.cancel();
      _tokenSubscription = messaging.onTokenRefresh.listen(
        (token) {
          unawaited(_register(token));
        },
      );
    } catch (_) {
      // Firebase/native config or backend may not exist yet.
      // Push setup must never prevent the trading app from starting.
    }
  }

  Future<void> _register(String token) async {
    try {
      await ApiClient.instance.registerPushToken(
        token: token,
        platform: _platform,
      );
    } catch (_) {
      // The token will be retried on the next app start/refresh.
    }
  }

  String get _platform {
    if (kIsWeb) return 'unknown';

    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'android';
      case TargetPlatform.iOS:
        return 'ios';
      default:
        return 'unknown';
    }
  }
}
