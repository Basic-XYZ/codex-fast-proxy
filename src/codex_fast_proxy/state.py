from __future__ import annotations

from typing import Any


SCHEMA_VERSION = 1


def collect_status(codex_home: str | None, provider: str | None = None) -> dict[str, Any]:
    from . import manager

    paths = manager.paths_for(codex_home)
    settings_data = manager.read_json(paths.settings_path)
    settings = manager.settings_from_dict(settings_data) if settings_data else None
    pid, running, health, healthy, pending_restart, runtime_matches = manager.proxy_runtime_state(paths, settings)
    config = manager.load_toml_config(paths.config_path)
    selected_provider = provider or (settings.provider if settings else manager.active_provider_name(config))
    config_base_url = manager.provider_base_url(config, selected_provider) if selected_provider else None
    hook_status = manager.fast_proxy_hook_trust_status(paths)
    login = manager.detect_login_mode(paths.codex_home)
    auth = manager.upstream_auth_status(paths, settings)
    config_matches = bool(settings and config_base_url == settings.base_url)
    needs_restart = bool(pending_restart or (healthy and not runtime_matches))
    behavior = manager.fast_behavior(settings, login)
    effective_policy = manager.effective_service_tier_policy(settings, login) if settings else None
    login_report = (
        manager.chatgpt_login_report(paths, settings, login, auth)
        if settings
        else {"provider_auth_preparation": None, "chatgpt_login_hint": None, "next_user_action": None}
    )
    diagnosis = manager.status_diagnosis(
        settings,
        running=running,
        healthy=healthy,
        pending_restart=pending_restart,
        config_matches=config_matches,
        runtime_matches=runtime_matches,
        needs_restart=needs_restart,
        startup_hook_ready=bool(hook_status["ready"]),
        login=login,
        auth=auth,
        behavior=behavior,
    )

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "status": "running" if running else "stopped",
        "pid": pid,
        "healthy": healthy,
        "runtime_id": manager.RUNTIME_ID,
        "runtime": manager.runtime_status(paths, health),
        "runtime_matches": runtime_matches,
        "needs_restart": needs_restart,
        "pending_restart": pending_restart,
        "diagnosis": diagnosis,
        "provider": selected_provider,
        "base_url": settings.base_url if settings else None,
        "upstream_base": settings.upstream_base if settings else None,
        "service_tier_policy": settings.service_tier_policy if settings else None,
        "service_tier_effective_policy": effective_policy,
        "fast_behavior": behavior,
        "login_mode": login.login_mode,
        "chatgpt_auth": login.chatgpt_auth,
        "api_key_auth": login.api_key_auth,
        "upstream_auth": auth["upstream_auth"],
        "upstream_api_key_env": auth["upstream_api_key_env"],
        "upstream_api_key_file": auth["upstream_api_key_file"],
        "upstream_api_key_ref": auth["upstream_api_key_ref"],
        "upstream_api_key_available": auth["upstream_api_key_available"],
        "upstream_api_key_source": auth["upstream_api_key_source"],
        "upstream_api_key_persistent": auth["upstream_api_key_persistent"],
        "chatgpt_login_compatible": bool(auth["upstream_api_key_persistent"]) if login.chatgpt_auth else None,
        **login_report,
        "config_base_url": config_base_url,
        "config_matches": config_matches,
        "startup_hook": hook_status["ready"],
        "startup_hook_trust": hook_status,
        "port_available": manager.is_port_available(settings.host, settings.port) if settings else None,
        "health": health,
        "log": str(paths.log_path),
        "stdout": str(paths.stdout_path),
        "stderr": str(paths.stderr_path),
    }
    return {**snapshot, "user_state": user_state(snapshot)}


def user_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    diagnosis = snapshot.get("diagnosis") if isinstance(snapshot.get("diagnosis"), dict) else {}
    code = diagnosis.get("code")
    provider_ready = bool(snapshot.get("provider") and snapshot.get("config_base_url"))

    if snapshot.get("config_matches") and snapshot.get("healthy") and not snapshot.get("needs_restart"):
        view = ("working", "运行正常", "Codex 已准备好继续使用当前模型服务。", None, None)
    elif snapshot.get("config_matches") and snapshot.get("needs_restart"):
        view = (
            "restart_required",
            "已准备好，请重启 Codex",
            "设置已保存。重启 Codex 后即可使用；如果之后切换到 ChatGPT 登录，也已完成准备。",
            "refresh",
            "我已重启，重新检查",
        )
    elif provider_ready and code in {"not_enabled", "config_not_proxy"}:
        view = (
            "ready_to_enable",
            "准备启用",
            "点击启用后，会自动准备当前模型服务路径，并提前准备 ChatGPT 账户登录兼容性。",
            "enable",
            "启用",
        )
    else:
        view = (
            "needs_attention",
            "需要处理",
            "当前环境还不能直接完成启用。请打开诊断，或让 Codex 根据诊断结果修复。",
            "diagnostics",
            "打开诊断",
        )
    code, title, message, primary_action, primary_label = view
    return {
        "code": code,
        "title": title,
        "message": message,
        "primary_action": primary_action,
        "primary_label": primary_label,
    }
