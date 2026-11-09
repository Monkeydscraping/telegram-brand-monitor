# telegram-brand-monitor

Know when your brand, product or competitor shows up in public Telegram channels. Every run tells you only what's new since last time, in your terminal or in Slack. It runs daily on GitHub Actions for free, no server, no Telegram account.

Real output, keyword `bitcoin`, two channels, second run of the day:

```
*3 new Telegram mention(s) of bitcoin*
- 🚨 MARKET: Stock futures slip as investors await US midterm results... Bitcoin drops more than 1% (@cointelegraph, 2026-11-04)
- 🇺🇸 INSIGHT: Bitcoin has gained an average median return of 63% in the 12 months following every US midterm election... (@cointelegraph, 2026-11-03)
- 🚨 JUST IN: Brazil's Mercado Bitcoin halts deposits and withdrawals after a security incident... (@cointelegraph, 2026-11-02)
```

The five mentions from the first run weren't repeated. That's the point.

## Two ways to watch

**1. Watch the channels that matter (recommended).** You list the channels, it checks them for your keywords over the last few days. Fresh, cheap, no noise.

```bash
python monitor.py "your brand" --channels cointelegraph,whale_alert_io --days 2
```

**2. Search all of public Telegram.** Good for finding *where* people talk about you; posts can be older and some channels are spammy. At the end it lists the channels that mentioned you, so you can copy the good ones into option 1.

```bash
python monitor.py "your brand"
```

The search runs on [Telegram Keyword Search](https://apify.com/monkey.d.scraping/telegram-keyword-search-channel-scraper), an Apify Actor: public channels only, literal matches in the post text, no login. Mentions already reported live in `seen.json` and are never shown twice; when you watch channels, the Actor skips them too, so you don't pay for them again.

## Run it

```bash
git clone https://github.com/Monkeydscraping/telegram-brand-monitor
cd telegram-brand-monitor
pip install -r requirements.txt

export APIFY_TOKEN=...            # apify.com > Settings > API & Integrations
export SLACK_WEBHOOK_URL=...      # optional

python monitor.py "your brand" --channels channel_one,channel_two
```

| Flag | Default | What it does |
| --- | --- | --- |
| `--channels` | none | channels to watch; empty = search all of Telegram |
| `--days` | 2 | with channels, how far back to look |
| `--max-results` | 30 | posts per run |
| `--languages` | any | e.g. `en,it`, keep only these languages |
| `--min-views` | none | skip small posts |
| `--max-cost` | 0.10 | hard spending cap per run, in USD |
| `--state` | `seen.json` | memory of what was already reported |
| `--out` | `new_mentions.csv` | this run's new mentions |

## Run it every day, for free

The repo ships with `.github/workflows/daily-monitor.yml`.

1. Fork this repo, open the Actions tab of your fork and enable workflows (GitHub turns them off in forks).
2. Settings > Secrets and variables > Actions: add the secret `APIFY_TOKEN` and, optionally, `SLACK_WEBHOOK_URL`.
3. Add the variable `KEYWORDS` (comma-separated) and, recommended, `CHANNELS`.
4. Done. It runs every day at 08:00 UTC. The list of reported mentions is kept in the Actions cache, not in your repo, so your fork doesn't publish what you're tracking.

## What it costs

- **Watching channels:** $0.001 per new mention, plus a tiny start fee. 30 new mentions a day ≈ 3 cents. Days with nothing new cost almost nothing.
- **Searching all of Telegram:** same per mention, plus $0.005 per search page checked.
- `--max-cost` stops the run at your cap, whatever happens. New Apify accounts get free monthly credits.

## FAQ

**Private channels or groups?** No. Public channels only.

**Does it match "brand" inside "brandnew"?** It matches the literal text you give. Use quotes and operators like `acme AND coffee` or `"acme coffee" -jobs`, see the Actor page.

**Can I watch several brands?** Yes: `python monitor.py acme "acme coffee" competitorx`.

---

Made by [Monkey.D.Scraping](https://github.com/Monkeydscraping). More examples: [social-comments-sentiment](https://github.com/Monkeydscraping/social-comments-sentiment), [facebook-groups-digest](https://github.com/Monkeydscraping/facebook-groups-digest). Something broke? Open an issue.
