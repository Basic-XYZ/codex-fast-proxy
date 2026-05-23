---
name: codex-fast-proxy
description: Codex App Fast proxy 和第三方 OpenAI 兼容 API 的鉴权拆分工具。支持 ChatGPT 登录、priority service_tier、Responses API 基准测试、启用/检查/更新/卸载。
---

当用户希望 Codex 管理本地 auth-split 和 Codex App Fast proxy 时，使用此 skill。

## 触发模式

- 启用请求，例如“启用 Codex Fast proxy”。
- App Fast 请求，例如“让 Codex App 使用 Fast”。
- 指定 provider 的请求，例如“为 PackyAPI 启用 Fast”。
- ChatGPT 登录兼容请求，例如“插件可用但模型请求 401”。
- 基准测试请求，例如“运行 Fast proxy 基准测试”或“检查我的 provider 是否支持 Fast”。
- 上游 URL 修改，例如“把 Codex Fast proxy upstream 设置为 https://api.example.com/v1”。
- 维护请求，例如“显示状态”、“检查更新”、“停止”或“卸载”。

## 执行方式

以 manager 作为唯一可信入口：

```powershell
python -m codex_fast_proxy doctor
python -m codex_fast_proxy install --start
python -m codex_fast_proxy install --start --use-provider-auth-file
python -m codex_fast_proxy prepare-chatgpt-login
python -m codex_fast_proxy prepare-chatgpt-login --apply
python -m codex_fast_proxy verify-upstream --upstream-base https://api.example.com/v1
python -m codex_fast_proxy set-upstream --upstream-base https://api.example.com/v1
python -m codex_fast_proxy set-upstream --use-provider-auth-file
python -m codex_fast_proxy set-upstream --clear-upstream-auth
python -m codex_fast_proxy set-upstream --service-tier-policy auto
python -m codex_fast_proxy set-upstream --service-tier-policy inject_missing
python -m codex_fast_proxy status
python -m codex_fast_proxy check-update
python -m codex_fast_proxy benchmark
python -m codex_fast_proxy autostart --quiet
python -m codex_fast_proxy stop --force
python -m codex_fast_proxy uninstall --defer-stop
python -m codex_fast_proxy uninstall
```

## 安全模型

