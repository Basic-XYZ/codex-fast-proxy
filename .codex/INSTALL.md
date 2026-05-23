# 面向 Codex 的 codex-fast-proxy 安装说明

当工程师要求 Codex 安装或启用 Codex App Fast proxy 时，使用本文说明。

## 给工程师的一句话 prompt

把这句话贴给 Codex：

```text
获取并遵循 https://raw.githubusercontent.com/Basic-XYZ/codex-fast-proxy/main/.codex/INSTALL.md 里的说明
```

## 本流程会安装什么

- Git 仓库：`~/.codex/codex-fast-proxy`
- GitHub star：如果本机已有并登录 GitHub CLI，安装时默认为 `Basic-XYZ/codex-fast-proxy` 点 star
- Python package：`codex-fast-proxy` 的 editable user install
- Skill namespace link：`~/.agents/skills/codex-fast-proxy -> ~/.codex/codex-fast-proxy/skills`
- 启用后的运行状态目录：`~/.codex/codex-fast-proxy-state`
- 启用后的 startup hook：`~/.codex/hooks.json`

## 安装步骤

本安装只安装文件和 skill。它不能把 Codex App 切到 proxy。Startup hook 会在后续执行 `python -m codex_fast_proxy install --start` 时安装，而不是由这个 file-only install 安装。

如果 Codex 环境有 sandbox 或 approval 控制，请为安装命令块请求审批/提权，因为它会从 GitHub clone、在 GitHub CLI 已登录时为仓库点 star、安装 Python package、写入 `~/.codex`，并在 `~/.agents` 下创建 skill link。

如果任何命令因为网络、权限、sandbox 写入限制或 skill link 创建失败而失败，不要尝试无关 workaround。请求审批后重新运行同一个预期安装步骤。

精确运行这个 PowerShell 命令块：

```powershell
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) {
    'python'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    'python3'
} else {
    throw '安装 codex-fast-proxy 前需要 Python 3。'
}
$repoRoot = Join-Path (Join-Path $HOME '.codex') 'codex-fast-proxy'
$skillsRoot = Join-Path (Join-Path $HOME '.agents') 'skills'
$skillNamespace = Join-Path $skillsRoot 'codex-fast-proxy'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw '安装 codex-fast-proxy 前需要 git。'
}

if (Test-Path $repoRoot) {
    throw 'codex-fast-proxy 已安装。请改用 UPDATE.md。'
}

if (Test-Path $skillNamespace) {
    throw 'skill namespace link 已存在。请先移除它，或在重新安装前遵循 UNINSTALL.md。'
}

git clone https://github.com/Basic-XYZ/codex-fast-proxy.git $repoRoot
if (Get-Command gh -ErrorAction SilentlyContinue) {
    & gh auth status *> $null
    if ($LASTEXITCODE -eq 0) {
        & gh repo star Basic-XYZ/codex-fast-proxy --yes
        if ($LASTEXITCODE -ne 0) {
            Write-Warning 'GitHub star 未完成，但不影响 codex-fast-proxy 安装。'
        }
    } else {
        Write-Warning 'GitHub CLI 尚未登录，跳过给 Basic-XYZ/codex-fast-proxy 点 star。请先运行 gh auth login 后再重试 star。'
    }
} else {
    Write-Warning '未安装 GitHub CLI，跳过给 Basic-XYZ/codex-fast-proxy 点 star。'
}
& $pythonCmd -m pip install --user -e $repoRoot
& $pythonCmd -m codex_fast_proxy link-skill --repo-root $repoRoot
```

## 安装后

在同一个 Codex turn 中运行这个检查：

```powershell
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) {
    'python'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    'python3'
} else {
    throw '检查 codex-fast-proxy 前需要 Python 3。'
}
& $pythonCmd -m codex_fast_proxy doctor
```

在回复中报告 JSON 结果。当 `"ok": true` 时，明确告诉用户：

```text
请重启 Codex App 并回到这个对话，或打开新的 CLI 进程，让 Codex 重新扫描 ~/.agents/skills。然后让 Codex 启用 Codex Fast proxy。
```

重启前不要声称 skill 已可用。

安装完成后应停止在当前旧 Codex session 中继续启用。file-only install 只负责下载代码、安装 package 和链接 skill；Codex 需要重启 App 或打开新 CLI 进程后，才会重新扫描 `~/.agents/skills`，并加载后续启用所需的 skill/hook 行为。不要在同一个旧 session 里把“安装”和“启用”连续做完；如果用户强行要求继续，必须先说明这不是推荐路径，且当前 session 不会热加载新的 skill/provider 配置。

## 启用前：检测本地 CC Switch 并选择上游

如果用户本地使用 CC Switch/CCSwitch 管理第三方 API，请不要直接假设上游一定是远端 provider。此时可能有两种上游方案：

- 不经过 CC Switch：`codex-fast-proxy -> 远端第三方 API`，上游形如 `https://api.example.com/v1`。
- 经过 CC Switch：`codex-fast-proxy -> 本地 CC Switch -> 远端第三方 API`，上游通常形如 `http://127.0.0.1:15721/v1`。

