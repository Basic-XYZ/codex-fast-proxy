# codex-fast-proxy update for Codex

Use these instructions when an engineer asks Codex to update Codex App Fast proxy.

## Normal path

Open the Control UI and let the user click `更新`:

```powershell
python -m codex_fast_proxy ui
```

Report the printed URL as plain text:

```text
请在外部浏览器中打开：http://127.0.0.1:<port>/
```

The UI action delegates to `python -m codex_fast_proxy update`; it owns git pull, editable reinstall,
skill link refresh, enabled-runtime refresh, and final status reporting. Do not reimplement those
steps in chat.

## Check only

If the user only asks whether an update is available, run this read-only command and stop:

```powershell
python -m codex_fast_proxy check-update
```

Report `relation`, `update_available`, `local_changes`, and `next_action`.

## CLI fallback

Use this only when the Control UI cannot be opened or the user explicitly asks Codex to perform the
update. It is also the bootstrap path for older installed versions that do not yet have the `update`
command.

If the Codex environment uses sandbox or approval controls, request approval/escalation because this
fetches from GitHub, reinstalls a Python package, writes under `~/.codex`, may refresh
`~/.codex/hooks.json`, and may create a skill link under `~/.agents`.

```powershell
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) {
    'python'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    'python3'
} else {
    throw 'Python 3 is required before updating codex-fast-proxy.'
}
$repoRoot = Join-Path (Join-Path $HOME '.codex') 'codex-fast-proxy'
if (-not (Test-Path $repoRoot)) {
    throw 'codex-fast-proxy is not installed. Follow INSTALL.md first.'
}
git -C $repoRoot pull --ff-only
& $pythonCmd -m pip install --user -e $repoRoot
& $pythonCmd -m codex_fast_proxy update --repo $repoRoot --skip-self-update
```

Use the returned JSON as the source of truth. Tell the user to restart Codex only when
`restart_required=true`, final `needs_restart=true`, or the result explicitly reports that Codex must
rescan skills.

Never print API key values, `auth.json` contents, ChatGPT tokens, cookies, request bodies, or prompts.
