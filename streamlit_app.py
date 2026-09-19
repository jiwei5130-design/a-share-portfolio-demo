"""Streamlit Community Cloud 入口 — A股智能交易决策系统 V1.0 Portfolio Demo。

SCC 适配（仅部署层，展示层与只读 API 业务逻辑零改动）：
  1) 首次启动时把分块的数据集 SQLite 逐字节还原（SHA256 校验，不一致立即失败）
  2) 用当前 Python 解释器（sys.executable）在后台启动只读 API（127.0.0.1，默认 8000）
     · 子进程 stdout/stderr 写入 data/api_subprocess.log（不再丢弃，便于云端诊断）
     · 等待 /health 返回 HTTP 200（单次请求 20 秒超时，总上限 300 秒）
     · 子进程提前退出或超时：把日志尾部显示到页面并打印到 Cloud Logs
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
API_PORT = int(os.getenv("SCC_API_PORT", "8000"))
API_BASE_URL = f"http://127.0.0.1:{API_PORT}"
HEALTH_TIMEOUT_SECONDS = 300
HEALTH_REQUEST_TIMEOUT_SECONDS = 20
LOG_TAIL_LINES = 40


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


def _api_is_healthy() -> bool:
    """只有 /health 真正返回 HTTP 200 才算成功（不做任何伪造）。"""
    try:
        with urllib.request.urlopen(
            f"{API_BASE_URL}/health", timeout=HEALTH_REQUEST_TIMEOUT_SECONDS
        ) as response:
            return response.status == 200
    except Exception:
        return False


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


def _start_api() -> str:
    if _api_is_healthy():
        return "只读 API 已在运行"
    environment = dict(os.environ)
    environment["PYTHONUNBUFFERED"] = "1"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = API_LOG_PATH.open("a", encoding="utf-8")
    log_handle.write(
        f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} starting API on {API_BASE_URL} ---\n"
    )
    log_handle.flush()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.web_api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(API_PORT),
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
        if _api_is_healthy():
            return f"只读 API 就绪（{API_BASE_URL}）"
        if process.poll() is not None:
            _report_failure(f"API 子进程已退出（exit code {process.returncode}）")
            raise RuntimeError(
                f"只读 API 子进程启动失败（exit code {process.returncode}）。"
                f"API 日志尾部：\n{_log_tail()}"
            )
        time.sleep(2)
    _report_failure(f"API 在 {HEALTH_TIMEOUT_SECONDS} 秒内未通过 /health 检查")
    raise RuntimeError(
        f"只读 API 在 {HEALTH_TIMEOUT_SECONDS} 秒内未通过 /health 检查（{API_BASE_URL}）。"
        f"API 日志尾部：\n{_log_tail()}"
    )


@st.cache_resource(show_spinner=False)
def _bootstrap() -> str:
    steps = [_restore_database()]
    os.environ.setdefault("STRATEGY1_API_URL", API_BASE_URL)
    steps.append(_start_api())
    return "；".join(steps)


try:
    _bootstrap()
except Exception as exc:  # 部署初始化失败必须显式失败
    st.error(f"部署初始化失败：{exc}")
    st.stop()

runpy.run_path(str(ROOT / "demo" / "portfolio_demo" / "streamlit_app.py"), run_name="__main__")
