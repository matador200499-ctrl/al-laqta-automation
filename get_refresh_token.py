from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",
    SCOPES
)

creds = flow.run_local_server(
    host="localhost",
    port=8080,
    authorization_prompt_message="سيتم فتح المتصفح لتسجيل الدخول إلى Google...",
    success_message="تمت الموافقة بنجاح. يمكنك إغلاق هذه الصفحة والعودة إلى البرنامج.",
    open_browser=True
)

print("\n" + "=" * 60)
print("YT_CLIENT_ID")
print(creds.client_id)
print("=" * 60)

print("\n" + "=" * 60)
print("YT_CLIENT_SECRET")
print(creds.client_secret)
print("=" * 60)

print("\n" + "=" * 60)
print("YT_REFRESH_TOKEN")
print(creds.refresh_token)
print("=" * 60)
