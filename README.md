# Untold Mysteries Daily: automated channel

Everything that makes the channel run. Claude writes the stories; GitHub Actions renders and uploads them.

## How a day works

1. **00:52 IST (night): Trend Scout + Script Writer** (Claude scheduled task, backup run 03:52) research trending mysteries, write 4 Shorts and 2 documentaries, and save them to `stories/pending/`.
2. **Around 21:00 IST, you approve** on the Approval Board (about 15 minutes on your phone). The Approval Sync runs hourly 21:05 to 05:05 and starts an upload if GitHub skipped one.
3. Approved stories move to `stories/approved/`. **GitHub Actions** then publishes one per hour from 21:15 to 05:15 IST (all inside 21:15-06:15). Each run:
   - renders each video (free voice, original illustrations and music),
   - makes the thumbnail for documentaries,
   - uploads it to YouTube with title, description, hashtags, chapters and the AI disclosure,
   - records it in `data/published.csv` and moves the story to `stories/published/`.
4. **Monday: Analyst** reads the channel stats and tells the Trend Scout what to make more of.

## Folders

| Folder | What's inside |
|---|---|
| `agents/` | Plain-language instructions for each agent |
| `pipeline/` | Video maker (`render.py` Shorts, `render_long.py` documentaries), thumbnails, YouTube uploader |
| `stories/` | `pending/` → `approved/` → `published/` |
| `assets/fonts/` | Poppins and Lora (SIL Open Font License) |
| `data/` | Log of everything published |

## One-time setup (owner)

1. **GitHub**: sign in, then connect GitHub to Claude (claude.ai → Settings → Connectors → GitHub).
2. **Google Cloud** (Claude drives this in the browser; you click Allow):
   - create a project, enable *YouTube Data API v3*,
   - OAuth consent screen: External, publish the app (so the sign-in doesn't expire after 7 days),
   - create an OAuth client (Desktop app).
3. **Get the refresh token** with Google's OAuth Playground using your client ID and secret (scopes `youtube.upload` and `youtube`), signing in to the channel's account.
4. **Paste three secrets** into GitHub → repo → Settings → Secrets and variables → Actions:
   `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`. Only you handle these values.
5. **Privacy**: videos upload as `private` until Google's free API audit approves the project
   (YouTube's rule for new API projects). Until then, publishing is one tap in YouTube Studio.
   After approval, set the repository variable `YT_PRIVACY` to `public`.

## Testing without uploading

```
DRY_RUN=1 python3 pipeline/publish_pending.py
```
