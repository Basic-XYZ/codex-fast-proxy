from __future__ import annotations

import html
import json
from typing import Any


CONTROL_TOKEN_HEADER = "X-Codex-Fast-Proxy-Token"

def render_page(snapshot: dict[str, Any], token: str) -> str:
    user_state = snapshot.get("user_state", {})
    title = str(user_state.get("title") or "需要处理")
    message = str(user_state.get("message") or "请打开诊断，或让 Codex 根据诊断结果修复。")
    primary_action = user_state.get("primary_action")
    primary_label = str(user_state.get("primary_label") or "刷新")
    button = (
        f'<button id="primary" data-action="{html.escape(str(primary_action))}">{html.escape(primary_label)}</button>'
        if primary_action in {"enable", "refresh"}
        else '<button id="primary" data-action="diagnostics">打开诊断</button>'
    )
    maintenance = ""
    labels: dict[str, str] = {}
    if snapshot.get("base_url"):
        upstream_value = html.escape(str(snapshot.get("upstream_base") or ""), quote=True)
        labels = {
            "update": "更新",
            "uninstall": "停用并恢复",
            "confirmUninstall": "我知道可能导致模型请求失败，仍要停用",
            "saveConfig": "保存并验证",
        }
        maintenance = f"""
        <button id="update" class="secondary" data-action="update">更新</button>
        <button id="uninstall" class="warn" data-action="uninstall">停用并恢复</button>
      </div>
      <div id="dangerZone" class="danger-zone" style="display:none">
        <p>仍要继续停用只适合你已经理解风险的情况。继续后，当前 ChatGPT 登录可能无法直接使用第三方模型服务。</p>
        <button id="confirmUninstall" class="warn" data-action="confirm-uninstall">我知道可能导致模型请求失败，仍要停用</button>
      </div>
      <h2>模型服务</h2>
      <form id="configForm">
        <label>服务地址
          <input id="upstreamBase" autocomplete="off" value="{upstream_value}" placeholder="https://api.example.com/v1">
        </label>
        <label>API Key
          <input id="apiKey" type="password" autocomplete="off" placeholder="留空则不修改已保存的 key">
        </label>
        <button id="saveConfig" type="submit">保存并验证</button>
      </form>
"""
    else:
        maintenance = "</div>"
    snapshot_json = html.escape(json.dumps(snapshot, ensure_ascii=False))
    token_json = json.dumps(token)
    labels_json = json.dumps(labels, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Codex 控制面板</title>
  <style>
    :root {{ color-scheme: light; font-family: "Segoe UI", system-ui, sans-serif; }}
    body {{ margin: 0; background: #f6f7f9; color: #17202a; }}
    main {{ max-width: 820px; margin: 0 auto; padding: 40px 20px; }}
    .panel {{ background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 24px; }}
    h1, .state {{ margin: 0 0 16px; }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 18px; margin: 28px 0 12px; }}
    .state {{ font-size: 32px; font-weight: 650; }}
    .message, .note {{ line-height: 1.6; color: #344054; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
    button {{ border: 0; border-radius: 8px; background: #1769aa; color: white; cursor: pointer; font-size: 15px; font-weight: 600; padding: 11px 18px; }}
    button.secondary {{ background: #344054; }}
    button.warn {{ background: #9a3412; }}
    button:disabled {{ cursor: wait; opacity: .65; }}
    .danger-zone {{ border-top: 1px solid #e5e8ef; margin-top: 18px; padding-top: 18px; }}
    .danger-zone p {{ color: #7c2d12; line-height: 1.6; margin: 0 0 12px; }}
    form {{ display: grid; gap: 10px; margin-top: 10px; }}
    label {{ display: grid; gap: 6px; color: #344054; font-size: 14px; }}
    input {{ border: 1px solid #cbd5e1; border-radius: 8px; font-size: 15px; padding: 10px 12px; }}
    details {{ margin-top: 24px; border-top: 1px solid #e5e8ef; padding-top: 18px; }}
    pre {{ background: #111827; border-radius: 8px; color: #e5e7eb; overflow: auto; padding: 16px; }}
  </style>
</head>
<body>
  <main>
    <h1>Codex 控制面板</h1>
    <section class="panel">
      <p id="state" class="state">{html.escape(title)}</p>
      <p id="message" class="message">{html.escape(message)}</p>
      <div class="actions">
        {button}
        {maintenance}
      <p class="note">如果你是在 Codex 内置浏览器看到此页面，重启 Codex 前请用外部浏览器打开此页面，否则重启后页面会关闭。</p>
      <details>
        <summary>诊断</summary>
        <pre id="diagnostics">{snapshot_json}</pre>
      </details>
    </section>
  </main>
  <script>
    const token = {token_json};
    const headerName = {json.dumps(CONTROL_TOKEN_HEADER)};
    const $ = (id) => document.getElementById(id);
    const labels = {labels_json};
    function resetControls(userState) {{
      Object.entries(labels).forEach(([id, label]) => {{
        const item = $(id);
        if (item) {{
          item.disabled = false;
          item.textContent = label;
        }}
      }});
      $('primary').disabled = false;
      const confirmUninstall = $('confirmUninstall');
      const dangerZone = $('dangerZone');
      if (dangerZone) dangerZone.style.display = userState.code === 'confirmation_required' ? 'block' : 'none';
      const uninstall = $('uninstall');
      if (uninstall) uninstall.style.display = userState.code === 'confirmation_required' ? 'none' : 'inline-block';
    }}
    function resetForm(snapshot) {{
      const upstreamBase = $('upstreamBase');
      if (upstreamBase) upstreamBase.value = snapshot.upstream_base || '';
      const apiKey = $('apiKey');
      if (apiKey) apiKey.value = '';
    }}
    function render(snapshot) {{
      const userState = snapshot.user_state || {{}};
      $('state').textContent = userState.title || '需要处理';
      $('message').textContent = userState.message || '请打开诊断，或让 Codex 根据诊断结果修复。';
      $('diagnostics').textContent = JSON.stringify(snapshot, null, 2);
      const button = $('primary');
      button.dataset.action = userState.primary_action || 'diagnostics';
      button.textContent = userState.primary_label || '打开诊断';
      resetControls(userState);
      resetForm(snapshot);
    }}
    async function requestAction(action, body) {{
      const response = await fetch('/api/actions/' + action, {{
        method: 'POST',
        headers: {{ [headerName]: token, 'Content-Type': 'application/json' }},
        body: body ? JSON.stringify(body) : undefined
      }});
      const data = await response.json();
      if (data.status !== 'ok') {{
        if (data.snapshot) render(data.snapshot);
        throw new Error(data.error || '操作没有完成。');
      }}
      render(data.snapshot);
      if (data.action && data.action.control_ui && data.action.control_ui.url) {{
        window.setTimeout(() => {{
          window.location.href = data.action.control_ui.url;
        }}, 500);
      }}
    }}
    async function runButton(button, action, body) {{
      button.disabled = true;
      const oldText = button.textContent;
      button.textContent = action === 'enable' ? '正在准备环境...' : '处理中...';
      try {{
        await requestAction(action, body);
      }} catch (error) {{
        $('state').textContent = '需要处理';
        $('message').textContent = (error && error.message) ? error.message : String(error);
        button.disabled = false;
        button.textContent = oldText;
      }}
    }}
    $('primary').addEventListener('click', async (event) => {{
      const action = event.currentTarget.dataset.action;
      if (action === 'enable') await runButton(event.currentTarget, 'enable');
      else if (action === 'refresh') window.location.reload();
      else document.querySelector('details').open = true;
    }});
    if ($('update')) $('update').addEventListener('click', (event) => runButton(event.currentTarget, 'update'));
    if ($('uninstall')) $('uninstall').addEventListener('click', (event) => runButton(event.currentTarget, 'uninstall'));
    if ($('confirmUninstall')) $('confirmUninstall').addEventListener('click', (event) => runButton(event.currentTarget, 'uninstall', {{ confirm: true }}));
    if ($('configForm')) $('configForm').addEventListener('submit', async (event) => {{
      event.preventDefault();
      await runButton($('saveConfig'), 'configure-upstream', {{
        upstream_base: $('upstreamBase').value.trim() || null,
        api_key: $('apiKey').value.trim() || null
      }});
      $('apiKey').value = '';
    }});
  </script>
</body>
</html>"""
