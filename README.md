# clip-radar-pulse — retired

This hourly watchdog used to live here so that its Actions minutes would be
free. It read the private clip-radar repo with a fine-grained personal access
token, which expired on 2026-11-19: every hourly check since then failed with
HTTP 401 and messaged about it, which is the opposite of a safety net.

The watchdog now lives inside the radar repo as
[`heartbeat.yml`](https://github.com/CJ0975/clip-radar/blob/main/.github/workflows/heartbeat.yml),
where it reads the state file from the same checkout and authorises with the
run's own `GITHUB_TOKEN`. Nothing to rotate, nothing to expire.

This repository can be deleted.
