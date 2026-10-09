# Shielded Nakas dashboard

French-language market dashboard for the Shielded Nakas Bitcoin ordinals collection on Ord Dropz.

**GitHub Pages:** https://3ajfr.github.io/shielded-nakas-dashboard/

The site is one static page. GitHub Actions rebuilds it about every 10 minutes from public read-only APIs and publishes it with the official GitHub Pages actions. There is no server and no API key.

## Charts

- Sale candles (open / high / low / close) on 1 hour, 4 hour, and 1 day buckets, in Europe/Paris time
- Median sale line, and RSI(14) (Wilder) on that median, with 30 and 70 lines
- Volume bars and the number of sales
- Live floor (lowest current ask) once `data/floor_history.csv` has points
- Before that history, a dotted hourly lowest-sale line labelled **APPROXIMATION** (sales under 5,000 sats are excluded)
- Header: floor, 24h volume in BTC and USD, 24h sales, 24h median change versus the previous 24h, live listed count
- Filters: Tous, Legendary+Epic, sub100, sub1k
- Log scale toggle
- The page reloads itself every 300 seconds

Listings marked stale or cancelling by the live listings feed are left out of the floor.

## Data sources

All endpoints are public. The workflow uses `GITHUB_TOKEN` only to push floor history and to deploy Pages.

- Collection, inscriptions, and trades: `https://backend-secondary-market-production.up.railway.app/api/secondary`
- Live listings: `https://shielded-mint-server-production.up.railway.app/api/shielded/listings`
- BTC/USD: mempool.space, then CoinGecko

Inscriptions supply the rarity tier, rank, and Shielded # used by the filters. The build fetches that payload on every run (about 4 MB, one response). A copy is kept in the gitignored `cache/` directory for local reruns. It is not committed.

Each run appends the live floors to `data/floor_history.csv`. The workflow commits that file back to `main`, so the real floor series accumulates. The dotted approximation is the period before the first saved floor.

## Build locally

Python 3.11 or newer, standard library only. `Europe/Paris` needs the system timezone data (present on Ubuntu and on GitHub-hosted runners).

```bash
python3 build_dashboard.py
```

The script writes `site/index.html`. Open that file in a browser. Plotly loads from a CDN (jsDelivr, with cdn.plot.ly as fallback).

## GitHub Actions

[`.github/workflows/pages.yml`](.github/workflows/pages.yml) runs on:

- a cron every 10 minutes (`*/10 * * * *`)
- `workflow_dispatch`
- a push to `main` (a commit that only updates `data/floor_history.csv` does not start another run)

The job builds `site/`, commits `data/floor_history.csv` when a new floor row was added, and deploys with `actions/configure-pages` (`enablement: true`), `actions/upload-pages-artifact`, and `actions/deploy-pages`. The workflow grants the token `pages: write`, `id-token: write`, and `contents: write`.

### Repository setting

Pages is disabled on this repository today. `enablement: true` is in the workflow, and it still cannot create the site: GitHub does not let the Actions `GITHUB_TOKEN` create a Pages site. Doing that would require a personal access token or a GitHub App with `administration: write`, and this repo stores no secrets.

After this workflow is on `main`:

1. Open **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.

That is the setting to change.

Leave **Settings → Actions → General → Workflow permissions** on the default (read access for repository contents and packages). This workflow's `permissions` block grants `contents: write`, `pages: write`, and `id-token: write` for its own job, which a personal-account repository allows.

The 10-minute schedule starts only once the workflow file is on `main`. GitHub can start a scheduled run a few minutes after the cron time. The first run stops at the Pages step until **Source** is **GitHub Actions**. Then use **Actions → Build and deploy dashboard → Run workflow**.

The history update is a direct push to `main`. A ruleset that rejects direct pushes to `main` would block that commit and the floor series would stop growing.

The page shows public market data for information. It is not financial advice.
