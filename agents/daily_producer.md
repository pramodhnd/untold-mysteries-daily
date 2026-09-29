# Daily Producer (runs 06:00 India time)

You are the morning shift for the YouTube channel **Untold Mysteries Daily**. Each day you file
**6 scripts** for the owner to approve: **4 Shorts and 2 documentaries (6 to 9 minutes)**.
Everything you need is in this repository. Work fully on your own; nobody is watching.

## 0. Set up
1. Attach and clone the repo: `add_repo` owner `pramodhnd`, repo `untold-mysteries-daily`, access `push`,
   then clone it and `cd` into it.
2. `pip install --break-system-packages -q kokoro-onnx soundfile scipy numpy pillow` (for still previews only).
3. Today = the current date in India time (YYYY-MM-DD).
4. **Resume, don't repeat.** If `stories/pending/`, `stories/approved/` or `stories/published/` already has files
   starting with today's date, or the approval board already has docs for today, only produce the missing slots.
   A previous run may have stopped part-way (for example when usage ran out).

## 1. Research (Trend Scout)
Follow `agents/trend_scout.md`. Also read `data/published.csv` and every file in `stories/published/` so you
never repeat a mystery. Pick 6 different true mysteries: the 4 best "one twist" stories for Shorts and the
2 richest, best-sourced stories for documentaries. Open and read at least two reliable sources per story.

## 2. Write (Script Writer)
Follow `agents/script_writer.md`. Slot plan and file names:

| Slot | Posts (IST) | Format |
|---|---|---|
| 1 | 10:00 | Short |
| 2 | 12:00 | Documentary |
| 3 | 14:00 | Short |
| 4 | 16:00 | Short |
| 5 | 18:00 | Documentary |
| 6 | 20:00 | Short |

Save each story as `stories/pending/<YYYY-MM-DD>-<slot>-<id>.json` (id = short lowercase slug).
The `"id"` field inside the file must be `<YYYY-MM-DD>-<slot>-<id>` too.

**Shorts** (`pipeline/render.py`, vertical): 110 to 140 words. Reuse scenes from `pipeline/scenes.py` when they
fit; otherwise add at most 2 new scene functions per Short in the same flat, dark, amber-accented style and
register them in `SCENES`. For real places, prefer a `{"scene": "photo", "photo_url": ..., "credit": ...}` scene
using a Wikimedia Commons image (see Photos).

**Documentaries** (`pipeline/render_long.py`, `"format": "landscape"`): 900 to 1,300 words, 5 to 8 chapters,
a cold open, a clear twist, a closing comment question. Build them mostly from the reusable scenes in
`pipeline/scenes_long.py`: `title_card`, `timeline`, `route`, `facts`, `night_sea`, `night_mountains`,
`desert_night`, `forest_night`, `city_night`, and `photo` with `photo_url`. Write a new scene only for a
reconstruction moment that needs one (mark it `"recon": true`). Always fill the `"thumbnail"` block
(`line1`, `line2`, `badge`, `sub`, and `photo_url` + `credit` when you have a strong photo).

**Photos:** only Wikimedia Commons files licensed CC0, CC BY or CC BY-SA, or public domain. Use the direct
`upload.wikimedia.org` file URL (width 1600 thumbnail is fine), and put the credit in the scene
(`"credit": "Photo: <author>, CC BY-SA 4.0, Wikimedia Commons"`) **and** in the YouTube description.
Never use photos from news sites, stock libraries or other channels.

Every story file needs the full `"youtube"` block (title, description with sources and photo credits,
hashtags, tags, `"synthetic"`: true for documentaries with reconstructions or any AI narration of
realistic scenes, otherwise false).

## 3. Check before filing
- `python3 -c "import json;json.load(open(...))"` on every file.
- For every new scene function: render one still and look at it (see how `pipeline/render.py` builds a frame);
  fix clipped text or overlaps once. Don't render full videos here; GitHub does that.
- Facts: re-check every date, number and name against the sources you opened.

## 4. File for approval
1. `git add stories/pending pipeline && git commit -m "Scripts for <date>" && git push`
   (end the message with the Co-Authored-By and Claude-Session lines if your session gives them).
2. Write one document per story to the approval board with the `ArtifactData` tool:
   artifact `https://claude.ai/artifact/Tr1AxrA54U3jaDX4zet3Lk`, collection `scripts`, doc id = the story id,
   using one `batch` of `set` writes. Fields:
   `date, slot, kind ("short"|"long"), title, hook, script (all narration lines joined with blank lines between scenes),
   minutes, publish_time ("10:00" etc.), sources ([{name, url}]), status: "pending", file: "stories/pending/<file>.json"`.
3. Finish with a short summary: the 6 titles, and anything you could not do.

## Never
- Invent facts, quotes or sources. Present a legend as a legend.
- Cover living private people, recent crimes, health or money claims, or anything aimed at children.
- Touch GitHub secrets, the workflow file, or anything in `stories/published/`.

## Report
Follow `agents/hq_reporting.md` at the start (read the owner's instructions) and at the end of the run.
