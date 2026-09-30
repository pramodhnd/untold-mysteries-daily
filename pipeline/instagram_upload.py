"""Post a rendered Short to Instagram as a Reel (Instagram API with Instagram Login, resumable upload).

Credentials come only from environment variables (GitHub Actions secrets), never from files in the repo:
  IG_USER_ID       the Instagram professional account id (from the Meta app dashboard)
  IG_ACCESS_TOKEN  long-lived token with instagram_business_basic + instagram_business_content_publish
Optional: IG_API_VERSION (default v23.0).
If either secret is missing, nothing is posted (YouTube publishing is never affected).

Usage: python3 pipeline/instagram_upload.py <video.mp4> <story.json>
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "https://graph.instagram.com"


def enabled():
    return bool(os.environ.get("IG_USER_ID") and os.environ.get("IG_ACCESS_TOKEN"))


def _ver():
    return os.environ.get("IG_API_VERSION", "v23.0")


def _call(method, path, params=None, data=None, headers=None, host=HOST):  # noqa: PLR0913
    params = dict(params or {}, access_token=os.environ["IG_ACCESS_TOKEN"])
    url = f"{host}/{_ver()}/{path}"
    body = None
    hdrs = {}
    if data is not None:
        body = data
    elif method == "POST":
        body = urllib.parse.urlencode(params).encode()
        params = {}
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Instagram API {method} {path}: {e.code} {e.read().decode(errors='replace')[:400]}")


def caption(story, credits=""):
    """Reel caption: title, first paragraph of the description, photo credits, hashtags (max 30), 2,200 chars."""
    meta = story.get("youtube", {})
    title = re.sub(r"\s*#shorts\b", "", meta.get("title") or story.get("title", ""), flags=re.I).strip()
    first = (meta.get("description", "").split("\n\n")[0]).strip()
    tags = [h for h in meta.get("hashtags", []) if h.lower() != "#shorts"]
    tags = list(dict.fromkeys(tags + ["#reels", "#mystery", "#truestory", "#unsolvedmysteries", "#history"]))[:30]
    parts = [title, first]
    if credits:
        parts.append("Photo credits:\n" + credits.strip())
    parts.append("A new true mystery every day. Longer documentaries on YouTube: Untold Mysteries Daily.")
    parts.append(" ".join(tags))
    text = "\n\n".join(p for p in parts if p)
    return text[:2200]


def post_reel(video, story, credits=""):
    """Upload and publish; returns {"id", "permalink"}."""
    if os.environ.get("DRY_RUN"):
        print(f"[dry run] would post Reel {os.path.basename(video)}", file=sys.stderr)
        return {"id": "DRYRUN", "permalink": ""}
    uid = os.environ["IG_USER_ID"]
    c = _call("POST", f"{uid}/media", {"media_type": "REELS", "upload_type": "resumable",
                                       "caption": caption(story, credits), "share_to_feed": "true"})
    cid = c["id"]
    size = os.path.getsize(video)
    with open(video, "rb") as fh:
        blob = fh.read()
    up = urllib.request.Request(f"https://rupload.facebook.com/ig-api-upload/{_ver()}/{cid}", data=blob, method="POST",
                                headers={"Authorization": f"OAuth {os.environ['IG_ACCESS_TOKEN']}", "offset": "0",
                                         "file_size": str(size), "Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(up, timeout=600) as r:
        res = json.load(r)
    if not res.get("success", True):
        raise RuntimeError(f"Instagram upload failed: {res}")
    for _ in range(40):  # up to ~13 minutes of processing
        st = _call("GET", cid, {"fields": "status_code,status"})
        code = st.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram processing {code}: {st.get('status')}")
        time.sleep(20)
    else:
        raise RuntimeError("Instagram processing timed out")
    pub = _call("POST", f"{uid}/media_publish", {"creation_id": cid})
    mid = pub["id"]
    link = ""
    try:
        link = _call("GET", mid, {"fields": "permalink"}).get("permalink", "")
    except Exception:  # noqa: BLE001
        pass
    return {"id": mid, "permalink": link}


if __name__ == "__main__":
    print(json.dumps(post_reel(sys.argv[1], json.load(open(sys.argv[2])))))