- 安装 repo 或 skill 不得修改 Codex provider config。
- 使用 `install --start` 启用；它会先启动本地 proxy，再切换 Codex config。
- 默认后台路径只允许监听 loopback host。不要建议用户把 `install --start`、`start` 或 autostart 配成 `0.0.0.0`；proxy 本身不做客户端鉴权。只有受控前台调试 `serve --allow-non-loopback` 才能显式放开。
- 稳定启用不能只看 `config_switched=true` 或 provider `base_url` 已经变成 `http://127.0.0.1:8787/v1`。成功启用必须同时满足 `healthy=true`、`config_matches=true`、`startup_hook=true`、`startup_hook_trust.ready=true`、`runtime_matches=true`、`needs_restart=false`，并确认 `base_url=http://127.0.0.1:8787/v1`。任一条件失败时，报告诊断和 `next_user_action`，不要告诉用户已经可以切 ChatGPT login 或继续依赖当前 session。
- 启用还会在 `~/.codex/hooks.json` 中安装一个 user-level Codex `SessionStart` hook，并启用 Codex hooks feature flag。较新的 Codex build 使用 `features.hooks = true`；旧文档/build 可能使用 `features.codex_hooks`。在 CLI/App 过渡期间，写入两个 key，并把任意一个 key 视为启用。hook 只会在 recorded provider 仍指向本地 proxy 时，在未来 Codex session 中启动缺失的 proxy。它不能因为 runtime code stale 就重启已经健康的 proxy。当前 Codex build 也可能需要 trusted hook state entry，因此把 `startup_hook: true` 视为已安装、已启用、已信任；如果 `startup_hook_trust` 报告 `modified` 或 `untrusted`，重新运行 enable/update，而不是只依赖 `~/.codex/hooks.json`。
- 启用状态下更新后，`install --start` 会比较运行中 proxy runtime 和已安装代码；当 config 仍指向本地 proxy 时，会在返回前重启 stale proxy runtime。Codex 可能为每个新 session 或 resumed session 触发 `SessionStart`；`autostart --quiet` 不记录正常 no-op 检查，也不会隐式刷新 stale runtime。
- 不要运行普通 `install` 来启用 proxy；manager 会拒绝在没有 `--start` 时切换 config。
- 默认 service tier policy 是 `auto`：ChatGPT-login 或状态不明确时保留 Codex App/CLI Fast 选择；API-key 模式下，当 Codex 省略 `service_tier` 时可以注入 priority，因为 App Fast UI 可能不可用。只有当用户明确要求全局 Fast 注入，并接受 Codex App 的 Fast UI toggle 不再控制缺失 tier 的请求时，才使用 `--service-tier-policy inject_missing`。只有当用户明确要求没有 proxy-side Fast 注入时，才使用 `--service-tier-policy preserve`。
- 首次启用或 model-path 设置变更前，`install --start` 会用一个 side-path Codex-style `POST /v1/responses` 请求验证候选 upstream 和 auth source，并使用 `stream=true`。如果验证失败，不要传 `--no-verify`，除非用户明确接受未来 Codex 模型请求可能失败。
- 已启用但 settings 里还没有 `service_tier_policy` 的旧安装，如果也没有 split upstream auth，属于 legacy global-Fast install；除非用户明确要求 App-controlled Fast，否则保留为 `inject_missing`。缺失 policy 且带 split upstream auth 的形态属于 ChatGPT-login auth split 路径，应视为 App-controlled `preserve`。
- 默认 `install --start` 会 best-effort 准备 provider auth file：如果能从 `auth.json` 或环境变量发现当前 provider key，就写入 proxy 管理的 `provider-auth.json` 并启用 `upstream_api_key_file`；如果找不到 key，继续使用 preserved auth 启用 proxy，不阻塞普通 API-key 模式。显式 `--use-provider-auth-file` 仍是强要求，缺 key 时必须失败。
- 对 ChatGPT 账户登录兼容性，优先使用 proxy-managed provider auth file，而不是编辑 `auth.json`、传入 literal key 或写全局用户环境变量。这样 proxy 会替换已经路由到本地 proxy 的上游 model-provider `Authorization` header，同时不影响 ChatGPT plugin/GitHub/App connector 请求。在 override 模式下，proxy 也会在转发 provider API 请求前丢弃意外的 `Cookie` header。现有 `--upstream-api-key-env <ENV_NAME>` 安装仍作为高级兼容路径支持。
- 当用户想要 ChatGPT login 兼容性时，先 dry run `prepare-chatgpt-login`。它可能在 `auth.json` 或环境中找到当前可用 provider key，但不得打印 key。报告非 secret JSON 字段，征得同意后再运行 `prepare-chatgpt-login --apply`。apply 后运行 `set-upstream --use-provider-auth-file`，让 streaming `/v1/responses` side-path verification 成功后再保存 settings。
- 如果 `set-upstream --use-provider-auth-file` 返回 `restart_required=true`，或随后的 `status` 报告 `needs_restart=true`，不要告诉用户现在可以用 ChatGPT 登录。说明 provider auth 已验证并保存，但运行中的 proxy 尚未加载新的 override。用户必须重启 Codex App，或明确允许 `python -m codex_fast_proxy start`，然后再登录 ChatGPT。
- provider auth split 激活且 `status.needs_restart=false` 后，告诉用户可以登录 ChatGPT，并在存在时报告 `chatgpt_login_windows_troubleshooting` JSON 字段。
- 如果 proxy startup 或 config switching 失败，manager 会在返回前恢复备份 config。
- 当用户想在 proxy 已启用时修改 provider URL、upstream auth source 或 service tier policy，使用 `set-upstream`。它必须保持 Codex config 指向本地 proxy，更新已保存 settings 和 uninstall baseline，并在 config 不再指向 recorded proxy 时拒绝执行。不要传 `--restart`，除非用户明确接受重启 proxy 可能中断当前 proxy-backed Codex session。不带 `--restart` 时，告诉用户重启 Codex App、打开新 CLI 进程，或稍后运行 `start` 来应用新 upstream。
- 当用户想测试候选 upstream 或 auth source 且不修改本地状态时，使用 `verify-upstream`。它必须运行与 `set-upstream` 相同的 streaming `/v1/responses` side-path check，然后停止，不写 settings、不编辑 Codex config、不安装 hooks、不重启 proxy。
- proxy 启用时，不要直接编辑 active provider 的 `base_url`。ChatGPT login 兼容性应通过 `prepare-chatgpt-login --apply` 和 `set-upstream --use-provider-auth-file` 配置 upstream provider auth，而不是编辑 `auth.json`。Model、reasoning 和其他 Codex config 字段仍可由用户或 agent 直接编辑。
- 运行中的 Codex process 不会热切换 provider config。启用后，重启 Codex App 并按需恢复同一对话，或打开新 CLI 进程。
- 如果当前 process 已经在使用 proxy，停止 proxy 可能中断对话。用 `uninstall --defer-stop` 禁用，告诉用户重启 Codex App 或打开新 CLI 进程，然后再次运行 uninstall 完成清理。
- 如果 uninstall output 有 `status="confirmation_required"`，说明没有应用任何卸载变更。先报告 `direct_upstream_auth_warning`。询问用户是要保持 proxy 启用、先把 Codex App 切回 API-key/第三方 provider 鉴权再卸载，还是明确接受 ChatGPT-login direct-upstream 401 风险继续。只有明确确认后，才用 `--confirm-chatgpt-direct-uninstall` 重新运行。
- 如果确认卸载后的 output 包含 `direct_upstream_auth_warning`，在任何重启说明前报告它。恢复 direct upstream 后不再有 proxy auth override；如果 Codex App 仍保持 ChatGPT 登录，第三方 provider 可能收到 ChatGPT auth 并返回 401。告诉用户重启前切回 API-key/第三方 provider 鉴权，或者如果想通过 ChatGPT-login UI 使用第三方 provider，就保持 proxy 启用。
- 卸载只移除 `codex-fast-proxy` hook，必须保留无关 hook。
- 当 Codex config 仍指向 proxy 时，不要运行 `stop`，除非用户明确接受当前和未来 session 可能失败。
- 只有当用户明确要求 A/B check 或确认费用时，才运行 `benchmark`。默认 benchmark 使用 `codex-cli` 模式：它启动本地 forwarding capture proxy，发起真实 `codex exec` 请求，并对保存的 upstream 运行三组 interleaved default-vs-priority 样本。它可能消耗明显 token quota。它使用现有 Codex/provider authentication，记录上游延迟但不存储响应内容；即使 provider response 不暴露 `service_tier`，也应比较 full-response latency。
- 当用户询问 provider 是否支持 Fast/Priority 时，运行或要求足够输入来运行默认 `full` profile 的 `benchmark`。不要把普通 proxy logs、`service_tier_injected=true` 或 HTTP 200 当成 provider Fast 支持证明；这些只证明 proxy 发送了成功请求。如果自动 auth discovery 无法在 env/provider config/`~/.codex/auth.json` 中找到 key，询问用户 API key environment variable name，再用 `--api-key-env` 重跑。
- 默认 benchmark timeout 是每个 sample 600 秒。如果 `full` benchmark 报告 `TimeoutExpired`，在下稳定性结论前，用更大的显式 timeout 重跑，例如 `--timeout 900`。
- `status` 和 `doctor` 包含本地 health check 和 runtime check；把 `healthy=false` 视为停止并诊断的理由。如果 update 后 `status.needs_restart=true`，告诉用户重启 Codex App、在旧 proxy 消失后打开新 CLI 进程，或在安全时运行 `python -m codex_fast_proxy start` 刷新 runtime code。Startup hook 不应该仅因 runtime code stale 就重启已经健康的 proxy。
- 如果用户只要求检查更新，运行 `check-update` 后停止。它是只读命令，不得 pull、install、重启 proxy、编辑 Codex config 或写入 proxy state。
- 成功启用后，报告 JSON result、顶层 `next_user_action`、`chatgpt_login_hint` message 和 `install_provider_auth_preparation`。如果 `chatgpt_login_hint.status=ready`，告诉用户 provider auth 已由 proxy 管理，可以保留当前模式，也可以在需要完整 Codex App UI 时登录 ChatGPT。如果 `chatgpt_login_hint.status=optional_setup_available`，告诉用户可以保留 API-key 模式用于第三方 API + 全局 Fast；如果想使用插件市场、GitHub/Apps/connectors、手动 Fast 控制、状态提示和语音输入等更完整 Codex App UI，应在切换 Codex App 到 ChatGPT login 前运行 `prepare-chatgpt-login`。不要在同一 turn 串联无关工作。

