# Portfolio Demo｜A股智能交易决策系统 V1.0

> 本目录是 **Portfolio Demo（求职作品集 / 面试演示版）** 的设计与开发目录。
> 与研发研究后台**完全隔离**：只读消费其稳定数据与 API，不修改任何研究结论。

---

## 1. Demo 定位

**A股智能交易决策系统 V1.0｜Portfolio Demo**

* 面向**真实用户场景**的产品展示版：求职作品集、面试演示、产品设计与落地能力展示；
* 目标：让第一次看到项目的招聘方在 **3–5 分钟内**理解：解决什么问题 → 如何理解市场 → 如何选择策略 → 如何形成个股决策依据 → 如何展示风险 → 如何持续研究优化策略；
* **不是**研发后台的复制版，**不是**研究报告的搬运，**不是**荐股 / 自动交易 / 收益承诺。

## 2. 与 Research Backend 的关系

```text
研发研究后台（已冻结：RESEARCH_BACKEND_GOLDEN_MASTER_2026-09-14）
        │  已验证数据 / 策略结果 / 研究结论（只读）
        ↓
Portfolio Demo（本目录）
        │
        ↓
面向用户的产品体验
```

* 冻结基准：`RESEARCH_BACKEND_GOLDEN_MASTER_2026-09-14`（见根目录冻结说明与 `snapshots/` 哈希清单）；
* Demo **只读调用**现有正式 API（`src/web_api/`）与预计算产物；
* Demo 与研发后台的隔离原则（同冻结文档 §9）：
  1. Demo 在独立目录开发，不修改冻结版本；
  2. 只读消费，不重算策略、不修改数据、不新建指标；
  3. 如需新展示，复用现有 API 字段与口径（如 `amount` / `turnover_metrics`）；
  4. Demo 的 UI 改动不回流修改正式 Web 页面逻辑；
  5. 任何对冻结区的修改必须专项授权 + 重新验收 + 发布新冻结版本号。

## 3. 数据来源

| 来源 | 说明 |
|---|---|
| 正式 API | `http://127.0.0.1:8000`（`src/web_api/`，16 个只读路由） |
| Strategy1 产物 | `data/strategy1_mvp_reports/`（Golden Master：30,122 信号 / 6,049 笔） |
| Strategy2 产物 | `data/strategy2_range_trading_reports/`（v1.0 研究归档）+ `data/strategy2_landmark_research/`（L 线 gate + evidence） |
| 市场/板块 | P4 Market Intelligence、Market Regime V1.0、P6 Sector Intelligence（只读） |

**禁止**：为 Demo 制造假数据；为视觉效果隐藏负结果；修改研究结果 / 策略参数 / 历史回测 / Research Gate。

## 4. 当前 Demo 状态

