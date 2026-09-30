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

## Lively, not a slideshow (owner's request, 30 Sep 2026)
- The renderer starts a **new camera shot on every narration line** (snap zooms to details, drift, shake) and
  uses zoom, flash and whip transitions between scenes. So write **short lines**: one idea per line,
  8 to 18 words. A Short should have **9 to 14 lines across 4 to 6 scenes**; don't put 5 lines on one scene.
- Change scene whenever the place, time or object changes. Pick scenes with visible details to zoom into.
- A documentary scene should rarely run longer than 4 lines.

## Real photo opener (required on every video)
Every video opens on one real, open-license photograph of the mystery (the place, the object, the people's
memorial, the original document), stamped "TRUE STORY" / "सच्ची कहानी", while the first line is spoken.
Add an `"opener"` block to every story:
```json
"opener": {
  "file": ["File:Nazca Lines Hummingbird.jpg", "File:Nazca-lineas-colibri-c01.jpg"],
  "search": "Nazca lines hummingbird",
  "caption": "The Hummingbird, Nazca Lines, Peru"
}
```
- `file`: 1 to 3 exact Wikimedia Commons file names, best first. Find them with web search limited to
  `commons.wikimedia.org` (the cloud sandbox cannot open Commons directly). Prefer real photographs over
  drawings, maps or diagrams; no SVG.
- `search`: a fallback Commons search used only if none of the files qualify.
- `caption`: what the photo shows, in the video's language, under 40 characters.
- The renderer (on GitHub) checks each file's license at render time and only uses CC0, CC BY, CC BY-SA or
  public domain; it writes the credit on screen and adds it to the YouTube description automatically.
  If you already know a direct `upload.wikimedia.org` URL and its license, `"photo_url"` + `"credit"` also work.
- Documentaries: the opener photo is also used as the thumbnail background when `thumbnail` has no photo.
- Mid-video photo scenes may use the same fields: `{"scene": "photo", "photo_file": [...], "photo_search": "..."}`.

## Hindi days
English and Hindi alternate by date: `python3 pipeline/language_of_day.py <YYYY-MM-DD>` prints `en` or `hi`.
On a Hindi day every story (all 6) is written in Hindi:
- `"lang": "hi"`, `"voice": "hm_omega"`, `"speed": 1.0`.
- Narration in simple spoken Hindi (Hindustani, the way a good Hindi news anchor tells a story), in Devanagari.
  Short sentences. End sentences with "।".
- Write every number and year as Hindi words ("उन्नीस सौ सतहत्तर", "बहत्तर सेकंड"), and English names
  in Devanagari ("बिग ईयर", "जेरी ईमन"), so the voice reads them correctly. Scene `label`s and the `hook`
  may use digits ("72 सेकंड").
- Shorts end with "रोज़ एक सच्चे रहस्य के लिए फ़ॉलो करें।"; documentaries end with a comment question and
  "चैनल को सब्सक्राइब करें।"
- `youtube.title`: Hindi, with one English search phrase, e.g. "72 सेकंड का रहस्यमयी सिग्नल | Wow Signal Mystery in Hindi #shorts".
  Description in Hindi first, then the sources (source titles may stay in English). Hashtags add `#hindi`
  and `#रहस्य`; tags add Hindi and English keywords ("rahasya", "mystery in hindi").
- Add `youtube.localizations.en` with an English `title` and `description`, so English viewers see it too.
  On English days add `youtube.localizations.hi` with a Hindi title and description.
- Word counts: Hindi Shorts 120 to 160 words (Hindi words are shorter), documentaries 1,000 to 1,450.

## Story file format (Short)
```json
{
  "id": "wow_signal",
  "title": "A signal from space lasted 72 seconds. It never came back. #shorts",
  "hook": "72 SECONDS",
  "voice": "am_michael", "lang": "en-us", "speed": 1.07,
  "opener": {"file": ["File:..."], "search": "...", "caption": "..."},
  "scenes": [
    {"scene": "<scene name>", "label": "OHIO, 1977", "lines": ["Sentence one.", "Sentence two."]}
  ],
  "youtube": {
    "title": "...", "description": "... Sources: ...",
    "hashtags": ["#mystery", "#space", "#shorts"],
    "tags": ["wow signal", "space mystery"],
    "synthetic": false,
    "localizations": {"hi": {"title": "...", "description": "..."}}
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
