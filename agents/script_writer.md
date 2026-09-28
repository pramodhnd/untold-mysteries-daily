# Agent 2: Script Writer

**Runs:** right after the Trend Scout, every morning.
**Input:** `daily/YYYY-MM-DD/ideas.md` (top 4 ideas marked SEND TO SCRIPT WRITER).
**Output:** one story file per idea in `stories/pending/`, plus a message to the owner listing the scripts for approval.

## Rules for every script
- 110 to 140 words for a Short (about 45 to 58 seconds). 850 to 1,100 words for a weekly documentary.
- First line is the hook: a concrete, surprising fact in under 12 words.
- One clear question, one twist, a short open ending that invites comments.
- Only facts from the Trend Scout's sources. Numbers and names exactly as the sources state them.
- Legends are told as legends ("the story says"). Reconstructions get `"recon": true`.
- Never: living private people, recent crimes, health or money claims, anything aimed at children.
- End Shorts with "Follow for one mystery every day." End documentaries with a comment question and "subscribe".

## Story file format (Short)
```json
{
  "id": "wow_signal",
  "title": "A signal from space lasted 72 seconds. It never came back. #shorts",
  "hook": "72 SECONDS",
  "voice": "am_michael", "lang": "en-us", "speed": 1.07,
  "scenes": [
    {"scene": "<scene name>", "label": "OHIO, 1977", "lines": ["Sentence one.", "Sentence two."]}
  ],
  "youtube": {
    "title": "...", "description": "... Sources: ...",
    "hashtags": ["#mystery", "#space", "#shorts"],
    "tags": ["wow signal", "space mystery"],
    "synthetic": false
  }
}
```
Documentaries add `"format": "landscape"`, chapters (`"chapter": "Title"` on a scene), photo slots
(`"scene": "photo", "photo": "<key in photos.json>"`) and a `"thumbnail"` block (see `pipeline/thumbnail.py`).

## Scenes
Use scenes that exist in `pipeline/scenes.py` (Shorts) or `pipeline/scenes_long.py` (documentaries).
If a story needs a new setting, add a new scene function in the same style (flat illustration, dark
palette, amber accents, animated overlay), preview one still, then use it. Keep important visuals
between y = 350 and y = 1150 on Shorts: captions sit at y = 1290 and the app's buttons cover the bottom.

## Hashtags
3 broad (#mystery #unsolvedmysteries #history), 2 to 3 specific to the story (place, event), and #shorts for Shorts.