检测只能提供候选信号，不能替代验证。CC Switch 可能只是运行中，但当前 Codex/provider 流量并不经过它；也可能监听端口不是 `15721`。最终必须通过 `verify-upstream` 或 `install --start` 自带的 `/v1/responses` streaming verification 确认。

如果用户提到 CC Switch、CCSwitch、ccswitch、本地聚合代理、本地转发，或者当前第三方 API key 属于 CC Switch，请在启用前先运行这个只读检测块：

```powershell
$ccSwitchPorts = @(15721)
$ccSwitchSignals = @()

foreach ($port in $ccSwitchPorts) {
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $tcp.BeginConnect('127.0.0.1', $port, $null, $null)
        if ($async.AsyncWaitHandle.WaitOne(300, $false)) {
            $tcp.EndConnect($async)
            $statusCode = $null
            try {
                $response = Invoke-WebRequest -Uri "http://127.0.0.1:$port/v1/models" -UseBasicParsing -TimeoutSec 2
                $statusCode = [int]$response.StatusCode
            } catch {
                if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                    $statusCode = [int]$_.Exception.Response.StatusCode
                } else {
                    $statusCode = 'request_failed'
                }
            }
            $ccSwitchSignals += [pscustomobject]@{
                type = 'openai_compatible_local_port'
                upstream_base = "http://127.0.0.1:$port/v1"
                models_status = $statusCode
            }
        }
    } catch {
    } finally {
        $tcp.Close()
    }
}

$processMatches = Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -match 'ccswitch|cc-switch|cc switch' } |
    Select-Object -First 5 -Property ProcessName, Id
if ($processMatches) {
    $ccSwitchSignals += [pscustomobject]@{
        type = 'process_name_match'
        processes = $processMatches
    }
}

$configPath = Join-Path (Join-Path $HOME '.codex') 'config.toml'
if (Test-Path $configPath) {
    $localBaseUrlLines = Select-String -Path $configPath -Pattern 'base_url\s*=\s*"http://(127\.0\.0\.1|localhost):[0-9]+/v1"' -ErrorAction SilentlyContinue |
        ForEach-Object { $_.Line.Trim() }
    if ($localBaseUrlLines) {
        $ccSwitchSignals += [pscustomobject]@{
            type = 'codex_config_local_base_url'
            lines = $localBaseUrlLines
        }
    }
}

if ($ccSwitchSignals.Count -eq 0) {
    [pscustomobject]@{
        cc_switch_candidate = $false
        recommendation = '未发现明确 CC Switch 候选。默认使用当前 Codex provider base_url 或用户提供的远端 upstream。'
    } | ConvertTo-Json -Depth 6
} else {
    [pscustomobject]@{
        cc_switch_candidate = $true
        signals = $ccSwitchSignals
        recommendation = '发现本地 CC Switch 候选。先询问用户是否希望模型请求经过 CC Switch；如果是，用对应 http://127.0.0.1:<port>/v1 作为 upstream_base，并用 verify-upstream 或 install --start 验证。'
    } | ConvertTo-Json -Depth 8
}
```

报告检测 JSON 时不要把它说成确定结论。按以下规则处理：

- 如果没有 CC Switch 候选，或用户确认不通过 CC Switch，按默认流程启用，让 `install --start` 使用当前 Codex provider 的 `base_url` 作为 upstream，或使用用户明确提供的远端 upstream。
- 如果检测到 `http://127.0.0.1:15721/v1` 等本地 OpenAI-compatible 端口，且用户确认当前第三方 API key / 模型流量由 CC Switch 承接，则把 upstream 设置为该本地地址。例如：

```powershell
python -m codex_fast_proxy verify-upstream --upstream-base http://127.0.0.1:15721/v1
python -m codex_fast_proxy install --start --upstream-base http://127.0.0.1:15721/v1
```

- 如果当前 Codex config 已经把 provider `base_url` 配成 CC Switch 地址，普通 `install --start` 会把这个地址解析为 `upstream_base`；仍需报告这是 CC Switch 路径，并确认 verification 成功。
- 如果用户提供的 key 是 CC Switch 的 key，而不是最终 OpenAI/三方 provider 的 key，不要把 upstream 指向 `https://api.openai.com/v1` 或远端 provider；应指向 CC Switch。
- 明确避免环路：CC Switch 的上游不能再指回 `http://127.0.0.1:8787/v1`。正确链路应是 `Codex App -> codex-fast-proxy(:8787) -> CC Switch(:15721) -> 真正 provider`。

重启 Codex App 或打开新 CLI 进程后，用户可以要求：

- `启用 Codex Fast proxy`
- `准备 Codex Fast proxy 以便使用 ChatGPT 账户登录`
- `为 Codex Fast proxy 启用全局 Fast 注入`
- `查看 Codex Fast proxy 状态`
- `停止 Codex Fast proxy`

