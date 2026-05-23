# 面向 Codex 的 codex-fast-proxy 更新说明

当工程师要求 Codex 更新 Codex App Fast proxy 时，使用本文说明。

## 给工程师的一句话 prompt

```text
获取并遵循 https://raw.githubusercontent.com/Basic-XYZ/codex-fast-proxy/main/.codex/UPDATE.md 里的说明
```

## 更新步骤

如果用户只要求检查是否有更新，运行这个只读命令后停止：

```powershell
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) {
    'python'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    'python3'
} else {
    throw '检查 codex-fast-proxy 更新前需要 Python 3。'
}
& $pythonCmd -m codex_fast_proxy check-update
```

报告 JSON，包括 `relation`、`update_available`、`local_changes` 和 `next_action`。如果 `relation=local_ahead`，不要把它报告成可用更新。除非用户随后明确要求更新，否则不要 pull、install、重启 proxy、编辑 Codex config 或写入 proxy state。

如果 Codex 环境有 sandbox 或 approval 控制，请为更新命令块请求审批/提权，因为它会从 GitHub fetch、安装 Python package，可能写入 `~/.codex`、`~/.codex/hooks.json`，并可能在 `~/.agents` 下创建 skill link。

如果任何命令因为网络、权限、sandbox 写入限制或 skill link 创建失败而失败，不要尝试无关 workaround。请求审批后重新运行同一个预期更新步骤。

精确运行这个 PowerShell 命令块：

```powershell
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) {
    'python'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    'python3'
} else {
    throw '更新 codex-fast-proxy 前需要 Python 3。'
}
$repoRoot = Join-Path (Join-Path $HOME '.codex') 'codex-fast-proxy'
$status = $null

if (-not (Test-Path $repoRoot)) {
    throw 'codex-fast-proxy 尚未安装。请先遵循 INSTALL.md。'
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

当 proxy 已启用时，报告 install JSON 和最终 status JSON；以最终 status JSON 作为当前状态。如果 skill 是新链接或发生变化，明确告诉用户：

```text
请重启 Codex App 并回到这个对话，或打开新的 CLI 进程，让 Codex 重新扫描 ~/.agents/skills。然后让 Codex 启用 Codex Fast proxy。
```

如果更新期间运行了 `install --start`，它会刷新 `~/.codex/hooks.json`，并为未来 App/CLI 启动启用 Codex `SessionStart` autostart。它也会比较运行中 proxy runtime 和已安装代码；如果 proxy 健康但 runtime stale，显式 `install --start`/`start` 可能会在返回前重启 proxy。用最终 `status` 输出报告 `runtime_matches` 和 `needs_restart`。如果 `status.needs_restart` 仍为 `true`，告诉用户重启 Codex App、在旧 proxy 退出后打开新 CLI 进程，或在安全时运行 `python -m codex_fast_proxy start` 来刷新 runtime code。Codex 可能为每个新 session 或 resumed session 触发 `SessionStart`；`autostart --quiet` 不会仅因 runtime code stale 而重启健康 proxy，也不会记录正常 no-op 检查。

当前 Codex build 可能需要 trusted user hooks。更新后，`startup_hook: true` 表示 hook 存在、已启用且当前 command hash 已被信任。如果 `startup_hook_trust` 报告 `modified` 或 `untrusted`，在让用户依赖 autostart 前重新运行 `python -m codex_fast_proxy install --start`。

更新后的当前行为：

- 新安装默认使用 `auto`：ChatGPT-login 或状态不明确时保留 Codex App/CLI Fast UI 选择；API-key 模式下，当 Codex 省略 `service_tier` 时可以使用全局 priority。
- 现有 `service_tier_policy`、provider auth file 和 `upstream_api_key_env` settings 会在 `install --start` 期间保留。
- 旧安装如果从未记录 `service_tier_policy`，且没有 split upstream auth，会被视为 `inject_missing`，以保持之前的全局 Fast 行为。缺失 policy 但带 split upstream auth 的形态属于 ChatGPT-login auth split 路径，应视为 App-controlled `preserve`。如果用户明确想要 auto 行为，运行：

```powershell
& $pythonCmd -m codex_fast_proxy set-upstream --service-tier-policy auto
```

不要传 `--restart`，除非用户接受中断当前 proxy-backed Codex session。

- 更新后如果要兼容 ChatGPT login，先准备 provider auth file，不打印 key，然后配置 proxy 使用该文件：

```powershell
& $pythonCmd -m codex_fast_proxy prepare-chatgpt-login
& $pythonCmd -m codex_fast_proxy prepare-chatgpt-login --apply
& $pythonCmd -m codex_fast_proxy set-upstream --use-provider-auth-file
```

第一条命令是 dry run。只有在用户同意把当前可用 provider key 复制到 proxy provider auth file 后，才运行 `--apply`。不要传 `--restart`，除非用户接受中断当前 proxy-backed Codex session。

永远不要打印 API key 值、`auth.json` 内容、ChatGPT token、Cookie、请求体或 prompt。
