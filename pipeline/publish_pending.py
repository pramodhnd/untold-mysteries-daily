"""Run by GitHub Actions: render and publish every approved story, then record it.

stories/approved/*.json  ->  render (Short or documentary)  ->  upload  ->  stories/published/ + data/published.csv
"""
import csv
import datetime
import glob
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PIPE = os.path.join(ROOT, "pipeline")
sys.path.insert(0, PIPE)


def run(cmd):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)


def main():
    approved = sorted(glob.glob(os.path.join(ROOT, "stories", "approved", "*.json")))
    if not approved:
        print("nothing approved; done")
        return
    limit = int(os.environ.get("MAX_PER_RUN", "4"))
    os.makedirs(os.path.join(ROOT, "stories", "published"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    log = os.path.join(ROOT, "data", "published.csv")
    new_log = not os.path.exists(log)
    for path in approved[:limit]:
        story = json.load(open(path))
        sid = story["id"]
        out = os.path.join(ROOT, "out", sid)
        os.makedirs(out, exist_ok=True)
        thumb = None
        if story.get("format") == "landscape":
            run(["python3", "pipeline/render_long.py", path, "photos.json", out])
            video = os.path.join(out, f"{sid}.mp4")
            thumb = os.path.join(out, f"{sid}_thumb.jpg")
            run(["python3", "pipeline/thumbnail.py", path, thumb])
            # YouTube chapters into the description
            chapters = open(os.path.join(out, f"{sid}_chapters.txt")).read().strip()
            yt = story.setdefault("youtube", {})
            if "CHAPTERS" not in yt.get("description", ""):
                yt["description"] = (yt.get("description", "") + "\n\nCHAPTERS\n" + chapters).strip()
        else:
            run(["python3", "pipeline/render.py", path, out])
            video = os.path.join(out, f"{sid}.mp4")
        from youtube_upload import upload
        vid = upload(video, story, thumb)
        print(f"published {sid} -> https://youtu.be/{vid}", flush=True)
        story.setdefault("youtube", {})["video_id"] = vid
        dest = os.path.join(ROOT, "stories", "published", os.path.basename(path))
        json.dump(story, open(dest, "w"), indent=1, ensure_ascii=False)
        os.remove(path)
        with open(log, "a", newline="") as fh:
            w = csv.writer(fh)
            if new_log:
                w.writerow(["date", "id", "title", "format", "video_id"])
                new_log = False
            w.writerow([datetime.date.today().isoformat(), sid, story["youtube"].get("title", story["title"]),
                        story.get("format", "short"), vid])
        shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    main()
