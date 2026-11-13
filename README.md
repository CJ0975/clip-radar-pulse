# Clip Radar Pulse

A public helper for [clip-radar](https://github.com/CJ0975/clip-radar) (private).
It exists for one reason: **a scanner cannot notice its own silence.**

GitHub runs scheduled workflows on a best-effort queue. Runs can be delayed by
tens of minutes, dropped entirely, or — on a brand-new private repository — never
registered at all. That is exactly what happened here: clip-radar's first six
hours produced zero `schedule` runs while `workflow_dispatch` worked fine.

## What this does

Once an hour (`17 * * * *`), [`tools/pulse.py`](tools/pulse.py):

1. reads `health.last_run` out of the radar's committed `data/state.json`;
2. if the last scan is **less than 3.5 hours old** → does nothing;
3. if it is **older** → `POST /repos/CJ0975/clip-radar/dispatches` with
   `event_type: pulse`, which starts a scan immediately;
4. if it cannot read the state file or the dispatch fails → **says so on
   Telegram**, because a backstop that fails silently is worse than none.

Because the radar dedupes by campaign id, an extra poke can never produce a
duplicate alert. The worst case is one wasted scan.

## Secrets

| Secret | Why |
|---|---|
| `RADAR_PAT` | Fine-grained token with access to clip-radar, to read the state file and dispatch |
| `TELEGRAM_BOT_TOKEN` | Only used to report *pulse failures* |
| `TELEGRAM_CHAT_ID` | Where those failure reports go |

Nothing in this repository is secret, and fork pull requests never receive
secrets.

## Manual test

**Actions → Pulse → Run workflow → force: true** starts a scan regardless of how
fresh the radar looks, which is the quickest way to check the whole chain.

Licence: do whatever you like.
