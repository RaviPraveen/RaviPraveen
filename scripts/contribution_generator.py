#!/usr/bin/env python3
"""Render GitHub public contribution calendar to a repository-owned SVG."""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

USER = "RaviPraveen"
OUT = Path("assets/contributions.svg")
COLORS = ["#131C2C", "#103F63", "#087CAC", "#06BCE4", "#53E9FF"]
LEVELS = dict(NONE=0, FIRST_QUARTILE=1, SECOND_QUARTILE=2, THIRD_QUARTILE=3, FOURTH_QUARTILE=4)
QUERY = """query($login:String!,$from:DateTime!,$to:DateTime!){
user(login:$login){contributionsCollection(from:$from,to:$to){
contributionCalendar{weeks{contributionDays{date contributionCount contributionLevel weekday}}}
}}}"""

def get_calendar():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN absent; refusing to fabricate contributions")
    now = dt.datetime.now(dt.timezone.utc)
    data = json.dumps({"query": QUERY, "variables": {
        "login": USER,
        "from": (now - dt.timedelta(days=364)).isoformat(),
        "to": now.isoformat(),
    }}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "RaviPraveen-Profile-Contributions"})
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(str(result["errors"]))
    cal = ((result.get("data") or {}).get("user") or {}).get("contributionsCollection") or {}
    cal = cal.get("contributionCalendar")
    if not cal or not cal.get("weeks"):
        raise RuntimeError("GitHub returned no calendar; keeping previous image")
    return cal

def render(calendar):
    weeks = calendar["weeks"]
    if not 45 <= len(weeks) <= 54:
        raise ValueError("Unexpected week count: " + str(len(weeks)))
    x0, y0, step, cell, width, height = 84, 94, 20, 15, 1212, 290
    parts = [f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="GitHub contributions in the last 12 months"><title>Ravi Praveen: public GitHub contributions, last 12 months</title><style>text{{font-family:Arial,sans-serif;fill:#B5C4D8}}.head{{font-size:21px;font-weight:bold;fill:#E8F7FF}}.sub{{font-size:13px;fill:#879AAF}}.month,.day{{font-size:13px}}</style><rect x="1" y="1" width="{width-2}" height="{height-2}" rx="18" fill="#05080E" stroke="#334155" stroke-width="1.2"/><text x="34" y="40" class="head">THE CODE CONSTELLATION</text><text x="{width-34}" y="39" text-anchor="end" class="sub">LAST 12 MONTHS · GITHUB ACTIVITY</text>"""]
    last_month = None
    n = 0
    for w, week in enumerate(weeks):
        days = week.get("contributionDays") or []
        if days:
            month = days[0]["date"][0:7]
            if month != last_month:
                label = dt.date.fromisoformat(days[0]["date"]).strftime("%b")
                parts.append(f'<text x="{x0+w*step}" y="74" class="month">{label}</text>')
                last_month = month
        for day in days:
            n += 1
            level = LEVELS[day["contributionLevel"]]
            dayx, dayy = x0 + w*step, y0 + int(day["weekday"])*step
            date, count = day["date"], int(day["contributionCount"])
            parts.append(f'<rect x="{dayx}" y="{dayy}" width="{cell}" height="{cell}" rx="3" fill="{COLORS[level]}" stroke="#324258" stroke-width=".85"><title>{date}: {count} contributions</title></rect>')
    if n < 350:
        raise RuntimeError("Incomplete calendar; preserving old SVG")
    for label, row in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
        parts.append(f'<text x="30" y="{y0+row*step+12}" class="day">{label}</text>')
    for i, color in enumerate(COLORS):
        parts.append(f'<rect x="{width-200+i*27}" y="245" width="15" height="15" rx="3" fill="{color}" stroke="#324258" stroke-width=".8"/>')
    parts.append(f'<text x="{width-256}" y="258" class="sub">LESS</text><text x="{width-34}" y="258" text-anchor="end" class="sub">MORE</text><text x="34" y="258" class="sub">Public contributions · Updated automatically each day</text></svg>')
    svg = "".join(parts)
    ET.fromstring(svg)
    return svg

def main():
    out = render(get_calendar())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    print("Updated", OUT, len(out), "bytes")

if __name__ == "__main__":
    main()
