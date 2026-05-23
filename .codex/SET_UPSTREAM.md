# 面向 Codex 的 codex-fast-proxy 上游 URL 修改说明

当工程师要求 Codex 修改已启用 Codex Fast proxy 使用的 provider URL 时，使用本文说明。

proxy 启用时，不要直接编辑 `~/.codex/config.toml` 中 active provider 的 `base_url`。该字段应继续指向本地 proxy。API key、model、reasoning 和其他 Codex settings 仍可照常在 `config.toml` 中编辑。

如果用户只想修改 Fast policy 或 ChatGPT-login upstream auth，不需要新的 upstream URL。如果用户想修改 provider URL 但没有提供新的 upstream URL，先询问。不要猜 provider URL。

如果 Codex 环境有 sandbox 或 approval 控制，请请求审批/提权，因为此流程可能写入 `~/.codex`、编辑 `~/.codex/hooks.json`、重启后台 proxy，并更新 uninstall recovery baseline。

下面每个 PowerShell 命令块都假设同一 shell 中已先运行这个 resolver：

```powershell
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) {
    'python'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    'python3'
} else {
    throw '修改 codex-fast-proxy 设置前需要 Python 3。'
}
```

把 `<UPSTREAM_BASE_URL>` 替换成用户提供的 URL 后，运行这个命令块：

```powershell
$statusJson = & $pythonCmd -m codex_fast_proxy status
$status = $statusJson | ConvertFrom-Json
if ($status.config_matches -ne $true) {
    $statusJson
    throw 'Codex config 不再指向 recorded local proxy。修改 upstream 前请检查 ~/.codex/config.toml。'
}

$resultJson = & $pythonCmd -m codex_fast_proxy set-upstream --upstream-base '<UPSTREAM_BASE_URL>'
$resultJson
& $pythonCmd -m codex_fast_proxy status
```

`set-upstream` 会在写 settings 前验证候选 route：它会用候选 upstream 和 auth source 发送一个 side-path Codex-style `POST /v1/responses` 请求，并带 `stream=true`。这是真实 provider 流量，可能消耗少量 quota。如果验证失败，不要用 `--no-verify` 重试，除非用户明确接受下一个 Codex session 可能无法访问模型。

如果用户要求先验证且不修改本地状态，运行：

```powershell
& $pythonCmd -m codex_fast_proxy verify-upstream --upstream-base '<UPSTREAM_BASE_URL>'
```

报告 JSON 结果后停止。`verify-upstream` 不能写 settings、编辑 Codex config、安装 hook 或重启 proxy。

如果不修改 upstream URL，只做 ChatGPT login 兼容性，请准备 proxy provider auth file。不要要求用户把 key 值粘贴到聊天中。它只影响已经经过本地 proxy 的 provider API 请求；不能拦截 ChatGPT plugin/GitHub/App connector 流量。在 override 模式下，proxy 会替换 provider `Authorization`，并在转发上游前丢弃意外的 `Cookie` header。

先 dry run：

```powershell
& $pythonCmd -m codex_fast_proxy prepare-chatgpt-login
```

只报告非 secret JSON 字段。如果 dry run 在 `auth.json` 或环境变量中找到了当前可用 provider key，应用前先询问：

```powershell
& $pythonCmd -m codex_fast_proxy prepare-chatgpt-login --apply
```

apply 步骤会把当前可用 provider key 复制到 `~/.codex/codex-fast-proxy-state/provider-auth.json`，不会打印 key，也不会修改 proxy settings。成功后继续执行 `set-upstream`，让 manager 在保存 auth override 前验证一次 streaming `/v1/responses` 请求。

```powershell
$statusJson = & $pythonCmd -m codex_fast_proxy status
$status = $statusJson | ConvertFrom-Json
if ($status.config_matches -ne $true) {
    $statusJson
    throw 'Codex config 不再指向 recorded local proxy。修改 upstream auth 前请检查 ~/.codex/config.toml。'
}

$resultJson = & $pythonCmd -m codex_fast_proxy set-upstream --use-provider-auth-file
$resultJson
& $pythonCmd -m codex_fast_proxy status
```

清除之前配置过的 upstream auth override，恢复保留 Codex 原始 provider `Authorization` header：

```powershell
& $pythonCmd -m codex_fast_proxy set-upstream --clear-upstream-auth
& $pythonCmd -m codex_fast_proxy status
```

如果要显式启用全局 Fast 注入，先确认用户接受：当请求缺少 `service_tier` 时，Codex App 的 Fast UI toggle 将不再控制这些请求。然后运行：

```powershell
& $pythonCmd -m codex_fast_proxy set-upstream --service-tier-policy inject_missing
& $pythonCmd -m codex_fast_proxy status
```

恢复 UI-controlled Fast 行为：

```powershell
& $pythonCmd -m codex_fast_proxy set-upstream --service-tier-policy preserve
& $pythonCmd -m codex_fast_proxy status
```

恢复默认自动行为：API-key 模式可使用全局 priority，ChatGPT-login 或状态不明确时保留 App/CLI 选择：

```powershell
& $pythonCmd -m codex_fast_proxy set-upstream --service-tier-policy auto
& $pythonCmd -m codex_fast_proxy status
```

报告 set-upstream JSON 和最终 status JSON。关键字段是 `provider`、`base_url`、`previous_upstream_base`、`upstream_base`、`service_tier_policy`、`upstream_auth`、`config_matches`、`verification`、`restart_required`、`start_result` 和 `next_user_action`。

不要使用 `--restart`，除非用户明确接受重启 proxy 可能中断当前 proxy-backed Codex session。如果 `restart_required=true`，告诉用户稍后重启 Codex App、打开新 CLI 进程，或运行 `python -m codex_fast_proxy start` 来应用新 upstream。

对 ChatGPT-login 准备流程来说，`restart_required=true` 或最终 `status.needs_restart=true` 是登录前的 hard stop。provider auth split 已验证并保存，但运行中的 proxy 尚未加载新的 auth override。告诉用户重启 Codex App，或明确允许运行 `python -m codex_fast_proxy start`，然后再登录 ChatGPT。不要在 `needs_restart=true` 时告诉用户可以切到 ChatGPT login；模型请求仍可能 401。

当 provider auth split 已激活，且最终 `status.needs_restart=false` 后，用户可以按需登录 ChatGPT 以使用完整 Codex App UI。同时提到这个 Windows 登录排障路径：如果 ChatGPT login 失败并出现 `OSError: [WinError 10013] ... socket ...`，让用户在管理员 PowerShell 中运行以下命令后重试：

```powershell
net stop winnat
netsh interface ipv4 show excludedportrange protocol=tcp
net start winnat
netsh interface ipv4 show excludedportrange protocol=tcp
```

如果用户修改了 provider auth、model、reasoning 或其他 Codex config，告诉他们重启 Codex App 或打开新 CLI 进程，让 Codex 重新加载这些设置。已运行的 Codex process 仍可能需要重启才能重新加载自己的 config 和 environment。
