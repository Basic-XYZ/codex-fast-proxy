from __future__ import annotations

import argparse
import contextlib
import io
import json
from typing import Any


def run_first_run_enable(codex_home: str | None, provider: str | None = None) -> dict[str, Any]:
    from . import manager

    paths = manager.paths_for(codex_home)
    config = manager.load_toml_config(paths.config_path)
    selected_provider = manager.choose_provider(config, provider)
    prepare_result = prepare_provider_auth(manager, codex_home, selected_provider)

    install_args = argparse.Namespace(
        codex_home=codex_home,
        provider=selected_provider,
        activate_provider=False,
        host=manager.DEFAULT_HOST,
        port=manager.DEFAULT_PORT,
        proxy_base=manager.DEFAULT_PROXY_BASE,
        upstream_base=None,
        service_tier=manager.DEFAULT_SERVICE_TIER,
        service_tier_policy=manager.DEFAULT_SERVICE_TIER_POLICY,
        upstream_api_key_env=None,
        use_provider_auth_file=True,
        verify=True,
        verify_timeout=60.0,
        start=True,
        prepare_only=False,
        verbose_proxy=False,
    )
    install_result = run_json_command(manager.command_install, install_args, allowed_exit_codes={0})
    return {
        "status": "enabled",
        "provider": selected_provider,
        "prepare_chatgpt_login": prepare_result,
        "install": install_result,
        "restart_required": True,
        "user_state": {
            "code": "restart_required",
            "title": "已准备好，请重启 Codex",
            "message": "设置已保存。请重启 Codex，重启后即可继续使用当前模型服务。",
        },
        "next_user_action": "请重启 Codex，然后回到此页面确认运行状态。",
    }


def prepare_provider_auth(manager: Any, codex_home: str | None, provider: str) -> dict[str, Any]:
    paths = manager.paths_for(codex_home)
    if manager.provider_auth_secret(paths, provider):
        return {
            "status": "already_prepared",
            "provider": provider,
            "target_auth": "provider_auth_file",
            "settings_changed": False,
        }

    args = argparse.Namespace(
        codex_home=codex_home,
        provider=provider,
        source_auth_key=None,
        target_env=None,
        apply=True,
    )
    return manager.prepare_chatgpt_login(args)


def run_json_command(command: Any, args: argparse.Namespace, *, allowed_exit_codes: set[int]) -> dict[str, Any]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exit_code = command(args)
    value = json.loads(output.getvalue()) if output.getvalue().strip() else {"status": "ok"}
    if not isinstance(value, dict):
        raise ValueError("Manager command returned an invalid JSON object.")
    if exit_code not in allowed_exit_codes:
        detail = value.get("message") or value.get("error") or f"exit code {exit_code}"
        raise ValueError(str(detail))
    return value