## Sandbox 与 approval 纪律

- clone GitHub、用 `pip` 安装、创建 `~/.agents` skill link、写 `~/.codex/config.toml`、写 `~/.codex/hooks.json`、启动后台 proxy 或移除安装文件等操作，可能需要用户 approval 或 elevated sandbox permissions。
- 如果 harness 支持 escalation，为预期命令请求 approval，而不是尝试其他路径。
- 如果命令因为网络、权限、sandbox 写入限制、skill link 创建或后台进程限制失败，停止并带 approval 重新运行同一个预期动作。不要发明绕过用户 sandbox policy 的 workaround。
- 不要打印 API key、request body、prompt 或 Codex history。除非用户明确要求恢复操作，否则不要编辑 `auth.json`；优先用 `prepare-chatgpt-login --apply` 把当前可用 provider key 复制到 proxy-managed provider auth file。

## 用户交接消息

- `.codex/INSTALL.md` 或 `.codex/UPDATE.md` 修改 skill 文件后，明确告诉用户重启 Codex App 并回到对话，或打开新 CLI 进程，让 Codex 重新扫描 `~/.agents/skills`；然后让 Codex 启用 Codex Fast proxy。
- `.codex/UNINSTALL.md` 后，明确告诉用户重启 Codex App，或打开新 CLI 进程，让 Codex 从 skill list 移除 `codex-fast-proxy`。
- 成功执行 `install --start` 后，只有在结果或随后的 `status` 同时满足 `healthy=true`、`config_matches=true`、`startup_hook=true`、`startup_hook_trust.ready=true`、`runtime_matches=true`、`needs_restart=false`，且 `base_url=http://127.0.0.1:8787/v1` 时，才明确告诉用户 Fast proxy 已稳定启用。即使稳定启用，当前 Codex process 也不会热切换；他们应该重启 Codex App 并回到对话，或打开新 CLI 进程。
- 成功执行 `install --start` 后，即使 status summary 已经很长，也必须追加这个可选 ChatGPT-login UI 提示：用户可以保留 API-key 模式用于第三方 API + 全局 Fast。如果想使用插件市场、GitHub/Apps/connectors、手动 Fast 控制、状态提示和语音输入等更完整 Codex App UI，应在切换 Codex App 到 ChatGPT login 前运行 `prepare-chatgpt-login`；直接切换可能导致 401。
- `uninstall --defer-stop` 返回 `status="confirmation_required"` 后，明确告诉用户因为 ChatGPT login 看起来处于活跃状态且 direct upstream 可能返回 401，所以没有应用任何卸载变更。不要让用户现在重启。
- `uninstall --defer-stop` 返回 `status="uninstalled"` 后，明确告诉用户 Codex config 已恢复为 direct upstream，proxy 被临时保留运行以避免中断当前 process。他们应该重启 Codex App 并回到对话，或打开新 CLI 进程，然后再次运行 uninstall 完成清理。
- 如果确认卸载后存在 `direct_upstream_auth_warning`，先警告 ChatGPT login 看起来处于活跃状态。恢复 direct upstream 后，请求不再经过 proxy upstream auth override。保持 ChatGPT login 可能把 ChatGPT auth 发给第三方 provider 并返回 401。用户应在重启前切回 API-key/第三方 provider 鉴权，或者保持 proxy 启用以便通过 ChatGPT-login UI 使用第三方 provider。

