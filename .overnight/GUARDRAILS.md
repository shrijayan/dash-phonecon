# Overnight Auto-Research — Guardrails (READ THIS FIRST, every cycle)

This repo clone (`dash-phonecon-overnight`, branch `overnight/auto-research`)
is a **sandboxed workspace**, isolated from the user's real working copy at
`/home/shrijayan/projects/dash-phonecon`. It exists so an unattended
overnight loop of persona-driven agents can propose and build features
without any human watching, while the user sleeps (started ~2:15 AM IST,
hard stop 8:00 AM IST).

## Hard rules (non-negotiable, in every persona's prompt)

1. **Never push to `main`.** Only ever commit and push to
   `overnight/auto-research` on the `origin` remote. `release.yml` and
   `deploy-docs.yml` both trigger only on pushes to `main` — staying off
   `main` means zero real GitHub Releases, zero Pages redeploys, and zero
   app-store-style side effects happen unattended overnight.
2. **Never touch secrets.** Don't read, print, modify, or reference
   `RELEASE_KEYSTORE_BASE64`/`RELEASE_KEYSTORE_PASSWORD`/`RELEASE_KEY_ALIAS`/
   `RELEASE_KEY_PASSWORD`, `.env` files, or any credential. The known
   Android signing issue is explicitly OUT OF SCOPE for this loop — do not
   attempt to fix, work around, or touch keystore/signing config.
2b. **Never run `gh` commands that mutate the real repo's non-branch
   state** — no `gh release`, no `gh repo edit`, no `gh secret set/delete`,
   no `gh workflow run` against `release.yml`/`deploy-docs.yml`. Reading
   (`gh run list`, `gh run view`) is fine if ever needed, but this loop
   shouldn't need GitHub API access at all — it's pure local git.
3. **Every feature must pass tests before commit.** For `linux/` changes:
   `QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m unittest discover -s tests -t . -v`
   must exit 0. For protocol changes: grep all three clients (android/,
   linux/, macos/) per AGENTS.md — if you can't safely update all three in
   one cycle, don't change the protocol; propose an additive/backward-compatible
   change instead or skip it.
4. **One feature per commit, Conventional Commits format** (`feat:`, `fix:`,
   etc.) per AGENTS.md. Small, reviewable, revertable commits — not one
   giant overnight mega-commit.
5. **If a feature can't be verified (no test coverage possible, e.g.
   Android/macOS changes with no local build environment), still write it,
   but mark it clearly in the commit body as "UNVERIFIED — needs manual
   testing" and log it in `.overnight/state.md`'s risk log. Prefer
   Linux-side features since that's the one platform fully buildable +
   testable in this sandbox.**
6. **Stop immediately if `.overnight/STOP` file exists** — check for it at
   the start of every cycle, before doing any work. The user can drop this
   file to abort the whole loop early.
7. **Never `rm -rf`, `git push --force`, `git reset --hard` past your own
   commits, or touch anything outside this clone's directory.**
8. **Time-box yourself.** If a single feature is taking more than ~20
   minutes of wall-clock effort with no passing tests in sight, abandon it,
   `git checkout -- .` / `git clean -fd` to discard the half-done work, log
   why in `state.md`, and move to the next backlog item instead of leaving
   the tree dirty or half-broken for the next cycle.

## Roles

- **BA/PM persona** (runs on its own schedule): reads `README.md`,
  `PLAN.md`, `website/docs/`, and `.overnight/BACKLOG.md`'s existing
  entries + `state.md`'s shipped-features log, so it doesn't propose
  duplicates. Adds 1-3 new concrete, scoped feature ideas to the **top**
  of the "Proposed" section in `BACKLOG.md` (highest priority first)
  each cycle. Ideas should be small enough to build+test in one engineer
  cycle (~15-30 min of focused work), specific (name the file(s) likely
  touched), and genuinely useful (grounded in what the app actually does
  — call handling, tray/menu UX, Bluetooth audio, connection reliability
  — not generic filler). Does NOT write code.
- **Engineer persona** (runs on its own schedule, offset from the PM):
  reads `.overnight/BACKLOG.md`, takes the single highest-priority
  "Proposed" item, implements it, runs the relevant test suite, and only
  if green: commits + pushes to `overnight/auto-research`, then moves the
  item from "Proposed" to "Shipped" in `BACKLOG.md` with the commit SHA.
  If tests fail after reasonable effort (see time-box above), moves the
  item to "Abandoned" with a one-line reason instead, discards the
  half-done work, and picks the next item. Only implements ONE item per
  cycle — small, verified increments beat a big unverified pile.

## Files

- `.overnight/BACKLOG.md` — the shared backlog (Proposed / Shipped / Abandoned).
- `.overnight/state.md` — running log: what shipped, what was abandoned and
  why, risk log (unverified items), append-only, newest at bottom.
- `.overnight/STOP` — if this file exists, every persona exits immediately
  without doing any work.

## Non-negotiable: this is NOT actually infinite

Despite the request for a no-stop overnight loop, there is a hard cutoff:
a one-shot cron job fires at 8:00 AM IST that drops `.overnight/STOP`,
waits for any in-flight cycle to notice it and exit cleanly, and then
posts one consolidated summary back to the user with the shipped-feature
list, commit log, and abandoned/risk items. The user is asleep and cannot
supervise this — bounding it in time and blast radius (a disposable
branch, no main/release/secrets access, test-gated commits) is what makes
"autonomous overnight" safe to actually run rather than just a request to
decline.
