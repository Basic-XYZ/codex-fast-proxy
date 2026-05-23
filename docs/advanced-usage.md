# 高级用法

本文把命令级细节从主 README 中拆出来。大多数用户应优先使用 [README.md](../README.md) 中的自然语言流程。

## 常用命令

以 manager 作为唯一可信入口：

```powershell
python -m codex_fast_proxy doctor
python -m codex_fast_proxy install --start
python -m codex_fast_proxy status
python -m codex_fast_proxy check-update
python -m codex_fast_proxy benchmark
python -m codex_fast_proxy start
python -m codex_fast_proxy stop --force
python -m codex_fast_proxy uninstall --defer-stop
python -m codex_fast_proxy uninstall
```

在 macOS/Linux 上，如果没有 `python`，使用 `python3 -m codex_fast_proxy ...`。

默认路径：

| 项目 | 路径 |
| --- | --- |
| 本地 proxy base URL | `http://127.0.0.1:8787/v1` |
| 仓库安装位置 | `~/.codex/codex-fast-proxy` |
| 运行状态目录 | `~/.codex/codex-fast-proxy-state` |
| Startup hook | `~/.codex/hooks.json` |
| 日志 | `~/.codex/codex-fast-proxy-state/state/fast_proxy.jsonl` |
| 配置备份 | `~/.codex/backups/codex-fast-proxy` |

## 状态与仪表盘

```powershell
python -m codex_fast_proxy status
```

健康启用状态应包含：

- `healthy=true`
- `config_matches=true`
- `startup_hook=true`
- `startup_hook_trust.ready=true`
- `runtime_matches=true`
- `needs_restart=false`

`config_matches=true` 或 `base_url=http://127.0.0.1:8787/v1` 不能单独代表可用。稳定启用必须同时确认 proxy 健康、startup hook 已安装且 trusted、运行中的 proxy runtime 与当前安装代码匹配，并且不需要重启。

常用状态字段：

- `diagnosis`：顶层运行判断。
- `fast_behavior`：可能是 `app_controlled`、`auto_global_priority`、`global_priority`、`preserve_only` 或 `unknown_conservative`。
- `provider_auth_preparation`：provider auth 是否已经为可选 ChatGPT 登录准备好。
- `chatgpt_login_hint` 和 `next_user_action`：面向用户的下一步。
- `runtime`：manager 源路径、运行中 proxy runtime，以及 startup hook command。

仪表盘 URL：

```text
http://127.0.0.1:8787/v1
```

仪表盘只读且脱敏。它会把 `GET /v1/models` 归类为 provider metadata 检查，避免挤掉真实模型生成流量。

## ChatGPT 登录兼容性

Codex App 插件、GitHub、Apps/connectors、手动 Fast 控制、状态提示和语音输入可能依赖 ChatGPT 账户登录。第三方 provider 模型请求仍应使用 provider key，而不是 ChatGPT 账户鉴权。

先做 provider key 发现的 dry run：

```powershell
python -m codex_fast_proxy prepare-chatgpt-login
```

`install --start` 会默认尝试做同样的 provider key 准备：能发现 key 时写入 proxy provider auth 文件并启用 auth split；找不到 key 时保留 Codex 原始 Authorization，不阻塞普通 API-key 模式。只有当启用结果里的 `chatgpt_login_hint.status` 不是 `ready`，并且你准备切到 ChatGPT 登录时，才需要继续手动执行下面的 apply 流程。

检查 dry-run 结果后，把当前可用 provider key 复制到 proxy provider auth 文件：

```powershell
python -m codex_fast_proxy prepare-chatgpt-login --apply
```

保存并验证 proxy auth split：

```powershell
python -m codex_fast_proxy set-upstream --use-provider-auth-file
python -m codex_fast_proxy status
```

auth 文件位于 `~/.codex/codex-fast-proxy-state/provider-auth.json`。它归 proxy 管理，不属于 Codex 的 `auth.json`，status 或日志不会打印 key。现有 `--upstream-api-key-env <ENV_NAME>` 配置仍作为高级兼容路径支持。

如果 `restart_required=true` 或最终 `status.needs_restart=true`，先不要用 ChatGPT 登录。请重启 Codex App、打开新 CLI 进程，或显式刷新 proxy：

```powershell
python -m codex_fast_proxy start
```

清除 auth override，恢复保留 Codex 原始 provider `Authorization` 行为：

```powershell
python -m codex_fast_proxy set-upstream --clear-upstream-auth
```

Windows 登录回调排障：

```powershell
net stop winnat
netsh interface ipv4 show excludedportrange protocol=tcp
net start winnat
netsh interface ipv4 show excludedportrange protocol=tcp
```

只有在 ChatGPT 登录失败并出现 `OSError: [WinError 10013] ... socket ...` 时使用这些命令。

## 修改上游或 Fast 策略

proxy 启用时，不要直接编辑 active provider 在 `config.toml` 里的 `base_url`。它应该继续指向本地 proxy。请修改保存的 upstream：

```powershell
python -m codex_fast_proxy set-upstream --upstream-base https://api.example.com/v1
```

只读验证上游：

```powershell
python -m codex_fast_proxy verify-upstream --upstream-base https://api.example.com/v1
```

Fast 策略：

```powershell
python -m codex_fast_proxy set-upstream --service-tier-policy auto
python -m codex_fast_proxy set-upstream --service-tier-policy preserve
python -m codex_fast_proxy set-upstream --service-tier-policy inject_missing
```

策略含义：

