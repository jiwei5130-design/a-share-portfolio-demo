"""Streamlit Community Cloud 入口 — A股智能交易决策系统 V1.0 Portfolio Demo。

SCC 适配（仅部署层，展示层与只读 API 业务逻辑零改动）：
  1) 首次启动时把分块的数据集 SQLite 逐字节还原（SHA256 校验，不一致立即失败）
  2) 选择只读 API 端口并启动（sys.executable 子进程，仅监听 127.0.0.1）：
     · 优先使用显式配置端口（SCC_API_PORT），否则用配置的 API 地址端口，否则 8000
     · 候选端口若已有**健康**的本项目 API（/health 200）→ 直接复用，不重复启动
     · 候选端口被占用但不健康（残留进程）→ 最小化清理（仅限本项目自己的 uvicorn 进程，
       Linux 下按 /proc 精确匹配；其他平台自动跳过）→ 仍不可用则换下一个可用端口
     · 实际端口同步到 STRATEGY1_API_URL（保证页面不会请求错误端口）
     · 子进程 stdout/stderr 写入 data/api_subprocess.log；等待 /health 200
       （单次请求 20 秒超时，总上限 300 秒；子进程提前退出立即失败并输出日志尾部）
  3) 运行既有展示层（demo/portfolio_demo/streamlit_app.py）

任何一步失败都会显示明确错误并停止启动（绝不静默降级、绝不用错误数据库继续）。
"""

from __future__ import annotations

import hashlib
import json
import locale
import os
import runpy
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import streamlit as st

try:  # Windows 控制台编码兜底（Linux/Cloud 为 UTF-8，无影响）
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
API_LOG_PATH = DATA_DIR / "api_subprocess.log"
DEFAULT_API_PORT = 8000
PORT_SCAN_LIMIT = 100  # 8000..8099
HEALTH_TIMEOUT_SECONDS = 300
HEALTH_REQUEST_TIMEOUT_SECONDS = 20
STALE_TERMINATE_WAIT_SECONDS = 5
LOG_TAIL_LINES = 40
API_MODULE_HINT = "src.web_api.app"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _restore_database() -> str:
    manifest_path = DATA_DIR / "MANIFEST.json"
    if not manifest_path.exists():
        raise RuntimeError(f"缺少数据清单文件：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = DATA_DIR / manifest["database"]
    expected = manifest["original_sha256"]

    if target.exists() and _sha256(target) == expected:
        return "数据集已就绪（SHA256 校验通过）"

    if target.exists():
        target.unlink()

    temporary = target.with_name(target.name + ".restoring")
    with temporary.open("wb") as out:
        for item in manifest["chunks"]:
            chunk = DATA_DIR / item["name"]
            if not chunk.exists():
                raise RuntimeError(f"缺少数据分块：{chunk.name}")
            if chunk.stat().st_size != item["size"]:
                raise RuntimeError(f"数据分块大小不符：{chunk.name}")
            with chunk.open("rb") as source:
                shutil.copyfileobj(source, out, 8 * 1024 * 1024)

    actual = _sha256(temporary)
    if actual != expected:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            "数据集还原校验失败（SHA256 不一致），已中止启动："
            f"期望 {expected[:16]}…，实际 {actual[:16]}…"
        )
    os.replace(temporary, target)
    return f"数据集还原完成并校验通过（{target.stat().st_size:,} 字节）"


def _api_is_healthy(base_url: str) -> bool:
    """只有 /health 真正返回 HTTP 200 才算成功（不做任何伪造）。"""
    try:
        with urllib.request.urlopen(
            f"{base_url}/health", timeout=HEALTH_REQUEST_TIMEOUT_SECONDS
        ) as response:
            return response.status == 200
    except Exception:
        return False


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _configured_api_url() -> str | None:
    value = None
    try:
        value = st.secrets.get("STRATEGY1_API_URL")
    except Exception:
        value = None
    if not value:
        value = os.environ.get("STRATEGY1_API_URL")
    return str(value).rstrip("/") if value else None


def _port_from_url(url: str | None) -> int | None:
    if not url:
        return None
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.hostname in ("127.0.0.1", "localhost") and parsed.port:
            return int(parsed.port)
    except Exception:
        return None
    return None


def _stale_api_pids() -> list[int]:
    """仅 Linux：找出属于当前用户、且是我们本项目 uvicorn 的残留进程。"""
    if not Path("/proc").exists():
        return []
    pids: list[int] = []
    uid = os.getuid() if hasattr(os, "getuid") else None
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if uid is not None and entry.stat().st_uid != uid:
                continue
            cmdline = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode(
                "utf-8", "replace"
            )
        except OSError:
            continue
        if "uvicorn" in cmdline and API_MODULE_HINT in cmdline:
            pids.append(int(entry.name))
    return pids


