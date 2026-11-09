"""Get pinged when your brand shows up in public Telegram channels. Only new mentions, every run.

Usage:
    python monitor.py "your brand"                                   # search all of public Telegram
    python monitor.py "your brand" --channels cointelegraph,binance  # watch these channels, last 2 days

Needs APIFY_TOKEN. SLACK_WEBHOOK_URL sends the new mentions to Slack.
Mentions already reported are remembered in seen.json, so each run only shows what's new.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.request
from decimal import Decimal

from apify_client import ApifyClient

SEARCH_ACTOR = "monkey.d.scraping/telegram-keyword-search-channel-scraper"
EXCLUDE_LIMIT = 1000   # the Actor skips up to 1,000 already-delivered post URLs
STATE_LIMIT = 5000     # how many reported URLs to remember


def load_seen(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_seen(path: str, seen: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen[-STATE_LIMIT:], f)


def build_input(keywords: list[str], channels: list[str], days: int, max_results: int, seen: list[str],
                languages: list[str], min_views: int | None) -> dict:
    """With channels: look for the keywords only in those channels, last `days` days (fresh, no search fee).
    Without channels: search all of public Telegram for the keywords (finds where you're mentioned, posts can be older)."""
    run_input = {"keywords": keywords, "maxResults": max_results}
    if channels:
        run_input.update(collectionMode="keywordInChannels", channels=channels, afterDate=f"{days} days")
    else:
        run_input["collectionMode"] = "keyword"
    if seen:
        run_input["excludePostUrls"] = seen[-EXCLUDE_LIMIT:]
    if languages:
        run_input["postLanguages"] = languages
    if min_views:
        run_input["minViews"] = min_views
    return run_input


def search(run_input: dict, max_cost: float) -> list[dict]:
    apify = ApifyClient(os.environ["APIFY_TOKEN"])
    print(f"searching Telegram for {', '.join(run_input['keywords'])}...", file=sys.stderr)
    run = apify.actor(SEARCH_ACTOR).call(
        run_input=run_input, max_total_charge_usd=Decimal(str(max_cost)), logger=None
    )
    if run is None:
        sys.exit("The Apify run did not start.")
    return list(apify.dataset(run.default_dataset_id).iterate_items())


def new_mentions(items: list[dict], seen: list[str]) -> list[dict]:
    known = set(seen)
    fresh, urls = [], set()
    for item in items:
        url = item.get("messageUrl")
        if not url or url in known or url in urls:
            continue
        urls.add(url)
        fresh.append(item)
    return sorted(fresh, key=lambda i: i.get("publishedAt") or "", reverse=True)


def format_mention(item: dict) -> str:
    text = " ".join((item.get("text") or "(no text)").split())[:200]
    date = (item.get("publishedAt") or "")[:10]
    views = item.get("views")
    meta = f"@{item.get('channelUsername')}, {date}" + (f", {views} views" if views else "")
    return f"- {text} ({meta}) {item.get('messageUrl')}"


def write_csv(items: list[dict], path: str) -> None:
    fields = ["publishedAt", "channelUsername", "views", "matchedKeywords", "text", "messageUrl"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            row = dict(item)
            row["matchedKeywords"] = ", ".join(item.get("matchedKeywords") or [])
            writer.writerow(row)


def post_to_slack(webhook: str, text: str) -> None:
    body = json.dumps({"text": text}).encode()
    request = urllib.request.Request(webhook, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            print(f"Slack answered {response.status}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("keywords", nargs="*", help="words or phrases to watch (or set KEYWORDS, comma-separated)")
    parser.add_argument("--channels", default="", help="comma-separated channels to watch (or set CHANNELS); "
                                                       "leave empty to search all of public Telegram")
    parser.add_argument("--days", type=int, default=2, help="with channels: look back this many days (default 2)")
    parser.add_argument("--max-results", type=int, default=30, help="posts per run (default 30)")
    parser.add_argument("--languages", default="", help="comma-separated ISO codes, e.g. en,it")
    parser.add_argument("--min-views", type=int, default=None, help="skip posts with fewer views")
    parser.add_argument("--max-cost", type=float, default=0.10, help="hard spending cap per run in USD (default 0.10)")
    parser.add_argument("--state", default="seen.json", help="file that remembers reported mentions")
    parser.add_argument("--out", default="new_mentions.csv", help="CSV with this run's new mentions")
    args = parser.parse_args()

    keywords = args.keywords or [k.strip() for k in os.environ.get("KEYWORDS", "").split(",") if k.strip()]
    if not keywords:
        sys.exit("Give at least one keyword, or set KEYWORDS.")
    if not os.environ.get("APIFY_TOKEN"):
        sys.exit("Set APIFY_TOKEN first (Apify console > Settings > API & Integrations).")

    channels_raw = args.channels or os.environ.get("CHANNELS", "")
    channels = [c.strip().lstrip("@") for c in channels_raw.split(",") if c.strip()]
    seen = load_seen(args.state)
    languages = [code.strip() for code in args.languages.split(",") if code.strip()]
    run_input = build_input(keywords, channels, args.days, args.max_results, seen, languages, args.min_views)
    fresh = new_mentions(search(run_input, args.max_cost), seen)

    write_csv(fresh, args.out)
    save_seen(args.state, seen + [i["messageUrl"] for i in fresh])

    if not fresh:
        print("No new mentions.")
        return
    report = f"*{len(fresh)} new Telegram mention(s) of {', '.join(keywords)}*\n" + "\n".join(map(format_mention, fresh))
    if not channels:
        found = sorted({i.get("channelUsername") for i in fresh if i.get("channelUsername")})
        report += "\n\nChannels that mentioned you (add the ones that matter with --channels for daily, fresher checks): " + ", ".join(found)
    print(report)
    if os.environ.get("SLACK_WEBHOOK_URL"):
        post_to_slack(os.environ["SLACK_WEBHOOK_URL"], report)
        print("sent to Slack", file=sys.stderr)


if __name__ == "__main__":
    main()
