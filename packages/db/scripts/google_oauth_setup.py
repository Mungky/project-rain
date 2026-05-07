"""One-time script to get Google OAuth2 refresh token for Nimbus Drive uploads.

Usage:
    uv run python packages/db/scripts/google_oauth_setup.py

Steps before running:
    1. Go to https://console.cloud.google.com/apis/credentials
    2. Create credentials -> OAuth 2.0 Client ID -> Desktop app
    3. Download the JSON file
    4. Run this script and paste the path when prompted
    5. Browser opens -> login with your Google account -> grant access
    6. Copy the printed values to your .env file
"""
import json
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("ERROR: google-auth-oauthlib not installed.")
    print("Run: uv pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/drive"]


def main():
    print("=" * 60)
    print("  Rain · Nimbus · Google Drive OAuth2 Setup")
    print("=" * 60)
    print()
    print("Sebelum lanjut, pastikan kamu sudah:")
    print("  1. Buka https://console.cloud.google.com/apis/credentials")
    print("  2. Create credentials → OAuth 2.0 Client ID → Desktop app")
    print("  3. Download JSON-nya")
    print()

    creds_path = input("Path ke OAuth credentials JSON (download dari Google Cloud): ").strip()
    if not creds_path:
        print("Cancelled.")
        sys.exit(0)

    try:
        with open(creds_path) as f:
            client_data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File tidak ditemukan: {creds_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("ERROR: File bukan JSON yang valid.")
        sys.exit(1)

    # Support both "web" and "installed" client types
    info = client_data.get("installed") or client_data.get("web")
    if not info:
        print("ERROR: Format JSON tidak dikenali. Pastikan pakai type 'Desktop app'.")
        sys.exit(1)

    print()
    print("Browser akan terbuka. Login dengan akun Google kamu dan klik Allow.")
    print("(kalau browser tidak terbuka otomatis, copy URL yang muncul di terminal)")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    print()
    print("=" * 60)
    print("  Berhasil! Tambahkan ini ke .env kamu:")
    print("=" * 60)
    print()
    print(f"GOOGLE_OAUTH_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_OAUTH_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
    print()
    print("Setelah itu:")
    print("  - Set NIMBUS_DRIVE_ROOT_FOLDER_ID ke ID folder RAIN-ARCHIVE di Drive kamu")
    print("  - Restart backend")
    print("=" * 60)


if __name__ == "__main__":
    main()
