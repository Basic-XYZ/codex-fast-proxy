from __future__ import annotations

import contextlib
import io
import json
from typing import Any


def state(code: str, title: str, message: str, primary_action: str = "refresh", primary_label: str = "重新检查") -> dict[str, str]:
    return {
        "code": code,
        "title": title,
        "message": message,
        "primary_action": primary_action,
        "primary_label": primary_label,
    }


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
    install_result = run_manager_json(manager, manager.command_install, install_args)

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


def run_update(codex_home: str | None, provider: str | None = None) -> dict[str, Any]:
    from . import manager

    result = manager.update_installation(codex_home, provider)
    if result.get("status") == "blocked":
        result["user_state"] = state(
            "update_blocked",
            "更新被暂停",
            str(result.get("next_user_action") or "当前安装状态不能安全更新，请打开诊断。"),
            "diagnostics",
            "打开诊断",
        )
        return result

    final_status = result.get("final_status") if isinstance(result.get("final_status"), dict) else {}
    if final_status.get("needs_restart"):
        result["user_state"] = state(
            "restart_required",
            "更新完成，请重启 Codex",
            "更新已完成，但当前 Codex 进程需要重启后才会使用新的代理状态。",
        )
    else:
        result["user_state"] = state(
            "updated",
            "更新完成",
            "已刷新到最新版本，当前状态可以继续使用。",
        )
    return result


def run_configure_upstream(
    codex_home: str | None,
    upstream_base: str | None,
    api_key: str | None,
) -> dict[str, Any]:
    from . import manager

    result = manager.configure_upstream(codex_home, upstream_base, api_key)
    if result.get("restart_required"):
        result["user_state"] = state(
            "restart_required",
            "配置已保存，请重启 Codex",
            "新的模型服务配置已验证并保存。重启 Codex 后会应用到当前使用路径。",
        )
    else:
        result["user_state"] = state(
            "configured",
            "配置已保存",
            "新的模型服务配置已验证并保存，当前状态可以继续使用。",
        )
    return result


def run_uninstall(codex_home: str | None, confirm_chatgpt_direct_uninstall: bool = False) -> dict[str, Any]:
    from . import manager

    defer_stop, _provider = manager.enabled_installation(manager.paths_for(codex_home), None)
    args = ["--defer-stop"] if defer_stop else []
    if confirm_chatgpt_direct_uninstall:
        args.append("--confirm-chatgpt-direct-uninstall")
    result = run_manager_json(
        manager,
        manager.command_uninstall,
        manager_args(manager, "uninstall", codex_home, *args),
        allowed_exit_codes={0, 4},
    )
    if result.get("status") == "confirmation_required":
        result["user_state"] = state(
            "confirmation_required",
            "需要确认",
            str(result.get("message") or "当前是 ChatGPT 登录模式，直接恢复到第三方模型服务可能导致请求失败。"),
            "diagnostics",
            "打开诊断",
        )
    elif result.get("stop_result", {}).get("status") == "deferred":
        result["user_state"] = state(
            "uninstalled_deferred",
            "已恢复，请重启 Codex",
            "Codex 配置已恢复到原模型服务。为避免打断当前会话，代理会暂时保留；重启 Codex 后可再次打开控制面板完成清理。",
        )
    else:
        result["user_state"] = state(
            "uninstalled",
            "已清理",
            "代理状态和启动项已清理。重启 Codex 或新开 CLI 后，Codex 会回到原模型服务路径。",
        )
    return result


def run_manager_json(
    manager: Any,
    command: Any,
    args: Any,
    *,
    allowed_exit_codes: set[int] | None = None,
) -> dict[str, Any]:
    allowed = allowed_exit_codes or {0}
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exit_code = command(args)
    text = output.getvalue().strip()
    result = json.loads(text) if text else {"status": "ok"}
    if not isinstance(result, dict):
        raise ValueError("Manager command returned an invalid JSON object.")
    if exit_code not in allowed:
        detail = result.get("message") or result.get("error") or f"exit code {exit_code}"
        raise ValueError(str(detail))
    return result


def manager_args(manager: Any, command: str, codex_home: str | None, *args: str) -> Any:
    argv = [command]
    if codex_home:
        argv.extend(["--codex-home", codex_home])
    argv.extend(args)
    return manager.build_parser().parse_args(argv)
