"""Streamlit Community Cloud 入口 — A股智能交易决策系统 V1.0 Portfolio Demo。

SCC 适配（仅部署层，展示层与只读 API 业务逻辑零改动）：
  1) 首次启动时把分块的数据集 SQLite 逐字节还原（SHA256 校验，不一致立即失败）
  2) 用当前 Python 解释器（sys.executable）在后台启动只读 API（127.0.0.1，默认 8000）
  3) 等待 /health 返回 200 后运行既有展示层（demo/portfolio_demo/streamlit_app.py）

任何一步失败都会显示明确错误并停止启动（绝不静默降级、绝不用错误数据库继续）。
"""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
API_PORT = int(os.getenv("SCC_API_PORT", "8000"))
API_BASE_URL = f"http://127.0.0.1:{API_PORT}"
HEALTH_TIMEOUT_SECONDS = 300


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
        return f"数据集已就绪（SHA256 校验通过）"

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
    try:
        with urllib.request.urlopen(f"{API_BASE_URL}/health", timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


def _start_api() -> str:
    if _api_is_healthy():
        return "只读 API 已在运行"
    environment = dict(os.environ)
    environment["PYTHONUNBUFFERED"] = "1"
    subprocess.Popen(
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + HEALTH_TIMEOUT_SECONDS
    while time.time() < deadline:
        if _api_is_healthy():
            return f"只读 API 就绪（{API_BASE_URL}）"
        time.sleep(2)
    raise RuntimeError(
        f"只读 API 在 {HEALTH_TIMEOUT_SECONDS} 秒内未通过 /health 检查（{API_BASE_URL}）；"
        "请查看 Cloud 日志。不会以错误状态继续启动。"
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
