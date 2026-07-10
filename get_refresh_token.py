"""
get_refresh_token.py

شغّل الملف ده مرة واحدة بس، على جهازك الشخصي (مش على GitHub Actions).
هيفتحلك متصفح تسجّل دخول بيه بحساب يوتيوب بتاع القناة، وهيطلع لك refresh token
تحطه بعدين كـ Secret اسمه YT_REFRESH_TOKEN في إعدادات الريبو.

الشرط: يكون عندك ملف client_secrets.json (نزّلته من Google Cloud Console)
في نفس المجلد ده.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n\nتم بنجاح! خد البيانات دي وحطها في GitHub Secrets:\n")
    print(f"YT_CLIENT_ID={creds.client_id}")
    print(f"YT_CLIENT_SECRET={creds.client_secret}")
    print(f"YT_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
