# Pre-Release Checklist

Work through this list **every time** before publishing a new release.
Nothing here is optional. Strangers will install this on machines you
can't access, so a small mistake here can cost you a refund or worse.

---

## 1. Source hygiene

- [ ] `git status` is clean except for intentional release changes
- [ ] No `.env` tracked (`git ls-files | grep -E '^\.env$'` returns nothing)
- [ ] No `user_secrets.json` tracked
- [ ] No `.claude/settings.local.json` tracked (contains session tokens + wallet fingerprints)
- [ ] No `bot.db`, `bot.db-shm`, `bot.db-wal`, `bot_backup_*.db` tracked
- [ ] No `*.log` files tracked (`crash.log`, `bot_superlog_*.log`, `coin_prep_output.log`)
- [ ] No `*.key`, `*.pem`, `*.crt` (wallet mTLS certs) tracked
- [ ] No `splash.exe` tracked — it's downloaded separately
- [ ] Absolute dev paths stripped from tracked docs — run:
      `git ls-files | xargs grep -l "t_you\|Users\\\\" 2>/dev/null`
      (should return nothing)
- [ ] No real wallet addresses hardcoded in source — run:
      `git ls-files | xargs grep -oE "xch1[a-z0-9]{50,}" 2>/dev/null`
      (anything that's not a null address or documented test placeholder needs to go)
- [ ] No real wallet fingerprints hardcoded in source — run:
      `git ls-files | xargs grep -E "fingerprint.*[0-9]{10}" 2>/dev/null`
- [ ] No API keys, tokens, or session secrets in source

## 2. Version + changelog

- [ ] `APP_VERSION` bumped in `desktop_app.py`
- [ ] Same version set in `installer.iss` (`MyAppVersion`)
- [ ] `CHANGELOG.md` updated with the new version and a human-readable summary
- [ ] About modal (`bot_gui.html` → `aboutAppVersion`) reflects via the API
- [ ] `RELEASES_API_URL` is set in the documented `.env.example` (leave blank by default)

## 3. Code quality

- [ ] All Python files parse: `python -c "import ast; [ast.parse(open(f,encoding='utf-8').read()) for f in __import__('glob').glob('*.py')]"`
- [ ] HTML sanity: script/style tags balanced, no unclosed `<div>`
- [ ] Every test passes: `pytest` (or the project's preferred runner)
- [ ] No `TODO` / `FIXME` / `XXX` introduced in the release diff that should have been resolved
- [ ] No `print()` debug spam in hot paths

## 4. Build

- [ ] Clean build: `python build.py` (or whatever `build.py` calls)
- [ ] `dist\ChiaMarketMaker\ChiaMarketMaker.exe` exists and is the expected size (~30–80 MB)
- [ ] `dist\ChiaMarketMaker\_internal\` present and complete
- [ ] `dist\ChiaMarketMaker\bot_gui.html` matches the source
- [ ] `dist\ChiaMarketMaker\.env.example` present
- [ ] `dist\ChiaMarketMaker\splash.exe` present if SPLASH_ENABLED is a supported feature

## 5. Code signing (Windows)

- [ ] EV (or OV if you must) cert plugged in
- [ ] Sign child binaries **first**:
      ```
      signtool sign /fd sha256 /td sha256 /tr http://timestamp.sectigo.com /a "dist\ChiaMarketMaker\splash.exe"
      ```
- [ ] Then sign the main exe:
      ```
      signtool sign /fd sha256 /td sha256 /tr http://timestamp.sectigo.com /a "dist\ChiaMarketMaker\ChiaMarketMaker.exe"
      ```
- [ ] Verify signatures:
      ```
      signtool verify /pa /v "dist\ChiaMarketMaker\splash.exe"
      signtool verify /pa /v "dist\ChiaMarketMaker\ChiaMarketMaker.exe"
      ```
      Both must print `Successfully verified`.
- [ ] Build the Inno Setup installer (open `installer.iss` in ISCC, Compile)
- [ ] Sign the installer itself:
      ```
      signtool sign /fd sha256 /td sha256 /tr http://timestamp.sectigo.com /a "Output\ChiaMarketMaker-Setup-X.Y.Z.exe"
      ```
- [ ] Verify the installer signature

## 6. Fresh-install test (on a clean Windows VM)

- [ ] Transfer ONLY the signed installer to the clean VM (not the whole repo)
- [ ] Double-click the installer
- [ ] **No SmartScreen red warning** — if you see "Windows protected your PC",
      your cert reputation isn't built yet (OV cert) or the signature is broken
- [ ] Installer completes with no errors
- [ ] Start Menu shortcut appears
- [ ] Launch from Start Menu
- [ ] App opens to its first-run state (no CAT selected, wallet picker visible)
- [ ] Check `%APPDATA%\ChiaMarketMaker\` exists and contains `.env`, `bot.db`
- [ ] `.env` was seeded from `.env.example` (has commented examples, no real values)
- [ ] Forcing a crash (e.g. modify config to bad value) writes a readable `crash.log` to `%APPDATA%\ChiaMarketMaker\`
- [ ] "View last crash report" in Help → Troubleshooting shows the crash
- [ ] "Open data folder" reveals `%APPDATA%\ChiaMarketMaker\` in Explorer
- [ ] Uninstaller in Add/Remove Programs works cleanly
- [ ] **After uninstall, verify `%APPDATA%\ChiaMarketMaker\` is still there** (intentional — user data is preserved)

## 7. Stranger-usability sanity check

Pretend you just downloaded this yourself and know nothing:

- [ ] Can you find the wallet setup without reading docs?
- [ ] The first-run setup checklist is visible and explains each step
- [ ] "Prepare Coins" button is discoverable before starting the bot
- [ ] "Smart Settings" is discoverable and does something sensible on click
- [ ] The Help modal's "Getting Started" tab reads well end-to-end
- [ ] The disclaimer in About modal is clear: users can lose money
- [ ] Wallet connection errors give actionable next steps, not raw stack traces

## 8. Publish

- [ ] Tag the release: `git tag vX.Y.Z && git push --tags`
- [ ] Create GitHub release with:
  - [ ] `ChiaMarketMaker-Setup-X.Y.Z.exe` (signed installer)
  - [ ] SHA-256 checksums file: `sha256sum ChiaMarketMaker-Setup-X.Y.Z.exe > CHECKSUMS.txt`
  - [ ] Release notes copied from `CHANGELOG.md`
- [ ] Update `RELEASES_API_URL` in your own dev `.env` to point at the new repo
      (so the in-app update check starts working for you)
- [ ] Announce publicly

## 9. Rollback plan

If something breaks after release:

- [ ] Mark the release as pre-release on GitHub so new users don't pick it up
- [ ] Post a pinned announcement explaining the issue
- [ ] Fix, bump patch version, and re-run this whole checklist from §2
- [ ] Do NOT silently overwrite the existing release artifacts — publish a new version
