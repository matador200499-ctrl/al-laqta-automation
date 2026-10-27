import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def find_client_secrets_file() -> Path:
    """Find common Google OAuth downloaded filenames without exposing the file."""
    configured = os.environ.get("GOOGLE_CLIENT_SECRETS_FILE", "").strip()
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend([Path("client_secrets.json"), Path("client_secret.json")])
    candidates.extend(sorted(Path(".").glob("client_secret*.json")))
    candidates.extend(sorted(Path(".").glob("client_secrets*.json")))

    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            if candidate.is_file():
                return candidate

    raise FileNotFoundError(
        "لم يتم العثور على ملف بيانات OAuth من Google. "
        "نزّل الملف من Google Cloud Console وضعه بجوار هذا السكريبت، "
        "أو اضبط GOOGLE_CLIENT_SECRETS_FILE على مساره. "
        "لا ترفع الملف إلى GitHub ولا ترسله في المحادثات."
    )


def main():
    client_secrets_file = find_client_secrets_file()
    print("تم العثور على ملف OAuth:", client_secrets_file.name)
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_file), SCOPES)
    creds = flow.run_local_server(
        host="localhost",
        port=8080,
        authorization_prompt_message="سيتم فتح المتصفح لتسجيل الدخول إلى Google...",
        success_message="تمت الموافقة بنجاح. يمكنك إغلاق هذه الصفحة والعودة إلى البرنامج.",
        open_browser=True,
    )

    print("\n" + "=" * 60)
    print("انسخ القيم التالية مباشرة إلى GitHub → Settings → Secrets and variables → Actions.")
    print("لا تنشر هذه القيم، ولا ترسلها لأي شخص، ولا تضعها في ملف داخل المستودع.")
    print("=" * 60)
    print("\nYT_CLIENT_ID")
    print(creds.client_id)
    print("\nYT_CLIENT_SECRET")
    print(creds.client_secret)
    print("\nYT_REFRESH_TOKEN")
    print(creds.refresh_token)
    print("=" * 60)


if __name__ == "__main__":
    main()
