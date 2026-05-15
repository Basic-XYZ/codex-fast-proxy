from __future__ import annotations

import contextlib
import io
import json
from typing import Any


def run_first_run_enable(codex_home: str | None, provider: str | None = None) -> dict[str, Any]:
    from . import manager

    paths = manager.paths_for(codex_home)
    config = manager.load_toml_config(paths.config_path)
    selected_provider = manager.choose_provider(config, provider)
    if manager.provider_auth_secret(paths, selected_provider):
        prepare_result = {
            "status": "already_prepared",
            "provider": selected_provider,
            "target_auth": "provider_auth_file",
            "settings_changed": False,
        }
    else:
        prepare_result = manager.prepare_chatgpt_login(manager_args(
            manager,
            "prepare-chatgpt-login",
            codex_home,
            "--provider",
            selected_provider,
            "--apply",
        ))

    install_args = manager_args(
        manager,
        "install",
        codex_home,
        "--provider",
        selected_provider,
        "--use-provider-auth-file",
        "--start",
    )
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exit_code = manager.command_install(install_args)
    install_result = json.loads(output.getvalue()) if output.getvalue().strip() else {"status": "ok"}
    if not isinstance(install_result, dict):
        raise ValueError("Manager command returned an invalid JSON object.")
    if exit_code != 0:
        detail = install_result.get("message") or install_result.get("error") or f"exit code {exit_code}"
        raise ValueError(str(detail))

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


def manager_args(manager: Any, command: str, codex_home: str | None, *args: str) -> Any:
    argv = [command]
    if codex_home:
        argv.extend(["--codex-home", codex_home])
    argv.extend(args)
    return manager.build_parser().parse_args(argv)
