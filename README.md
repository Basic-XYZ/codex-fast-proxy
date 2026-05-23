# codex-fast-proxy

[![CI](https://github.com/Basic-XYZ/codex-fast-proxy/actions/workflows/ci.yml/badge.svg)](https://github.com/Basic-XYZ/codex-fast-proxy/actions/workflows/ci.yml)

Codex App 的鉴权拆分代理，面向第三方 OpenAI 兼容 API。

你可以让 Codex App 继续使用 ChatGPT 账户登录，从而保留完整 App UI；同时把模型请求继续发给你的第三方 OpenAI 兼容 API。`codex-fast-proxy` 会把 provider 流量转到本地代理，按需使用独立 provider 鉴权，保持流式响应不变，并在 Codex App 自带 Fast 控制可用时尊重它的选择。

[中文指南](docs/README.zh-CN.md) · [快速开始](#快速开始) · [常用流程](#常用流程) · [仪表盘](#仪表盘) · [安全边界](#安全边界) · [高级用法](docs/advanced-usage.md) · [赞助](#赞助)

![Codex Fast Proxy 概览](docs/assets/codex-fast-proxy-promo.gif)

## 为什么需要它

Codex App 的插件市场、GitHub/Apps 连接器、手动 Fast 控制、状态提示和语音输入等能力通常和 ChatGPT 账户登录绑定。但使用第三方 API provider 的用户仍然希望模型请求走自己的 provider endpoint 和 API key。

这个项目把这两件事拆开：Codex App 可以保持 ChatGPT 账户登录来使用 UI 和连接器能力，而 `/v1/responses` 模型流量继续走你配置的 provider。Fast/Priority 被当成 provider 能力来测量，而不是默认假设一定有效。

## 它做什么

- 让 Codex App 保持 ChatGPT 账户登录，同时让 provider API 请求使用你的第三方上游。
- 将 Codex provider 流量从 `http://127.0.0.1:8787/v1` 转发到保存的上游 provider。
- 可选地用 proxy 管理的本地鉴权文件替换 proxied provider 请求里的 `Authorization`，避免把 ChatGPT 账户鉴权转发给第三方 provider。
- 只在策略允许时修改 `POST /v1/responses`。
- 不改变 `model`、`reasoning`、`tools`、`input`、请求体字段和 SSE frame。
- 当 Codex App 自己发送 `service_tier` 时，保留 App 的手动 Fast 选择。
- 安装 Codex `SessionStart` hook，让后续 Codex session 可以拉起缺失的 proxy。
- 提供只读本地仪表盘，展示脱敏状态、最近流量和 benchmark 摘要。

## Fast 效果

Fast/Priority 很重要，但本地 proxy 不能保证加速。这个 proxy 可以发送 priority hint，真实延迟效果取决于上游 OpenAI 兼容 provider。有些 provider 会接受 `service_tier="priority"`，但实际测量 workload 不一定更快；有些 provider 也不会在响应 metadata 中回显 priority。

请用内置 A/B 基准测试作为当前 provider 和模型的判断依据：

```text
运行 Codex Fast proxy A/B benchmark
```

基准测试会区分三件事：priority 请求是否被接受、测量任务是否变快、provider 响应 metadata 是否明确确认 priority。它还会记录对照组拆分是否有效，也就是 default 样本必须不带 `service_tier`，priority 样本必须发送预期值。

## 快速开始

把这句话贴给 Codex：

```text
获取并遵循 https://raw.githubusercontent.com/Basic-XYZ/codex-fast-proxy/main/.codex/INSTALL.md 里的说明
```

然后重启 Codex App，回到同一对话，说：

```text
启用 Codex Fast proxy
```

启用后，再次重启 Codex App，或者打开新的 Codex CLI 进程，让 Codex 重新加载 provider 配置。后续 session 会使用已安装的 startup hook。

安装步骤刻意只安装文件：它会克隆仓库、安装 Python package、链接 skill。只有你明确启用后，它才会切换 provider、启动 proxy 或安装 hook。

## 常用流程

大多数用户应该通过自然语言让 Codex 操作：

| 目标 | 对 Codex 说 |
| --- | --- |
| 从 GitHub 安装 | `获取并遵循 https://raw.githubusercontent.com/Basic-XYZ/codex-fast-proxy/main/.codex/INSTALL.md 里的说明` |
| 启用 proxy | `启用 Codex Fast proxy` |
| 查看状态 | `查看 Codex Fast proxy 状态` |
| 打开仪表盘 | 打开 `http://127.0.0.1:8787/v1` |
| 准备 ChatGPT 登录 | `准备 Codex Fast proxy 以便使用 ChatGPT 账户登录` |
| 运行 A/B 基准测试 | `运行 Codex Fast proxy A/B 基准测试` |
| 修改上游 URL | `把 Codex Fast proxy 上游设置为 https://api.example.com/v1` |
| 检查更新 | `检查 Codex Fast proxy 更新` |
| 更新 | `获取并遵循 https://raw.githubusercontent.com/Basic-XYZ/codex-fast-proxy/main/.codex/UPDATE.md 里的说明` |
| 卸载 | `获取并遵循 https://raw.githubusercontent.com/Basic-XYZ/codex-fast-proxy/main/.codex/UNINSTALL.md 里的说明` |

高级命令用法见 [docs/advanced-usage.md](docs/advanced-usage.md)。

## 启用后

健康启用状态应该包含：

- `healthy=true`
- `config_matches=true`
- `startup_hook=true`
- `startup_hook_trust.ready=true`
- `runtime_matches=true`
- `needs_restart=false`
- `base_url=http://127.0.0.1:8787/v1`

`base_url` 指向 `8787` 只代表配置已经切到本地 proxy；必须同时满足健康、hook trust、runtime 和 restart 状态，才算稳定启用。否则可能出现 config 已切换但本地 proxy 没起来，最终请求返回 502 或无法打开仪表盘。

在 API-key 模式下，默认 `auto` 策略可以在 Codex 省略 `service_tier` 时注入全局 priority，因为此时 App Fast UI 可能不可用。在 ChatGPT-login 或状态不明确时，默认行为更保守，会保留 Codex 自己的 Fast 选择。

## 使用 ChatGPT 登录

ChatGPT 登录是可选的。只有当你想使用完整 Codex App UI，例如插件市场、GitHub/Apps 连接器、手动 Fast 控制、状态提示或语音输入时，才需要它。proxy 的 auth split 会在登录后继续把模型请求留在第三方 provider 上。

切换 Codex App 到 ChatGPT 登录前，先让 Codex 准备 provider 鉴权：

```text
准备 Codex Fast proxy 以便使用 ChatGPT 账户登录
```

manager 会把当前可用的第三方 provider key 复制到 `~/.codex/codex-fast-proxy-state/provider-auth.json`，不会打印 key。如果结果报告 `needs_restart=true`，先不要登录。先重启 Codex App，或者让 Codex 执行：

```powershell
python -m codex_fast_proxy start
```

如果 Windows 上 ChatGPT 登录失败并出现 `OSError: [WinError 10013] ... socket ...`，请在管理员 PowerShell 中依次运行：

```powershell
net stop winnat
netsh interface ipv4 show excludedportrange protocol=tcp
net start winnat
netsh interface ipv4 show excludedportrange protocol=tcp
```

如果 ChatGPT 登录失败并出现 `Token exchange failed ... 403 Forbidden: Country, region, or territory not supported`，重试前先检查路由：

- 确认 proxy 状态已经就绪，包括 `needs_restart=false`。
- 确认 provider auth 准备和 auth split 已经完成。
- 确保你的系统代理 / VPN 设置，包括必要时的 TUN 模式，会覆盖 Codex App/WebView 登录流量，而不只是模型 provider 流量。
- 临时关闭可能覆盖或分流登录路由的路由/代理切换工具，例如 `ccswitch`。
- 把这个问题视为 OpenAI OAuth token exchange 阶段的地区/路由拒绝，它和第三方 provider 鉴权失败是两件事。

## 仪表盘

打开：

```text
http://127.0.0.1:8787/v1
```

仪表盘只读。它会显示本地 proxy 状态、上游 URL、Fast 策略、鉴权模式、最近 `/v1/responses` 流量、metadata 检查，以及最近一次 benchmark 摘要。它不会显示 prompt、请求体、响应内容、API key、Cookie 或 header。

## 安全边界

- proxy 只处理 provider API 请求；不拦截 ChatGPT 插件市场、GitHub、Apps、连接器或 ChatGPT Cookie。
- `service_tier` 修改只限于 `POST /v1/responses`。
- SSE 流式响应会原样透传。
- 日志已脱敏，只包含 path、status、latency、stream flag、是否注入 `service_tier` 等运行 metadata。
- 必要时卸载采用两阶段：先恢复 config，让 proxy 为当前 session 临时保活，然后在 Codex 重启后清理。
- 如果 ChatGPT 登录处于活跃状态，而卸载会恢复 direct upstream，卸载会先停下并要求明确确认。你可以保持 proxy 启用、先切回 API-key/第三方 provider 鉴权再卸载，或者明确接受 direct third-party provider 可能因 ChatGPT auth 返回 401 的风险。

## Agent Skill 与发现

这个仓库包含 Codex Agent Skill：

- Skill 名称：`codex-fast-proxy`
- Skill 路径：`skills/codex-fast-proxy/SKILL.md`
- 主要用途：安装、启用、验证、基准测试、更新、修改上游、准备 ChatGPT 登录兼容性，以及卸载此 proxy。

索引公开 GitHub 仓库 Agent Skill 的工具可以在上述路径发现这个 skill。本项目不声明已上架 SkillsMP 或其他 marketplace，也不是 OpenAI 官方 plugin 或官方 marketplace 项目。

## Plugin 准备状态

仓库包含 `.codex-plugin/plugin.json` 元数据，指向 `./skills/`，用于未来 Codex plugin 分发流程。当前支持的安装路径仍然是上面的 Codex 管理式安装提示词。Plugin 元数据不会安装 hook、修改 provider config、启动 proxy，也不代表官方 marketplace 上架。

## 赞助

如果 `codex-fast-proxy` 节省了你的时间，可以在你自己的 GitHub Sponsors 或仓库说明中配置支持入口。

## 许可证

MIT
