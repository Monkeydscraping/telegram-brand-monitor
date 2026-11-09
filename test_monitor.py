"""Offline tests: no Apify or Slack calls. Run with `python -m pytest -q`."""

import json

import monitor


def item(n, date="2026-11-08T10:00:00Z", **extra):
    return {"messageUrl": f"https://t.me/chan/{n}", "channelUsername": "chan", "publishedAt": date,
            "text": f"post {n}", **extra}


def test_channel_mode_skips_already_seen_posts():
    seen = [f"https://t.me/chan/{n}" for n in range(1500)]
    run_input = monitor.build_input(["acme"], ["cointelegraph"], 2, 30, seen, ["en"], 100)
    assert run_input["collectionMode"] == "keywordInChannels"
    assert run_input["channels"] == ["cointelegraph"] and run_input["afterDate"] == "2 days"
    assert len(run_input["excludePostUrls"]) == 1000
    assert run_input["excludePostUrls"][-1] == "https://t.me/chan/1499"
    assert run_input["postLanguages"] == ["en"] and run_input["minViews"] == 100


def test_search_mode_has_no_date_window_and_no_exclusions_on_first_run():
    run_input = monitor.build_input(["acme"], [], 2, 30, [], [], None)
    assert run_input["collectionMode"] == "keyword"
    assert "afterDate" not in run_input and "excludePostUrls" not in run_input


def test_only_new_mentions_newest_first():
    items = [item(1, "2026-11-07T00:00:00Z"), item(2, "2026-11-08T00:00:00Z"), item(2), {"text": "no url"}]
    fresh = monitor.new_mentions(items, ["https://t.me/chan/3"])
    assert [i["messageUrl"] for i in fresh] == ["https://t.me/chan/2", "https://t.me/chan/1"]
    assert monitor.new_mentions(items, ["https://t.me/chan/1", "https://t.me/chan/2"]) == []


def test_state_round_trip(tmp_path):
    path = tmp_path / "seen.json"
    assert monitor.load_seen(str(path)) == []
    monitor.save_seen(str(path), [f"u{n}" for n in range(6000)])
    saved = json.loads(path.read_text())
    assert len(saved) == monitor.STATE_LIMIT and saved[-1] == "u5999"


def test_format_and_csv(tmp_path):
    mention = item(7, views="4.9K", matchedKeywords=["acme"])
    line = monitor.format_mention(mention)
    assert "@chan, 2026-11-08, 4.9K views" in line and line.endswith("https://t.me/chan/7")
    out = tmp_path / "m.csv"
    monitor.write_csv([mention], str(out))
    assert "acme" in out.read_text(encoding="utf-8")