只有当用户指定 provider，或 `doctor` 报告无法选择 active provider 时，才使用 `--provider <name>`。

只有当 Codex config 不包含可用 provider `base_url`，或用户明确想使用不同 upstream 时，才使用 `--upstream-base <url>`。
只把 `--upstream-api-key-env <ENV_NAME>` 作为带 environment variable name 的高级兼容路径使用，绝不要传 literal key value。
当用户想停止覆盖 upstream Authorization 并回到 Codex 原始 provider auth 行为时，使用 `--clear-upstream-auth`。

启用后的 upstream URL 修改，优先使用 `set-upstream --upstream-base <url>`，不要重新运行 `install --start --upstream-base <url>`。

## 结果处理

- 把 JSON output 作为唯一可信来源。
- 不要把 `config_switched=true`、`config_matches=true` 或 `base_url=http://127.0.0.1:8787/v1` 单独当成成功。config 指向本地 proxy 但 proxy 不健康、runtime 不匹配、hook 未安装或 hook trust 未 ready 时，用户仍可能遇到 502 或无法打开 `127.0.0.1:8787`。
- 在存在时报告 `provider`、`base_url`、`upstream_base`、`service_tier_policy`、`upstream_auth`、`running`、`diagnosis`、`provider_auth_preparation`、`chatgpt_login_hint`、`next_user_action`、`chatgpt_login_windows_troubleshooting`、`runtime_matches`、`needs_restart`，以及 backup 或 restore 状态。
- 诊断 stale runtime、错误 Python executable 或 startup hook 指向不同 checkout 时，使用 `status.runtime`。不要只从 `~/.codex/hooks.json` 推断 hook 是否就绪。
- 对 App-specific traffic 检查，用最近的 `/v1/responses` events 作为模型生成证据。把 `GET /v1/models` 视为 provider metadata 检查；除非 `/v1/responses` 也失败，不要把孤立的 `/v1/models` 失败报告为模型生成失败。
- 不要打印 API key、`auth.json`、request body、prompt 或 Codex history。
- 对 benchmark results，报告 profile、medians、observed speedup、`priority_accepted`、`observed_priority_effective`、存在时的 provider-confirmed priority metadata、sample counts、`service_tier_control.valid` 和 errors。优先 full-response total latency 和 first-output latency，而不是 first-event/TTFB。
  把 `priority_accepted=true` 视为 wire parameter 被接受的证明，把 `observed_priority_effective=true` 视为此测量 workload 获益的证明。报告 `benchmark_mode`，不要把 Codex CLI/app-server benchmark 结果说成 App-specific guarantee。App-specific verification 应在用户发送 App 消息后使用最近 dashboard/proxy traffic。`priority_accepted=true` 表示至少一个 priority sample 成功；始终报告显示的 `ok/count` sample counts。不要基于单次运行声称 guaranteed speedup。
