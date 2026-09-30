"""Which language today's videos are in: English and Hindi on alternate India dates.

2026-09-30 is English, 2026-10-01 Hindi, 2026-10-02 English, and so on.
Usage: python3 pipeline/language_of_day.py [YYYY-MM-DD]   -> prints "en" or "hi"
"""
import datetime
import sys

ANCHOR = datetime.date(2026, 9, 30)  # an English day


def language_for(day):
    return "en" if (day - ANCHOR).days % 2 == 0 else "hi"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        d = datetime.date.fromisoformat(sys.argv[1])
    else:
        d = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).date()
    print(language_for(d))
