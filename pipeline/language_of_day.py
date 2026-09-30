"""Which language today's videos are in.

Owner's decision (30 Sep 2026): English only. The Hindi support in the renderer stays available but unused;
to bring back alternating days, set ALTERNATE = True.
Usage: python3 pipeline/language_of_day.py [YYYY-MM-DD]   -> prints "en" or "hi"
"""
import datetime
import sys

ANCHOR = datetime.date(2026, 9, 30)  # an English day
ALTERNATE = False


def language_for(day):
    if not ALTERNATE:
        return "en"
    return "en" if (day - ANCHOR).days % 2 == 0 else "hi"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        d = datetime.date.fromisoformat(sys.argv[1])
    else:
        d = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).date()
    print(language_for(d))
