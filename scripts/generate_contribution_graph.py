import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path


API_URL = "https://api.github.com/graphql"
OUTPUT_FILE = Path("assets/contribution-graph.svg")
NUMBER_OF_DAYS = 30


def get_contributions():
    token = os.environ["PROFILE_TOKEN"]
    username = os.environ.get("GITHUB_USERNAME", "MaorMalka")

    today = datetime.now(timezone.utc)
    start = today - timedelta(days=NUMBER_OF_DAYS - 1)

    query = """
    query($username: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $username) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
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
            "username": username,
            "from": start.isoformat(),
            "to": today.isoformat(),
        },
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-contribution-graph",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    if "errors" in result:
        raise RuntimeError(result["errors"])

    calendar = result["data"]["user"]["contributionsCollection"][
        "contributionCalendar"
    ]

    days = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append(
                {
                    "date": day["date"],
                    "count": day["contributionCount"],
                }
            )

    days.sort(key=lambda item: item["date"])
    return days[-NUMBER_OF_DAYS:], calendar["totalContributions"]


def create_svg(days, total):
    width = 1000
    height = 360

    left = 70
    right = 30
    top = 80
    bottom = 65

    graph_width = width - left - right
    graph_height = height - top - bottom

    highest = max([day["count"] for day in days] + [1])

    points = []

    for index, day in enumerate(days):
        x = left + index * graph_width / max(len(days) - 1, 1)
        y = top + graph_height - (
            day["count"] / highest * graph_height
        )

        points.append((x, y, day))

    line_points = " ".join(
        f"{x:.2f},{y:.2f}" for x, y, _ in points
    )

    grid = []

    for index in range(5):
        y = top + index * graph_height / 4
        value = round(highest * (4 - index) / 4)

        grid.append(
            f'<line x1="{left}" y1="{y}" '
            f'x2="{width - right}" y2="{y}" '
            f'stroke="#243247" stroke-width="1"/>'
        )

        grid.append(
            f'<text x="{left - 15}" y="{y + 5}" '
            f'fill="#8B9BB4" font-size="13" '
            f'text-anchor="end">{value}</text>'
        )

    labels = []

    for index, (x, _, day) in enumerate(points):
        if index % 5 == 0 or index == len(points) - 1:
            date_text = datetime.strptime(
                day["date"], "%Y-%m-%d"
            ).strftime("%d/%m")

            labels.append(
                f'<text x="{x}" y="{height - 30}" '
                f'fill="#8B9BB4" font-size="12" '
                f'text-anchor="middle">{date_text}</text>'
            )

    circles = []

    for x, y, day in points:
        circles.append(
            f'<circle cx="{x}" cy="{y}" r="4" '
            f'fill="#BB86FC">'
            f'<title>{escape(day["date"])}: '
            f'{day["count"]} contributions</title>'
            f'</circle>'
        )

    generated_time = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
        width="{width}" height="{height}"
        viewBox="0 0 {width} {height}">

      <rect width="100%" height="100%" rx="18" fill="#0D1117"/>

      <text x="{width / 2}" y="38"
        fill="#E6EDF3" font-size="23"
        font-family="Arial, sans-serif"
        font-weight="bold" text-anchor="middle">
        Maor Malka's Contribution Graph
      </text>

      <text x="{width / 2}" y="62"
        fill="#8B9BB4" font-size="13"
        font-family="Arial, sans-serif"
        text-anchor="middle">
        {total} contributions during the selected period
      </text>

      {''.join(grid)}

      <polyline
        points="{line_points}"
        fill="none"
        stroke="#8A2BE2"
        stroke-width="4"
        stroke-linejoin="round"
        stroke-linecap="round"/>

      {''.join(circles)}
      {''.join(labels)}

      <text x="{width - 25}" y="{height - 8}"
        fill="#536174" font-size="10"
        font-family="Arial, sans-serif"
        text-anchor="end">
        Updated {generated_time}
      </text>
    </svg>
    """

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(svg, encoding="utf-8")


def main():
    days, total = get_contributions()
    create_svg(days, total)
    print(f"Graph created at {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