- `auto`：API-key 模式可以注入缺失的 priority；ChatGPT-login 或状态不明确时保留 Codex 选择。
- `preserve`：永不注入 service tier。
- `inject_missing`：仅在缺少 `service_tier` 时注入 `service_tier="priority"`。

除非明确跳过，`set-upstream` 会在写 settings 前发送一次 side-path Codex-style `POST /v1/responses` 请求，并使用 `stream=true`。这是真实 provider 流量，可能消耗少量 quota。

## 基准测试

自然语言触发：

```text
运行 Codex Fast proxy A/B 基准测试
```

命令：

```powershell
python -m codex_fast_proxy benchmark
```

默认基准测试使用 `codex-cli` 模式。它会通过本地 capture proxy 发起真实 `codex exec` 请求，并交错比较 default 与 priority 样本。它只保存脱敏指标。

常用选项：

```powershell
python -m codex_fast_proxy benchmark --timeout 900
python -m codex_fast_proxy benchmark --profile smoke
python -m codex_fast_proxy benchmark --mode direct
python -m codex_fast_proxy benchmark --api-key-env PACKY_API_KEY
```

结果解读：

- `service_tier_control.valid=true`：default 样本省略了 `service_tier`，priority 样本发送了预期值。
- `priority_accepted=true`：至少一个 priority 样本成功。
- `observed_priority_effective=true`：本次测量任务获益。
- `provider_confirmed_priority=true`：provider 响应 metadata 明确确认 priority；并非所有 provider 都会提供。
- 一定要结合样本数量和错误一起看这些 flag。

普通 proxy 日志中的 `service_tier_injected=true` 和 HTTP 200 只能证明 proxy 成功发送了请求。基准测试结果才是判断速度影响的更强信号。

## 更新

只读检查更新：

```powershell
python -m codex_fast_proxy check-update
```

遵循远端更新流程：

```text
获取并遵循 https://raw.githubusercontent.com/Basic-XYZ/codex-fast-proxy/main/.codex/UPDATE.md 里的说明
```

如果更新修改了 skill 文件，请重启 Codex App 或打开新 CLI 进程，让 skill discovery 重新加载。如果 proxy 已启用，更新流程会重新运行 `install --start`；在安全时它可能刷新 stale runtime。

## 卸载

遵循远端卸载流程：

```text
获取并遵循 https://raw.githubusercontent.com/Basic-XYZ/codex-fast-proxy/main/.codex/UNINSTALL.md 里的说明
```

两阶段卸载：

1. 如果 ChatGPT login 处于活跃状态且 direct upstream 可能 401，第一次运行会在修改 config、hook、proxy process 或文件前停下，并返回 `status="confirmation_required"`。
2. 明确确认后，或未检测到 ChatGPT direct-upstream 风险时，第一次运行会把 Codex config 恢复为 direct upstream，并移除 startup hook。
3. 它可能让 proxy process 临时保活，以便当前依赖 proxy 的 session 完成。
4. 重启 Codex App 或打开新 CLI 进程。
5. 再次运行卸载，停止剩余 proxy 并删除文件。

如果卸载返回 `status="confirmation_required"`，说明没有应用任何卸载变更。你可以保持 proxy 启用、先把 Codex App 切回 API-key/第三方 provider 鉴权再卸载，或明确继续：

```powershell
python -m codex_fast_proxy uninstall --defer-stop --confirm-chatgpt-direct-uninstall
```

如果确认卸载后返回 `direct_upstream_auth_warning`，说明 Codex config 已恢复为 direct upstream，但当前 Codex auth 状态仍像 ChatGPT 账户登录。Direct upstream 模式不再有 proxy auth override，所以模型请求可能把 ChatGPT auth 发给第三方 provider 并返回 401。重启前请切回 API-key/第三方 provider 鉴权，或者保持 proxy 启用以使用 ChatGPT-login UI 与第三方 provider。

## 终端恢复

如果模型请求已经坏掉，在 Codex 外部使用这些命令：

```powershell
python -m codex_fast_proxy status
python -m codex_fast_proxy start
python -m codex_fast_proxy set-upstream --clear-upstream-auth
python -m codex_fast_proxy uninstall --defer-stop
```

## 安全模型

- 默认只监听本机 loopback 地址。后台安装、自启动和 `start` 不会接受 `0.0.0.0` 这类非 loopback host，避免把未做客户端鉴权的 proxy 暴露到局域网。
- 只有手动前台 `serve` 支持 `--allow-non-loopback`，用于受控调试场景。
- `install --start` 在切换 config 前验证上游 `/v1/responses` streaming route。
- Startup hook 会在 `SessionStart` 时运行 `codex_fast_proxy autostart --quiet`。
- hook 只在 recorded provider 仍指向本地 proxy 时启动缺失的 proxy。
- 不会仅因 runtime code stale 就重启健康 proxy；准备刷新 runtime 时使用显式 `start`。
- 当 Codex config 仍指向 proxy 时，`stop` 会拒绝执行，除非显式传 `--force`。
- 卸载只删除 `codex-fast-proxy` hook，并保留无关 hook。
- 日志永不包含 API key、Cookie、请求体、prompt、tool 参数或响应内容。

## 开发

```powershell
python -m pip install --user -e .
python -m codex_fast_proxy doctor
python -m unittest discover -s tests -p "test_*.py"
```

前台运行 proxy：

```powershell
python -m codex_fast_proxy serve `
  --host 127.0.0.1 `
  --port 8787 `
  --proxy-base /v1 `
  --upstream-base https://api.example.com/v1 `
  --service-tier priority `
  --service-tier-policy auto
```
