# A股智能交易决策系统 V1.0 · Portfolio Demo（Streamlit Community Cloud 部署副本）

本目录是**独立可上传 GitHub 的 SCC 部署副本**：展示层与只读 API 均为已验证副本，未修改任何业务逻辑。

## 结构

```text
scc_demo/
├── streamlit_app.py        SCC 入口：还原数据集（分块 + SHA256 校验）→ 启动只读 API → 运行展示层
├── requirements.txt        streamlit / pandas / altair / starlette / uvicorn（均为实际运行依赖）
├── .streamlit/config.toml  主题
├── src/                    只读 API 依赖闭包（含"数据集 CSV 缺失"适配）
├── data/                   Online Dataset V1（9 个小文件 + market_data.db 的 5 个分块 + MANIFEST.json）
├── demo/portfolio_demo/    展示层（6 页，含 120 日窗口适配）
└── README.md
```

## 数据分块（GitHub 100 MiB 单文件限制）

- `data/market_data.db`（379,887,616 字节）被切分为 **5 个分块**（每个 ≈72.46 MiB，<100 MiB）；
- `data/MANIFEST.json` 记录每块大小/SHA256 与**整库原始 SHA256**；
- 启动时按序拼接 → **SHA256 必须与原始值完全一致**（`03fb7b21…`），否则**立即失败并报错**；
- 分块是逐字节切分，**未压缩、未修改数据库内容**；拼接结果与 Online Dataset 完全一致。

## 在 Streamlit Community Cloud 部署

1. 把本目录内容推送到一个 **GitHub 仓库**（仓库根目录 = 本目录）；
2. 打开 <https://share.streamlit.io> → **Create app** → 选择该仓库；
3. **Main file path** 填 `streamlit_app.py`；
4. Python 版本选 **3.12**（或 3.11）；
5. **Secrets**（可选，推荐）：`STRATEGY1_API_URL = "http://127.0.0.1:8000"`
   （不填也可以：入口会在启动时自动设置为 `http://127.0.0.1:<SCC_API_PORT 默认 8000>`）；
6. 点击 **Deploy**。首次启动会：还原数据集（数秒）→ 启动只读 API → 等待 `/health` 200 → 打开页面。

## 运行机制与边界

- 只读 API 由入口以 `sys.executable` 在后台启动，仅监听 `127.0.0.1`（不对外）；
- 数据从 `data/` 读取（容器本地，只读使用）；重启后重新还原（仓库分块仍在）；
- **不含** `strategy1_demo_dataset.csv`（1.13 GB）：线上只使用预计算信号缓存；API 副本已适配"缺失该 CSV 时跳过 mtime 检查，且禁止错误重建"；
- 展示层页面、API 业务逻辑、数据内容均未修改；不新增功能、不改变 UI。

## 本地自检（无需 Docker）

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
# 若本机 8000 端口被占用，可指定：SCC_API_PORT=8051
```
