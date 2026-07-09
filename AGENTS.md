# AGENTS.md

Guidance for coding agents (and humans) working in this repo. Read
`README.md` and `PLAN.md` first for what this project *is*; this file
is about how to build, test, and ship changes to it correctly.

## Repo layout

Three independent clients speak the exact same WebSocket JSON protocol
to one Android app (see `website/docs/protocol.mdx` for the wire format):

| Path | Platform | Language | Build |
|---|---|---|---|
| `android/` | Android app (the phone side) | Kotlin | Gradle |
| `linux/` | Ubuntu desktop client | Python (PySide6) | `./build-deb.sh` → `.deb` |
| `macos/` | macOS desktop client | Swift (SwiftUI) | `./build.sh` → `.app` |
| `website/` | Documentation site | TypeScript (Docusaurus) | `npm run build` |

Changing the protocol requires updating **all three** clients plus
`website/docs/protocol.mdx` — grep for the message type constant in
each of `android/`, `linux/src/dashphone/protocol.py`, and
`macos/DashPhone/Network/` before assuming a one-sided change is safe.

## Build & test commands

### Android
```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64   # see Pitfalls below
cd android
./gradlew assembleDebug
```
No unit test suite exists yet for the Android client — verify by
building and, if a device/emulator is available, installing
(`adb install -r app/build/outputs/apk/debug/app-debug.apk`).

### Ubuntu (linux/)
```bash
cd linux
sudo apt install python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtwidgets python3-websockets
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 -m unittest discover -s tests -t . -v
```
`QT_QPA_PLATFORM=offscreen` is required in headless/CI environments —
PySide6 otherwise tries to open a real display and hangs or errors.

### macOS (macos/)
```bash
cd macos
swift build            # or ./build.sh for a full .app bundle
swift test              # if/when a test target exists
```
Building requires Xcode Command Line Tools and only works on macOS.

### Docs site (website/)
```bash
cd website
npm install
npm run build            # must pass with zero broken links (onBrokenLinks: 'throw')
npm run serve             # smoke-test the production build locally
```

## Conventions

- **Commits**: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`,
  etc.) — the release pipeline (`.github/workflows/release.yml`) parses
  commit messages since the last tag to decide the next semver bump
  (`feat:` → minor, `fix:`/`chore:`/others → patch, `BREAKING CHANGE` /
  `!` → major). Non-conventional messages are treated as patch-level.
- **Version source of truth**: the root `VERSION` file. Never hand-edit
  version strings in `android/app/build.gradle`,
  `linux/packaging/control.in`, etc. — `.github/scripts/bump_versions.py`
  syncs `VERSION` into every platform's version fields as part of the
  release workflow.
- Keep documentation (`website/docs/`) in sync with behavior you change
  — especially `protocol.mdx` (wire format), `troubleshooting.mdx`, and
  the platform-specific install pages.

## Pitfalls discovered in this repo

- **Android/Gradle + JDK**: the system default `java` may resolve to a
  newer JDK (e.g. 25) that this repo's Gradle wrapper (8.4) cannot
  parse ("Unsupported class file major version"). Always
  `export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64` (or wherever
  JDK 17 lives) before running `./gradlew`. If a build was ever run
  under the wrong JDK first, the Kotlin incremental-compilation cache
  can get corrupted — run `./gradlew --stop && rm -rf app/build build .gradle`
  before retrying.
- **PySide6 in headless environments**: always set
  `QT_QPA_PLATFORM=offscreen` when running the Linux client's tests or
  importing its modules outside a real X11/Wayland session.
- **Docusaurus doc `id` frontmatter**: for docs nested in subfolders
  (e.g. `docs/ubuntu/install.mdx`), the frontmatter `id:` must be just
  the filename (`install`), not the folder-qualified path
  (`ubuntu/install`) — Docusaurus derives the folder prefix itself.
  Sidebar/link references still use the folder-qualified form
  (`ubuntu/install`) in `sidebars.ts` and cross-doc links.
- **Docusaurus sidebar categories with a `link`**: when a category has
  `link: {type: 'doc', id: 'x'}`, do not also list that same doc id as
  the first entry of `items` — it duplicates the page in prev/next
  pagination and in the flattened sidebar. `items` should only list the
  *other* docs in that category.
- **MDX heading anchors**: don't use explicit `{#custom-id}` anchor
  syntax in `.mdx` files — MDX's JS/JSX expression parser can choke on
  the braces. Docusaurus auto-slugs headings via github-slugger; link
  to the auto-generated slug instead (verify with a local build/serve
  before trusting a cross-page anchor link).
- **`python3-pyside6.*` is missing from Ubuntu 24.04 ("noble")'s apt
  archives entirely** (confirmed via Launchpad — the `pyside6` source
  package's earliest published series is 24.10 "oracular"). GitHub's
  `ubuntu-latest` runner is still 24.04, so CI installs PySide6 from
  PyPI (`pip install --break-system-packages PySide6`) instead of apt
  for the `build-linux`/`test-linux` jobs — this only affects the CI
  build/test environment, not the shipped `.deb`'s `Depends:`. Real
  Ubuntu 24.04 LTS end users installing the `.deb` may hit the same
  unsatisfiable-dependency problem; this is a known open issue, not
  yet resolved in the package's `Depends:` or the docs' "24.04+"
  support claim.
- **`bump_versions.py`'s "did the substitution actually match" check**
  must test pattern presence directly (e.g. `pattern.search(text)`),
  not compare before/after text equality — a version bump to the same
  value the file already has (e.g. this project's bootstrap release,
  where `VERSION` already contains the initial version) is a
  legitimate no-op substitution and must not be mistaken for "pattern
  not found".
- **Bash `read var1 var2 < <(cmd | tr '\n' ' ')` in a `set -e` script**:
  stripping the trailing newline means `read` hits EOF without a final
  delimiter and returns exit 1 even after successfully populating both
  variables, killing the step. Use `mapfile -t arr < <(cmd)` instead.
