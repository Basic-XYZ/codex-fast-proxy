# 面向 Codex 的 codex-fast-proxy 卸载说明

当工程师要求 Codex 卸载 Codex App Fast proxy 时，使用本文说明。

## 给工程师的一句话 prompt

```text
获取并遵循 https://raw.githubusercontent.com/Basic-XYZ/codex-fast-proxy/main/.codex/UNINSTALL.md 里的说明
```

## 卸载步骤

运行中的 Codex process 不会热切换 provider config。如果当前 process 正在使用 proxy，停止 proxy 可能中断对话。下面的命令块会先恢复 config，并在需要时延迟停止；用户重启 Codex App 并回到同一对话，或打开新 CLI 进程后，再运行同一说明完成清理。

如果用户在启用 proxy 后修改过 `~/.codex/config.toml`，manager 会尽量保留这些更改：当 recorded provider 仍指向本地 proxy 时，它只把该 provider 的 `base_url` 恢复为保存的 upstream。

卸载只移除 `~/.codex/hooks.json` 中的 `codex-fast-proxy` 条目；必须保留无关用户 hooks。

如果 Codex 环境有 sandbox 或 approval 控制，请为卸载请求审批/提权，因为它可能恢复 `~/.codex/config.toml`、编辑 `~/.codex/hooks.json`、停止后台 proxy、卸载 Python package、移除 `~/.agents` 下的 skill link，并删除 `~/.codex/codex-fast-proxy`。

如果任何命令因为权限、sandbox 写入限制、process lock 或 skill link 移除失败而失败，不要尝试无关 workaround。请求审批后重新运行同一个预期卸载步骤。

精确运行这个 PowerShell 命令块：

```powershell
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) {
    'python'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    'python3'
} else {
    throw '卸载 codex-fast-proxy 前需要 Python 3。'
}
$repoRoot = Join-Path (Join-Path $HOME '.codex') 'codex-fast-proxy'
$uninstallJson = $null
$uninstallResult = $null
$status = $null
$deferred = $false
$confirmationRequired = $false

if (Test-Path $repoRoot) {
    $env:PYTHONPATH = Join-Path $repoRoot 'src'
    $statusJson = & $pythonCmd -m codex_fast_proxy status
    $status = $statusJson | ConvertFrom-Json
    if ($status.config_matches -eq $true) {
        $uninstallJson = & $pythonCmd -m codex_fast_proxy uninstall --defer-stop
        $uninstallResult = $uninstallJson | ConvertFrom-Json
        $uninstallJson
        if ($uninstallResult.status -eq 'confirmation_required') {
            Write-Host 'uninstall_confirmation_required=true'
            $confirmationRequired = $true
        } else {
            Write-Host 'restart_required_before_cleanup=true'
            $deferred = $true
        }
    } else {
        $uninstallJson = & $pythonCmd -m codex_fast_proxy uninstall
        $uninstallResult = $uninstallJson | ConvertFrom-Json
        $uninstallJson
        if ($uninstallResult.status -eq 'confirmation_required') {
            Write-Host 'uninstall_confirmation_required=true'
            $confirmationRequired = $true
        } elseif ($uninstallResult.config_restore -eq 'skipped_config_changed') {
            throw 'proxy install 之后 Codex config 已变化，且 selected provider 不再指向 recorded proxy。proxy 未停止，文件未移除。请检查 ~/.codex/config.toml；如果想恢复 recorded backup，可用 --force 重新运行 uninstall。'
        }
    }
}

if ((-not $deferred) -and (-not $confirmationRequired)) {
    if (Test-Path $repoRoot) {
        $env:PYTHONPATH = Join-Path $repoRoot 'src'
        & $pythonCmd -m codex_fast_proxy unlink-skill --repo-root $repoRoot
    }

    & $pythonCmd -m pip uninstall -y codex-fast-proxy

    if (Test-Path $repoRoot) {
        Remove-Item -LiteralPath $repoRoot -Recurse -Force
    }
}
```

如果有 uninstall JSON 结果，报告它。

如果命令块打印 `uninstall_confirmation_required=true`，说明没有应用任何卸载变更。先报告 `direct_upstream_auth_warning`，再询问用户是要保持 proxy 启用，还是明确继续卸载。只有在用户清楚接受 ChatGPT-login direct-upstream 401 风险后，才用 `--confirm-chatgpt-direct-uninstall` 重新运行 manager。

如果 uninstall JSON 有 `status="uninstalled"` 且包含 `direct_upstream_auth_warning`，先报告这个 warning，再告诉用户重启 Codex。这表示 Codex config 已恢复为 direct third-party upstream，但当前 Codex auth 状态仍像 ChatGPT 账户登录。Direct upstream 模式不再有 proxy auth override，所以模型请求可能把 ChatGPT auth 发给第三方 provider 并 401。告诉用户重启前先把 Codex App 切回 API-key/第三方 provider 鉴权，或者如果想使用 ChatGPT-login UI 与第三方 provider，就保持 proxy 启用。

当清理完成且没有 `restart_required_before_cleanup=true` 时，明确告诉用户：

```text
请重启 Codex App，或打开新的 CLI 进程，让 Codex 从 skill 列表中移除 codex-fast-proxy。
```

如果命令块打印 `restart_required_before_cleanup=true`，明确告诉用户：

```text
Codex config 已恢复为 direct upstream，proxy 被临时保留运行以避免中断当前 process。请重启 Codex App 并回到这个对话，或打开新的 CLI 进程，然后再次运行 uninstall 完成清理。
```

如果命令块打印 `uninstall_confirmation_required=true`，明确告诉用户：

```text
未应用任何卸载变更，因为 ChatGPT login 看起来处于活跃状态，direct upstream 模式可能返回 401。你可以保留 proxy 以便通过 ChatGPT-login UI 使用第三方 provider，先把 Codex App 切回 API-key/第三方 provider 鉴权再卸载，或明确确认仍要继续卸载。
```

如果 `status="uninstalled"` 且存在 `direct_upstream_auth_warning`，在重启说明前追加：

```text
警告：ChatGPT login 看起来处于活跃状态。卸载恢复 direct upstream 后，请求不再经过 proxy upstream auth override。如果 Codex 继续使用 ChatGPT auth，第三方 provider 可能收到 ChatGPT token 并返回 401。请在重启前切回 API-key/第三方 provider 鉴权，或保留 proxy 以便通过 ChatGPT-login UI 使用第三方 provider。
```
