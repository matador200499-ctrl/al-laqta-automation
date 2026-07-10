"""
upload_youtube.py
يرفع فيديو على يوتيوب باستخدام YouTube Data API v3،
معتمدًا على refresh token متولّد مسبقًا (بدون فتح متصفح).

بيقرأ العنوان/الوصف/التاجز من content.json (الناتج من generate_content.py).
"""

import os
import sys
import json

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def get_authenticated_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds)


def main():
    video_path = os.environ.get("VIDEO_PATH")
    privacy_status = os.environ.get("PRIVACY_STATUS", "private")

    if not video_path or not os.path.exists(video_path):
        print(f"خطأ: ملف الفيديو غير موجود: {video_path}", file=sys.stderr)
        sys.exit(1)

    with open("content.json", "r", encoding="utf-8") as f:
        content = json.load(f)

    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": content.get("title", "فيديو جديد - اللقطة"),
            "description": content.get("description", ""),
            "tags": content.get("tags", []),
            "categoryId": "25",  # News & Politics — عدّلها حسب تصنيف قناتك
        },
        "status": {
            "privacyStatus": privacy_status,  # private / unlisted / public
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/*")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    print("جاري رفع الفيديو...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"تقدّم الرفع: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    print(f"تم الرفع بنجاح! رابط الفيديو: https://youtu.be/{video_id}")

    with open("upload_result.json", "w", encoding="utf-8") as f:
        json.dump({"video_id": video_id, "url": f"https://youtu.be/{video_id}"}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