| 阶段 | 状态 |
|---|---|
| 产品结构设计（Product Spec） | ✅ 已完成（`PORTFOLIO_DEMO_PRODUCT_SPEC.md`） |
| 信息架构设计（IA） | ✅ 已完成（`PORTFOLIO_DEMO_INFORMATION_ARCHITECTURE.md`） |
| **Step 1：基础结构 + 入口 + 全局 Layout** | ✅ **已完成**（`streamlit_app.py` / `api_client.py` / `presentation.py` / 4 个页面骨架） |
| **Step 2：首页数据与产品体验** | ✅ **已完成**（`app_pages/home.py`：Hero + 市场概览 + 环境/板块 + 重点信号 + 研究可信度 + 数据边界） |
| **Step 3：策略中心** | ✅ **已完成**（导航已注册） |
| **Step 4：今日信号** | ✅ **已完成**（`app_pages/signals.py`：决策链路 + 动态真实候选卡 + 信号解释 + T+1/T+2 约束 + 风险边界；空结果与 API 异常分支已实现） |
| **Step 5：个股详情** | ✅ **已完成**（`app_pages/stock_detail.py`：基本状态 + 信号条件清单 + 计划价/T+1 + 所属行业 NOT_AVAILABLE + 风险与 Exit Engine + 历史验证 + 数据边界；无 code / code 不存在 / 无历史交易分支已实现） |
| **Step 6：市场环境 / 板块环境** | ✅ **已完成**（导航已注册为 5 项 + 隐藏详情页） |
| **市场环境 V2.1 产品化改版** | ✅ **已完成**（`app_pages/market.py`：核心判断（偏弱 + 评分）/ 市场环境评分（含 −100~+100 范围与 7 大核心指数构成）/ 市场涨跌与强弱 / 市场指数 / 市场环境走势；已移除研发口径与数据边界说明） |
| **板块环境 V2.1 产品化改版** | ✅ **已完成**（`app_pages/sectors.py`：一句描述 + 真实交易日切换器（250 日）+ 活跃板块 + 折叠「查看完整 31 行业数据」（已删轮动状态列与全部接口/质量说明）；已移除行业上下文、行业与策略关系、数据边界） |
| **策略中心 V2.1 产品化改版** | ✅ **已完成**（`app_pages/strategies.py`：正式名称「隔日超短趋势策略」「支撑位策略」；历史验证表现（信号/成交/胜率/平均净收益/盈亏比/组合模拟最大回撤）/ 资金管理敏感性 A·B·C / 策略逻辑；已移除 Research Gate、研究线状态、冻结规则、数据边界、策略对比与全部技术字段） |
| **公网展示层安全清理 + 手机端适配（Phase 1）** | ✅ **已完成**（shell 页脚移除 PARTIAL_UNIVERSE；home/signals/stock_detail 移除研发字段、内部接口路径、策略内部参数、NOT_AVAILABLE、原始字段；全部横排指标行改为 `st.columns` 以支持窄屏纵向堆叠；真实 390px（CDP 模拟）实测 6 页无横向溢出。详见 `PORTFOLIO_DEMO_PUBLIC_DEPLOY_PLAN.md`） |
| 公网部署（单 VPS：Caddy → Demo → 内部 API） | ⏳ **实施准备完成**（`PORTFOLIO_DEMO_PUBLIC_DEPLOY_PLAN.md`；未部署、未购买 VPS、API 不开放公网端口） |
| **Step 7：全站视觉与产品体验 Polish** | ✅ **已完成**（首页信息层级、市场页三层结构、板块页折叠全表、策略中心层级与“为什么未上线”突出、信号卡精简、个股详情阅读顺序与返回入口） |
| 下一步：最终验收 → 截图 / 作品集 → 简历 → 投递 | ⏳ 等待人工验收 |

**启动方式（Demo，端口 8503）**：

```powershell
cd /d D:\隔日战法
D:\miniconda\python.exe -m streamlit run portfolio_demo\streamlit_app.py --server.port 8503
```

> 研发后台保持 8502；Demo 只读调用 8000 端口的正式 API。当前页面骨架**不展示任何数据**，等待 Step 3–6 实现。

## 5. 禁止修改的研究对象（Demo 开发期同样适用）

* Strategy1 核心逻辑 / 参数 / Golden Master / MVP Runner / 适配器；
* Strategy2 核心逻辑 / v1.0 参数 / Phase 4A 协议 / L 冻结定义 / Research Gate 结论；
* StrategyEngine、Exit Engine；
* Market Regime V1.0 核心计算与阈值；P4 Market Intelligence；P6 Sector Intelligence；
* 数据库（`data/market_data.db`、`stock_data.db`）、原始回测结果；
* 正式 API 字段语义与正式 Web 主架构；
* `DQ-VOLUME-UNIT-MIX-001`（volume 单位混合问题，保持 OPEN）。

## 6. 演示主线（5 分钟）

```text
① 首页        “这是我做的一套 A 股智能交易决策产品。”
② 市场环境    “系统首先判断当前市场处于什么环境。”
③ 策略中心    “不同市场环境下，并不是所有策略都适用。”
④ 今日信号    “系统进一步把市场、策略和个股条件结合起来。”
⑤ 个股详情    “最终给出的不是一句买/卖，而是可解释的决策依据。”
⑥ Strategy2   “策略本身也会被持续验证：研究 → 回测 → 否定 → 优化。”
```