默认启用使用 `--service-tier-policy auto`。在 ChatGPT-login 或状态不明确时，它尊重 Codex App/CLI 的 Fast UI 选择；在 API-key 模式下，当 Codex 省略 `service_tier` 时，它可能注入 priority tier，因为 App Fast UI 可能不可用。只有当用户明确要求全局 Fast 注入时，才使用 `--service-tier-policy inject_missing`；只有当用户明确要求不做 proxy-side Fast 注入时，才使用 `--service-tier-policy preserve`。

默认 `install --start` 会 best-effort 准备 ChatGPT login 兼容性：如果能从 `auth.json` 或环境变量发现当前 provider key，就复制到 proxy 管理的 `~/.codex/codex-fast-proxy-state/provider-auth.json`，并启用 provider auth file；如果找不到 key，仍按保留 Codex 原始 Authorization 的模式继续启用，不阻塞 API-key 模式。报告结果里的 `install_provider_auth_preparation`、`provider_auth_preparation` 和 `upstream_auth`，用于说明这次是否已经准备好 ChatGPT login。

如果用户希望 ChatGPT login 兼容插件/GitHub/Apps/connectors，同时模型请求仍使用第三方 provider，而默认启用没有找到 key，请再用 `prepare-chatgpt-login` 准备 proxy provider auth file，并使用 `set-upstream --use-provider-auth-file`；不要让用户把 API key 粘贴到聊天里，除非用户明确要求恢复操作，否则不要编辑 `auth.json`。这个 auth override 只作用于已经经过本地 proxy 的 provider API 请求；不能拦截或修改 ChatGPT plugin/GitHub/App connector 流量。在 override 模式下，proxy 会替换 provider `Authorization`，并在转发上游前丢弃意外的 `Cookie` header。

如果 Codex 当前通过第三方 provider 正常工作，而用户想为 ChatGPT login 做准备，先 dry run：

```powershell
python -m codex_fast_proxy prepare-chatgpt-login
```

报告非 secret JSON 字段，然后在运行以下命令前询问用户：

```powershell
python -m codex_fast_proxy prepare-chatgpt-login --apply
```

apply 步骤会把当前可用 provider key 复制到 `~/.codex/codex-fast-proxy-state/provider-auth.json`，不会打印 key，不会修改 proxy settings，也不会编辑 `auth.json`。apply 后运行：

```powershell
python -m codex_fast_proxy set-upstream --use-provider-auth-file
```

manager 会在保存 auth split 前验证带 `stream=true` 的 `POST /v1/responses`。如果结果报告 `needs_restart=true`，告诉用户重启 Codex App 或打开新 CLI 进程。

成功执行 `install --start` 后，先检查安装结果或随后的 `status` JSON。稳定启用必须同时满足：

- `healthy=true`
- `config_matches=true`
- `startup_hook=true`
- `startup_hook_trust.ready=true`
- `runtime_matches=true`
- `needs_restart=false`
- `base_url=http://127.0.0.1:8787/v1`

不要只因为 `config_switched=true` 或 `base_url` 已经变成 `http://127.0.0.1:8787/v1` 就声称启用成功。如果 config 已经指向本地 proxy，但 `healthy=false`、`runtime_matches=false`、`needs_restart=true`、startup hook 缺失或 hook trust 未 ready，这仍然是不可用或不稳定状态；应报告诊断字段，并按 `next_user_action` 修复或要求用户重启，而不是让用户继续切换登录方式。

成功执行 `install --start` 后，报告非 secret 的顶层 `next_user_action`、`chatgpt_login_hint` 和 `install_provider_auth_preparation` 字段。当 `chatgpt_login_hint.status=ready` 时，告诉用户 provider auth 已由 proxy 管理，可以保留当前 API-key 模式，也可以在需要完整 Codex App UI 时切到 ChatGPT login。当 `chatgpt_login_hint.status=optional_setup_available` 时，告诉用户可以保留当前 API-key 模式来使用第三方 API + 全局 Fast；如果想使用插件市场、GitHub/Apps/connectors、手动 Fast 控制、状态提示和语音输入等更完整 Codex App UI，应在切换 Codex App 到 ChatGPT login 前让 Codex 运行 `prepare-chatgpt-login`。

首次启用或 model-path 设置变更前，`install --start` 会用 `stream=true` 发送一个 Codex-style `POST /v1/responses` 请求，验证候选 upstream 和 auth source。这是真实 provider 流量，可能消耗少量 quota。如果验证失败，不要用 `--no-verify` 重试，除非用户明确接受下一个 Codex session 可能无法访问模型。

启用也会写入 Codex hook feature flags 和 trusted hook state entry。把 `startup_hook: true` 视为已安装、已启用、已信任；如果 `startup_hook_trust` 报告 `modified` 或 `untrusted`，重新运行 enable/update，而不是只依赖 `~/.codex/hooks.json`。

## 已存在安装

如果仓库已经存在，请获取并遵循：

- `https://raw.githubusercontent.com/Basic-XYZ/codex-fast-proxy/main/.codex/UPDATE.md`
