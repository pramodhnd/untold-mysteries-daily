"""Publisher agent: upload a rendered video to YouTube with the YouTube Data API v3.

Credentials come only from environment variables (GitHub Actions secrets), never from files in the repo:
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Optional: YT_PRIVACY (default "private"; set to "public" after Google's API audit approves the project).

Usage: python3 pipeline/youtube_upload.py <video.mp4> <story.json> [thumbnail.jpg]
Prints the new video id.
"""
import json
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def client():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def metadata(story):
    meta = story.get("youtube", {})
    title = meta.get("title") or story["title"]
    desc = meta.get("description", "")
    tags = meta.get("tags", [])
    hashtags = " ".join(meta.get("hashtags", []))
    if hashtags and hashtags not in desc:
        desc = f"{desc}\n\n{hashtags}".strip()
    out, total = [], 0
    for t in tags:  # YouTube rejects more than ~500 characters of tags
        total += len(t) + (2 if " " in t else 0) + 1
        if total > 480:
            break
        out.append(t)
    return title[:100], desc[:4900], out


def upload(path, story, thumb=None):
    if os.environ.get("DRY_RUN"):
        print(f"[dry run] would upload {path} as {metadata(story)[0]!r}", file=sys.stderr)
        return "DRYRUN"
    yt = client()
    title, desc, tags = metadata(story)
    meta = story.get("youtube", {})
    lang = "hi" if str(story.get("lang", "en")).lower().startswith("hi") else "en"
    body = {
        "snippet": {"title": title, "description": desc, "tags": tags,
                    "categoryId": str(meta.get("category_id", "27")),  # 27 = Education
                    "defaultLanguage": lang, "defaultAudioLanguage": lang},
        "status": {
            "privacyStatus": os.environ.get("YT_PRIVACY", "private"),
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": bool(meta.get("synthetic", True)),
            "embeddable": True,
            "publicStatsViewable": True,
        },
    }
    parts = "snippet,status"
    # translated title/description (e.g. English for a Hindi video) so viewers in the other language find it too
    loc = {k: {"title": v.get("title", "")[:100], "description": v.get("description", "")[:4900]}
           for k, v in (meta.get("localizations") or {}).items() if k != lang and v.get("title")}
    if loc:
        body["localizations"] = loc
        parts += ",localizations"
    req = yt.videos().insert(part=parts, body=body,
                             media_body=MediaFileUpload(path, chunksize=8 * 1024 * 1024, resumable=True))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"upload {int(status.progress() * 100)}%", file=sys.stderr)
    vid = resp["id"]
    if thumb and os.path.exists(thumb):
        try:  # needs a phone-verified channel; skip quietly otherwise
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb)).execute()
        except Exception as e:  # noqa: BLE001
            print(f"thumbnail skipped: {e}", file=sys.stderr)
    return vid


if __name__ == "__main__":
    story = json.load(open(sys.argv[2]))
    print(upload(sys.argv[1], story, sys.argv[3] if len(sys.argv) > 3 else None))
