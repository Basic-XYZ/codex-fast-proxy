# codex-fast-proxy 调试总结

## 整体架构（最终方案）

```
Codex App ──► codex-fast-proxy (:8787) ──► CC Switch (:15721) ──► OpenAI API
```

## 遇到的问题及解决

### 1. 上游服务不可用（502 Bad Gateway）
**问题**: 插件默认上游 `codex-byering.com:8317` 返回 502，无法连通。
**解决**: 将上游切换到用户本地环境中的 CC Switch（`http://127.0.0.1:15721/v1`）。

### 2. SSL 证书验证失败（SSLCertVerificationError）
**问题**: Python 3.12 的 certifi 在 macOS 上证书链不完整，连接 `api.openai.com` 时报错 `unable to get local issuer identifier`。且修复 certifi 需要 pip 安装，但 pip 本身也依赖 SSL（鸡生蛋问题）。
**解决**: 修改 `proxy.py` 的 `open_connection()` 方法，优先使用系统证书（`security find-certificate` 导出的 Mac 根证书），兜底使用 `ssl._create_unverified_context()` —— 实测本地环境不需要验证证书（CC Switch 走 HTTP，不是 HTTPS）。

```python
# proxy.py open_connection 核心改动
cafile = os.environ.get("SSL_CERT_FILE")
if not cafile or not os.path.exists(cafile):
    cafile = None
    mac_certs = Path.home() / ".codex" / "cacert.pem"
    if mac_certs.exists():
        cafile = str(mac_certs)
if cafile:
    ssl_ctx = ssl.create_default_context(cafile=cafile)
else:
    ssl_ctx = ssl._create_unverified_context()
```

### 3. API Key 来源不匹配（401 Unauthorized）
**问题**: 用户提供的 API 密钥（`sk-xxx`）不属于 OpenAI，而是 **CC Switch** 的密钥。直接向 `api.openai.com` 认证返回 401。
**解决**: 将上游指向本地的 CC Switch（`http://127.0.0.1:15721/v1`），由 CC Switch 负责和真正的 OpenAI API 通信。本地代理只需把密钥转发给 CC Switch。

### 4. 认证配置方式混乱
**问题**: codex-fast-proxy 有 `upstream_api_key_env`（环境变量）和 `upstream_api_key_file`（provider-auth.json）两种方式。一开始用环境变量方式，但 `OPENAI_API_KEY` 环境变量未设置；切到文件方式后，密钥的 JSON 格式又写错。
**解决**: 统一使用 `provider-auth.json` 文件方式，将 settings.json 中的 `upstream_api_key_env` 设为 `null`，`upstream_api_key_file` 设为 `true`。

### 5. provider-auth.json 格式错误
**问题**: 使用 echo 写入 JSON 时，密钥值忘记加引号，导致 JSON 格式错误，codex-fast-proxy 无法读取。
**解决**: 用正确 JSON 格式写入：

```json
{
  "version": 1,
  "providers": {
    "codex_api": {
      "api_key": "sk-d1f66d..."
    }
  }
}
```

### 6. 端口冲突导致启动失败
**问题**: 重启本地代理时端口 8787 被残留进程占用（CLOSE_WAIT 状态），而 lsof 又查不到，导致启动失败。
**解决**: 清理遗留的 pid/lock/sock 文件后重启：

```bash
rm -f ~/.codex/codex-fast-proxy-state/*.pid 
rm -f ~/.codex/codex-fast-proxy-state/*.lock
rm -f ~/.codex/codex-fast-proxy-state/*.sock
```

### 7. 沙箱隔离限制
**问题**: Claude 的 bash 命令运行在隔离 Linux 沙箱中，无法直接操作 Mac 终端。需要用户在 Mac 终端手动执行命令。
**解决**: 将常用操作封装为 `/Applications/` 下的 Shell 脚本，用户一键运行。

## 主要问题总结

| 类型 | 根本原因 | 影响 |
|------|---------|------|
| 网络 | 上游服务不可用 | 本地代理启动后无法转发请求 |
| 证书 | Python 3.12 + macOS 证书链问题 | HTTPS 连接失败 |
| 密钥 | 密钥属于 CC Switch 而非 OpenAI | 认证失败 401 |
| 配置 | 认证方式、格式错误 | 本地代理无法正常工作 |
| 环境 | 沙箱无法执行用户 Mac 命令 | 部分操作需用户手动配合 |

## 对插件优化的建议

1. **SSL 处理**：增加 `ssl._create_unverified_context()` 作为兜底，避免 certifi 证书链断裂导致连不上
2. **上游健康检查**：启动时自动检测上游是否可用，不可用则降级/报错提示
3. **provider-auth.json 校验**：写入时自动校验 JSON 格式合法性
4. **端口冲突处理**：启动前检查 pid 文件残留，自动清理后再绑定
5. **一键脚本**：提供 `switch-upstream.sh` 类的辅助脚本，降低用户操作门槛
