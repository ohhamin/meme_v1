#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if ! command -v flutter >/dev/null 2>&1; then
  echo "flutter command was not found in PATH." >&2
  exit 1
fi

echo "Using: $(flutter --version | head -n 1)"
echo "Generating Android scaffold in a temporary directory..."

flutter create   --platforms=android   --org com.ohhamin   --project-name meme_v1   "$TMP_DIR/meme_v1"

rm -rf "$MOBILE_DIR/android"
cp -R "$TMP_DIR/meme_v1/android" "$MOBILE_DIR/android"

echo
echo "Android scaffold created at:"
echo "  $MOBILE_DIR/android"
echo
echo "Existing lib/ and pubspec.yaml were not overwritten."
echo "Next:"
echo "  cd $MOBILE_DIR"
echo "  flutter pub get"
echo "  flutter run --dart-define=API_BASE_URL=<backend> --dart-define=API_TOKEN=<token>"
echo
echo "Firebase push will remain optional until Android Firebase config is added."
