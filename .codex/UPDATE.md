# codex-fast-proxy update for Codex

Use these instructions when an engineer asks Codex to update Codex App Fast proxy.

## One-paste prompt for engineers

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-fast-proxy/main/.codex/UPDATE.md
```

## Update steps

If the user only asks to check whether an update is available, run this read-only command and stop:

```powershell
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) {
    'python'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    'python3'
} else {
    throw 'Python 3 is required before checking codex-fast-proxy updates.'
}
& $pythonCmd -m codex_fast_proxy check-update
```

Report the JSON, including `relation`, `update_available`, `local_changes`, and `next_action`. If
`relation=local_ahead`, do not report it as an available update. Do not pull, install, restart the
proxy, edit Codex config, or write proxy state unless the user then explicitly asks to update.

If the Codex environment uses sandbox or approval controls, request approval/escalation for the update block because it fetches from GitHub, installs a Python package, may write under `~/.codex`, may write `~/.codex/hooks.json`, and may create a skill link under `~/.agents`.

If any command fails because of network, permissions, sandbox write limits, or skill link creation, do not try unrelated workarounds. Ask for approval and rerun the same intended update step.

Run this PowerShell block exactly:

```powershell
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) {
    'python'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    'python3'
} else {
    throw 'Python 3 is required before updating codex-fast-proxy.'
}
$repoRoot = Join-Path (Join-Path $HOME '.codex') 'codex-fast-proxy'
$status = $null

if (-not (Test-Path $repoRoot)) {
    throw 'codex-fast-proxy is not installed. Follow INSTALL.md first.'
}

git -C $repoRoot pull --ff-only
& $pythonCmd -m pip install --user -e $repoRoot
& $pythonCmd -m codex_fast_proxy link-skill --repo-root $repoRoot

$statusJson = & $pythonCmd -m codex_fast_proxy status
$status = $statusJson | ConvertFrom-Json
if ($status.config_matches -eq $true) {
    & $pythonCmd -m codex_fast_proxy install --start
    & $pythonCmd -m codex_fast_proxy status
} else {
    & $pythonCmd -m codex_fast_proxy doctor
}
```

Report the install JSON and the final status JSON when the proxy was already enabled; use the final
status JSON as the current state. If the skill was newly linked or changed, explicitly tell the user:

```text
Restart Codex App and return to this conversation, or open a new CLI process, so Codex can rescan ~/.agents/skills. Then ask Codex to enable Codex Fast proxy.
```

If `install --start` ran during update, it refreshes `~/.codex/hooks.json` and enables Codex `SessionStart` autostart for future App/CLI starts. It also compares the running proxy runtime with the installed code; if the proxy is healthy but stale, explicit `install --start`/`start` may restart the proxy before returning. Use the final `status` output to report `runtime_matches` and `needs_restart`. If `status.needs_restart` is still `true`, tell the user to restart Codex App, open a new CLI process after the old proxy is gone, or run `python -m codex_fast_proxy start` when it is safe to refresh runtime code. Codex may fire `SessionStart` for each new or resumed session; `autostart --quiet` does not restart an already healthy proxy just because runtime code is stale, and it does not log normal no-op checks.

Current Codex builds may require trusted user hooks. After update, `startup_hook: true` means the
hook exists, is enabled, and its current command hash is trusted. If `startup_hook_trust` reports
`modified` or `untrusted`, rerun `python -m codex_fast_proxy install --start` before asking the user
to rely on autostart.

Current behavior after update:

- New installs default to `auto`: ChatGPT-login or unclear states preserve Codex App/CLI Fast UI
  choices, while API-key mode can use global priority when Codex omits `service_tier`.
- Existing `service_tier_policy`, provider auth file, and `upstream_api_key_env` settings are preserved during
  `install --start`.
- Older installs that never recorded `service_tier_policy` and do not have split upstream auth
  are treated as `inject_missing` to keep their previous global Fast behavior. Missing policy plus
  split upstream auth is treated as App-controlled `preserve`, because that shape belongs to the
  ChatGPT-login auth split path. If the user explicitly wants auto behavior, run:

```powershell
& $pythonCmd -m codex_fast_proxy set-upstream --service-tier-policy auto
```

  Do not pass `--restart` unless the user accepts interrupting current proxy-backed Codex sessions.

- For ChatGPT login compatibility after update, first prepare the provider auth file without
  printing the key, then configure the proxy to use that file:

```powershell
& $pythonCmd -m codex_fast_proxy prepare-chatgpt-login
& $pythonCmd -m codex_fast_proxy prepare-chatgpt-login --apply
& $pythonCmd -m codex_fast_proxy set-upstream --use-provider-auth-file
```

  The first command is a dry run. Run the `--apply` command only after the user approves copying the
  currently working provider key into the proxy provider auth file. Do not pass `--restart` unless
  the user accepts interrupting current proxy-backed Codex sessions.

Never print API key values, `auth.json` contents, ChatGPT tokens, cookies, request bodies, or prompts.