- 如果 install 或 update 修改了 skill 文件，告诉用户重启 Codex。

## 预期行为

- `install --start` 备份 `~/.codex/config.toml`。
- selected provider 的原始 `base_url` 变为 `upstream_base`。
- selected provider 的 `base_url` 变为 `http://127.0.0.1:8787/v1`。
- 首次启用前，`install --start` 会在切换 config 前，对 candidate upstream/auth route 验证一次 streaming `/v1/responses` 请求，除非用户明确接受 `--no-verify`。
- `verify-upstream` 报告相同 candidate route validation，但不修改 persistent state。
- `set-upstream` 更新保存的 `upstream_base`、service tier policy、upstream auth source 和 uninstall recovery baseline，不改变 model、reasoning、tools、input 或 literal API key value。写 settings 前，它会向 candidate upstream/auth source 发送一个 side-path Codex-style `POST /v1/responses` 请求，并带 `stream=true`。这是真实 provider 流量；如果失败，不要加 `--no-verify`，除非用户明确接受未来 Codex 请求可能中断。它只会在 proxy 未运行或用户明确接受 `--restart` 时立即应用；否则会延迟重启运行中的 proxy，避免切断当前响应。
- `SessionStart` hook 会在未来 Codex session 中调用当前 Python executable，并带 `-m codex_fast_proxy autostart --quiet`。
- 默认 `auto` 在 ChatGPT-login 或状态不明确时保留 Codex App/CLI `service_tier` 选择；API-key 模式下，当字段缺失时可注入 `service_tier="priority"`。只有显式 `inject_missing` 会不区分 login mode 强制全局 Fast。
- 可选 upstream auth split 作用于 proxied provider API 请求，不作用于 ChatGPT plugin、GitHub、Apps、connector、cookie 或 token 流量；override 模式会替换 `Authorization`，并在转发上游前丢弃意外 `Cookie` header。
- `benchmark` 比较不带 `service_tier` 的 synthetic Codex-style 请求与 `service_tier="priority"` 请求。默认 `codex-cli` 模式用于测量真实 Codex 加速；`--profile smoke` 只是低成本连通性检查；Codex CLI 不可用时，`--mode direct` 是较不具代表性的 fallback。它只把脱敏指标存储到 `~/.codex/codex-fast-proxy-state/state/fast_proxy.benchmark.json`。本地 dashboard 显示最近保存的 benchmark summary，永远不会启动 benchmark run。
- 当当前 config 仍匹配 installed state 时，`uninstall` 恢复完整 backup。
- 如果 config 变过，但 selected provider 仍指向本地 proxy，`uninstall` 只把该 provider 的 `base_url` 恢复为 `upstream_base`，并保留其他 config changes。
- 如果 ChatGPT login 处于活跃状态，而 uninstall 会新恢复 direct upstream，除非显式 `--confirm-chatgpt-direct-uninstall`，否则 `uninstall` 会在修改 config、hooks、proxy process 或 files 前返回 `status="confirmation_required"`。
- 如果 `uninstall` 报告 `config_restore="skipped_config_changed"`，不要删除 package 或 repo；selected provider 已不再指向 recorded proxy，所以在使用 `--force` 前先询问用户。
