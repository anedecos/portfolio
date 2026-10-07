"""Refresh the anonymous, publicly visible GitHub contribution calendar."""

import argparse
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, urlopen

USERNAME = "anedecos"
SOURCE = f"https://github.com/users/{USERNAME}/contributions"
OUTPUT = Path(__file__).resolve().parents[1] / "contributions.json"


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.labels = {}
        self.total_text = ""
        self.capture = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-date" in attrs and "ContributionCalendar-day" in attrs.get("class", "").split():
            cell_id = attrs["id"]
            if cell_id in self.cells:
                raise ValueError("Duplicate calendar cell")
            self.cells[cell_id] = {"date": attrs["data-date"], "level": int(attrs["data-level"])}
        if tag == "h2" and attrs.get("id") == "js-contribution-activity-description":
            self.capture = (tag, None)
            self.text = []
        elif tag == "tool-tip" and attrs.get("for"):
            self.capture = (tag, attrs["for"])
            self.text = []

    def handle_data(self, data):
        if self.capture:
            self.text.append(data)

    def handle_endtag(self, tag):
        if self.capture and tag == self.capture[0]:
            text = " ".join("".join(self.text).split())
            if tag == "h2":
                self.total_text = text
            else:
                self.labels[self.capture[1]] = text
            self.capture = None


def parse_calendar(html, now=None):
    now = now or datetime.now(timezone.utc)
    parser = CalendarParser()
    parser.feed(html)
    total_match = re.fullmatch(r"([\d,]+) contributions? in the last year", parser.total_text)
    if not total_match or not 350 <= len(parser.cells) <= 380:
        raise ValueError("GitHub did not return a complete yearly contribution calendar")
    days = []
    for cell_id, cell in parser.cells.items():
        match = re.match(r"^(No|[\d,]+) contributions? on ", parser.labels.get(cell_id, ""))
        if not match:
            raise ValueError("Missing or unrecognized contribution count")
        count = 0 if match[1] == "No" else int(match[1].replace(",", ""))
        day = date.fromisoformat(cell["date"])
        level = cell["level"]
        if day.isoformat() != cell["date"] or not 0 <= level <= 4 or (count == 0) != (level == 0):
            raise ValueError("Invalid calendar cell")
        days.append({"date": day.isoformat(), "count": count, "level": level})
    days.sort(key=lambda day: day["date"])
    dates = [date.fromisoformat(day["date"]) for day in days]
    if any(b - a != timedelta(days=1) for a, b in zip(dates, dates[1:])):
        raise ValueError("Calendar dates must be unique and consecutive")
    if abs((dates[-1] - now.date()).days) > 1:
        raise ValueError("GitHub returned an outdated calendar")
    total = int(total_match[1].replace(",", ""))
    if sum(day["count"] for day in days) != total:
        raise ValueError("Calendar counts do not match the public total")
    return {"username": USERNAME, "source": SOURCE, "retrievedAt": now.isoformat(), "total": total, "days": days}


def refresh(output=OUTPUT, fetch=None):
    def fetch_public_html():
        request = Request(SOURCE, headers={"User-Agent": "anedecos-portfolio-calendar", "Accept-Language": "en"})
        with urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise ValueError("GitHub calendar request failed")
            return response.read(2_000_001).decode("utf-8")

    fetch = fetch or fetch_public_html
    for attempt in range(3):
        try:
            html = fetch()
            if len(html) > 2_000_000:
                raise ValueError("Unexpected calendar response size")
            data = parse_calendar(html)
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    temporary = output.with_suffix(".json.tmp")
    try:
        temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Updated public calendar: {data['total']:,} contributions, {len(data['days'])} days")
    return data


if __name__ == "__main__":
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--output", type=Path, default=OUTPUT)
    options = arguments.parse_args()
    try:
        refresh(options.output)
    except Exception as error:
        print(f"Calendar refresh failed; the previous snapshot is unchanged: {error}", file=sys.stderr)
        sys.exit(1)