def _terminate_stale_api() -> bool:
    """最小化清理：只终止本项目自己的残留 uvicorn（非本项目进程一律不动）。"""
    pids = _stale_api_pids()
    if not pids:
        return False
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            continue
    deadline = time.time() + STALE_TERMINATE_WAIT_SECONDS
    while time.time() < deadline:
        if not _stale_api_pids():
            return True
        time.sleep(0.5)
    return not _stale_api_pids()


def _select_api_port() -> tuple[int, str]:
    """返回 (端口, 说明)。健康则复用；被占用且不健康则最小清理，再不行换端口。"""
    explicit = os.getenv("SCC_API_PORT")
    preferred = (
        int(explicit)
        if explicit and explicit.isdigit()
        else _port_from_url(_configured_api_url()) or DEFAULT_API_PORT
    )
    candidates = [preferred] + [
        port
        for port in range(DEFAULT_API_PORT, DEFAULT_API_PORT + PORT_SCAN_LIMIT)
        if port != preferred
    ]
    for index, port in enumerate(candidates):
        base_url = f"http://127.0.0.1:{port}"
        if _api_is_healthy(base_url):
            return port, f"复用已运行的只读 API（{base_url}）"
        if _port_is_free(port):
            return port, f"使用端口 {port}"
        if index == 0 and _terminate_stale_api() and _port_is_free(port):
            return port, f"清理残留 API 后使用原端口 {port}"
    raise RuntimeError(
        f"在 {DEFAULT_API_PORT}–{DEFAULT_API_PORT + PORT_SCAN_LIMIT - 1} 范围内未找到可用端口"
    )


def _log_tail() -> str:
    if not API_LOG_PATH.exists():
        return "(API 子进程日志尚未生成)"
    try:
        raw = API_LOG_PATH.read_bytes()
    except OSError as exc:
        return f"(无法读取 API 子进程日志：{exc})"
    for encoding in ("utf-8", locale.getpreferredencoding(False)):
        try:
            lines = raw.decode(encoding).splitlines()
            return "\n".join(lines[-LOG_TAIL_LINES:]) or "(API 子进程日志为空)"
        except (UnicodeDecodeError, LookupError):
            continue
    return "\n".join(raw.decode("utf-8", "replace").splitlines()[-LOG_TAIL_LINES:])


def _report_failure(reason: str) -> None:
    tail = _log_tail()
    print(f"[scc_demo] {reason}", flush=True)
    print(f"[scc_demo] API 子进程日志尾部（{LOG_TAIL_LINES} 行）：\n{tail}", flush=True)


def _apply_api_url(base_url: str) -> None:
    """让展示层使用实际启动成功的端口（环境变量；secrets 只读时给出明确告警）。"""
    os.environ["STRATEGY1_API_URL"] = base_url
    configured = _configured_api_url()
    if configured and configured != base_url:
        print(
            "[scc_demo] 注意：Streamlit secrets 中的 STRATEGY1_API_URL="
            f"{configured} 与本次实际端口 {base_url} 不一致；"
            "请把该 secret 删除或改为实际端口，否则页面会请求错误端口。",
            flush=True,
        )


def _start_api() -> str:
    port, note = _select_api_port()
    base_url = f"http://127.0.0.1:{port}"
    if note.startswith("复用"):
        _apply_api_url(base_url)
        return note

    environment = dict(os.environ)
    environment["PYTHONUNBUFFERED"] = "1"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = API_LOG_PATH.open("a", encoding="utf-8")
    log_handle.write(
        f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} starting API on {base_url} ---\n"
    )
    log_handle.flush()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            API_MODULE_HINT + ":app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(ROOT),
        env=environment,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    deadline = time.time() + HEALTH_TIMEOUT_SECONDS
    while time.time() < deadline:
        if _api_is_healthy(base_url):
            _apply_api_url(base_url)
            return f"只读 API 就绪（{base_url}；{note}）"
        if process.poll() is not None:
            _report_failure(f"API 子进程已退出（exit code {process.returncode}）")
            raise RuntimeError(
                f"只读 API 子进程启动失败（exit code {process.returncode}）。"
                f"API 日志尾部：\n{_log_tail()}"
            )
        time.sleep(2)
    _report_failure(f"API 在 {HEALTH_TIMEOUT_SECONDS} 秒内未通过 /health 检查")
    raise RuntimeError(
        f"只读 API 在 {HEALTH_TIMEOUT_SECONDS} 秒内未通过 /health 检查（{base_url}）。"
        f"API 日志尾部：\n{_log_tail()}"
    )


@st.cache_resource(show_spinner=False)
def _bootstrap() -> str:
    steps = [_restore_database()]
    steps.append(_start_api())
    return "；".join(steps)


try:
    _bootstrap()
except Exception as exc:  # 部署初始化失败必须显式失败
    st.error(f"部署初始化失败：{exc}")
    st.stop()

runpy.run_path(str(ROOT / "demo" / "portfolio_demo" / "streamlit_app.py"), run_name="__main__")
