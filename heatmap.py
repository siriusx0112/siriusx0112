
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]
OUTPUT = Path("assets/contributions.svg")

COLORS = {
    "NONE": "#080D1B",
    "FIRST_QUARTILE": "#21103D",
    "SECOND_QUARTILE": "#5720A5",
    "THIRD_QUARTILE": "#8538F5",
    "FOURTH_QUARTILE": "#D9B8FF",
}

BACKGROUND = "#080D1B"
TEXT = "#D8F6FF"
MUTED = "#7FA8CB"
CYAN = "#00CFFF"

today = datetime.now(timezone.utc).date()
start = today - timedelta(days=364)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

payload = {
    "query": query,
    "variables": {
        "login": USERNAME,
        "from": f"{start.isoformat()}T00:00:00Z",
        "to": f"{today.isoformat()}T23:59:59Z",
    },
}

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "SiriusX-Nebula-Heatmap",
    },
    method="POST",
)

with urllib.request.urlopen(request, timeout=30) as response:
    result = json.load(response)

if result.get("errors"):
    sys.exit(json.dumps(result["errors"], indent=2))

user = result.get("data", {}).get("user")

if not user:
    sys.exit(f"GitHub user {USERNAME!r} was not found.")

calendar = user["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
total = calendar["totalContributions"]

# SVG geometry
cell = 11
gap = 4
step = cell + gap
left = 38
top = 53
right = 20
bottom = 30

width = left + len(weeks) * step - gap + right
height = top + 7 * step - gap + bottom

svg = [
    (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="title desc">'
    ),
    '<title id="title">SiriusX Nebula Contribution Heatmap</title>',
    f'<desc id="desc">{total} GitHub contributions in the last year.</desc>',
    """
    <defs>
      <radialGradient id="nebula">
        <stop offset="0%" stop-color="#123D70" stop-opacity=".65"/>
        <stop offset="100%" stop-color="#080D1B" stop-opacity="0"/>
      </radialGradient>
      <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
        <feGaussianBlur stdDeviation="2" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    """,
    f'<rect width="{width}" height="{height}" rx="14" fill="{BACKGROUND}"/>',
    f'<rect width="{width}" height="{height}" rx="14" fill="url(#nebula)"/>',
    (
        f'<rect x=".5" y=".5" width="{width - 1}" '
        f'height="{height - 1}" rx="13.5" '
        'fill="none" stroke="#18395B"/>'
    ),
    (
        f'<text x="17" y="22" fill="{CYAN}" '
        'font-family="monospace" font-size="10" letter-spacing="2">'
        'SIRIUSX / CONTRIBUTION LOG</text>'
    ),
    (
        f'<text x="17" y="41" fill="{TEXT}" '
        'font-family="system-ui,sans-serif" font-size="12" font-weight="600">'
        f'{escape(USERNAME)} · {total} contributions in the last year'
        '</text>'
    ),
]

# Decorative stars
for x, y, radius in [
    (0.08, 0.22, 1),
    (0.20, 0.12, 0.7),
    (0.91, 0.25, 0.8),
    (0.74, 0.10, 0.7),
    (0.96, 0.70, 0.8),
    (0.13, 0.88, 0.7),
]:
    svg.append(
        f'<circle cx="{int(width * x)}" cy="{int(height * y)}" '
        f'r="{radius}" fill="#BDEFFF" opacity=".6"/>'
    )

# Weekday labels
for row, label in [(0, "Sun"), (2, "Tue"), (4, "Thu"), (6, "Sat")]:
    y = top + row * step + cell - 1
    svg.append(
        f'<text x="7" y="{y}" fill="{MUTED}" '
        'font-family="system-ui,sans-serif" font-size="9">'
        f'{label}</text>'
    )

# Contribution calendar
last_month = None

for week_index, week in enumerate(weeks):
    for day in week["contributionDays"]:
        day_date = date.fromisoformat(day["date"])

        if not start <= day_date <= today:
            continue

        row = (day_date.weekday() + 1) % 7  # Sunday = 0
        x = left + week_index * step
        y = top + row * step
        level = day["contributionLevel"]
        color = COLORS.get(level, COLORS["NONE"])
        count = day["contributionCount"]

        label = (
            f'{day_date.isoformat()}: {count} contribution'
            f'{"s" if count != 1 else ""}'
        )

        glow = (
            ' filter="url(#glow)"'
            if level == "FOURTH_QUARTILE"
            else ""
        )

        svg.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
            f'rx="2.5" fill="{color}"{glow}>'
            f'<title>{escape(label)}</title></rect>'
        )

        if day_date.day <= 7 and day_date.month != last_month:
            svg.append(
                f'<text x="{x}" y="{top - 8}" fill="{MUTED}" '
                'font-family="system-ui,sans-serif" font-size="9">'
                f'{day_date.strftime("%b")}</text>'
            )
            last_month = day_date.month

# Legend
legend_y = height - 15
svg.append(
    f'<text x="{left}" y="{legend_y}" fill="{MUTED}" '
    'font-family="system-ui,sans-serif" font-size="9">Less</text>'
)

legend_x = left + 31

for level in [
    "NONE",
    "FIRST_QUARTILE",
    "SECOND_QUARTILE",
    "THIRD_QUARTILE",
    "FOURTH_QUARTILE",
]:
    svg.append(
        f'<rect x="{legend_x}" y="{legend_y - 9}" '
        f'width="9" height="9" rx="2" fill="{COLORS[level]}"/>'
    )
    legend_x += 14

svg.append(
    f'<text x="{legend_x + 2}" y="{legend_y}" fill="{MUTED}" '
    'font-family="system-ui,sans-serif" font-size="9">More</text>'
)
svg.append("</svg>")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(svg), encoding="utf-8")

print(f"Generated {OUTPUT} with {total} contributions.")
