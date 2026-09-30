# IpoBodh — IPO Terminal

The IPO section moved out of `devrajai/ArthaSaar` into its own repository.

- Live terminal: https://devrajai.github.io/IpoBodh/
- `index.html` + `scripts/ipo-*.js` — the liquid-glass IPO terminal UI
- `data/` — IPO data (issues, GMP, subscriptions, market data, news, filings ...)
- `scripts/*.py` — the collectors/builders that regenerate `data/`
- `.github/workflows/` — the scheduled jobs that refresh the data

The terminal is a self-contained static site: all asset paths are relative, so it serves from the repo root.

Secrets the workflows expect (add them in this repo's Settings > Secrets): `TG_TOKEN`, `TG_CHAT_ID`,
`GOOGLE_SHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `IPOGURU_API_KEY`.
