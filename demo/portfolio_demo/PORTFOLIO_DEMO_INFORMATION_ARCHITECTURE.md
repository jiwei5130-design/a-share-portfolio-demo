# Portfolio Demo 信息架构（Information Architecture）

项目名称：**A股智能交易决策系统 V1.0｜Portfolio Demo**  
文档性质：**信息架构设计（只设计，不开发）**  
上游基准：`RESEARCH_BACKEND_GOLDEN_MASTER_2026-09-14`（只读）

---

## 1. 页面层级

```text
L0  首页｜Dashboard                      /                     （产品定位 + 今日概览 + 入口）
L1  市场环境                             /market               （现在是什么市场）
L1  板块环境                             /sectors              （关注在哪里）
L1  策略中心                             /strategies           （用哪类策略）
L1  ├── Strategy1｜隔日趋势              /strategies/strategy1 （正式验证线）
L1  └── Strategy2｜关键价格地标研究      /strategies/strategy2 （实验研究线）
L1  今日信号                             /signals              （今天发现了什么）
L2  个股详情                             /stock/{code}         （为什么是它 / 风险在哪）
```

* 导航栏可见 5 项：**首页 / 市场环境 / 板块环境 / 策略中心 / 今日信号**；
* `个股详情` 为二级页面（从信号/策略页进入），不出现在主导航；
* `Strategy1 / Strategy2` 为策略中心内的二级标签页，不单独占用导航。

## 2. 导航结构

```text
A股智能交易决策系统 V1.0
│
├── 首页
├── 市场环境
├── 板块环境
├── 策略中心
│     ├── Strategy1｜隔日趋势
│     └── Strategy2｜关键价格地标研究
├── 今日信号
└── （隐藏）个股详情 /stock/{code}
```

全局元素：

| 元素 | 内容 |
|---|---|
| 顶栏 | 产品名 + 数据日期 + 数据范围徽章（`PARTIAL_UNIVERSE` / `真实数据`） |
| 底栏 | “研究与决策辅助｜不是荐股或自动交易系统｜不承诺收益” |
| 状态徽章 | `真实数据` / `研究性` / `PARTIALLY_SUPPORTED` / `NOT_AVAILABLE` / `STATISTICAL SYNTHETIC CURVE — NOT PORTFOLIO RISK` |

## 3. 页面之间的关系（数据流与跳转）

```text
                 ┌──────────────┐
                 │  ① 首页      │
                 └──────┬───────┘
        ┌───────────────┼────────────────┬──────────────┐
        ↓               ↓                ↓              ↓
 ② 市场环境        ③ 板块环境        ④ 策略中心      ⑤ 今日信号
        │               │                │              │
        │  环境→策略    │  行业上下文     │  策略→信号   │
        └───────────────┴────────────────┘              │
                                                         ↓
                                                  ⑥ 个股详情
                                                         │
                                                         └─→ 回到 ④ 策略中心（历史验证）

④ 策略中心 ──→ Strategy2 研究（研究→回测→否定→优化 案例）
```

关键关系：

| 关系 | 说明 |
|---|---|
| 首页 → 全部 | 首页每个卡片均可下钻（成交额→市场环境；策略状态→策略中心；候选→个股详情） |
| 市场环境 → 策略中心 | “环境 → 策略影响”：市场环境状态作为策略研究背景 |
| 板块环境 → 今日信号 | 行业上下文（当前股票—行业映射 `NOT_AVAILABLE`，仅到行业层） |
| 策略中心 → 今日信号 | 按策略筛选信号（当前只有 Strategy1 产生信号） |
| 今日信号 → 个股详情 | 每条候选可进入详情 |
| 个股详情 → 策略中心 | 查看对应策略的完整历史验证与边界 |

## 4. 用户路径

### 4.1 主路径（面试 5 分钟，默认路径）

```text
首页（产品是什么）
  → 市场环境（现在是什么市场）
  → 策略中心（用哪类策略；Strategy1 正式线）
  → 今日信号（链路 + 今日候选）
  → 个股详情（可解释依据 + 风险）
  → 策略中心 / Strategy2 研究（持续验证与迭代）
```

### 4.2 研究路径

```text
首页 → 策略中心 → Strategy2 研究 → 研究证据（支持/负结果）→ 为什么未进入正式线 → 下一步
```

### 4.3 风控路径

```text
首页（风险状态）→ 市场环境（环境风险）→ 今日信号 → 个股详情（最大风险 / Exit Engine / T+1 约束）
```

### 4.4 边界说明路径（诚实性展示）

```text
任意页面 → 数据范围徽章 → 市场环境页“数据边界”区 → 板块环境页“股票—行业映射 NOT_AVAILABLE”
```

## 5. 页面 ↔ 数据源映射（只读 API）

| 页面 | API / 产物 | 关键字段 |
|---|---|---|
| 首页 | `/api/v1/overview`、`/api/v1/market/overview`、`/api/v1/market/regime`、`/api/v1/sectors/overview`、`/api/v1/signals`、`/api/v1/backtest/performance`、`/api/v1/strategies/strategy1/portfolio-risk` | `current_market_date`、`today_candidate_count`、`breadth.latest.amount`、`regime.state_label`、`rotation_state`、`total_trades`、`win_rate`、`portfolios.A.max_drawdown` |
| 市场环境 | `/api/v1/market/overview`、`/api/v1/market/regime`、`/api/v1/market/regime/history` | `breadth.latest.amount`、`breadth.history[].amount`、`coverage`、`ma_breadth`、`regime.regime_score`、`volume_context` |
| 板块环境 | `/api/v1/sectors/overview`、`/api/v1/sectors/{code}` | `return_1d/5d/20d`、`relative_hs300_5d/20d`、`rank_5d/20d`、`rotation_state` |
| 策略中心｜Strategy1 | `/api/v1/backtest/performance`、`/api/v1/strategies/strategy1/regime-performance`、`/api/v1/strategies/strategy1/portfolio-risk` | `total_trades`、`win_rate`、`avg_return`、`profit_loss_ratio`、`max_drawdown`、`portfolios.A/B/C`、`episode`、`by_regime` |
| 策略中心｜Strategy2 | `/api/v1/strategies/strategy2/landmark-research`、`/api/v1/strategies/strategy2/landmark-evidence` | `research_gate`、`statuses`、`v1_0.sections`、`landmark.trade_level`、`landmark.stability`、`landmark.portfolio`、`synthetic` |
| 今日信号 | `/api/v1/signals?date=`、`/api/v1/overview` | `total`、`items[code,name,buy_price,ma5_distance,pressure_distance,entry_reason,risk_warning]`、`score_definition` |
| 个股详情 | `/api/v1/stocks/{code}`、`/api/v1/signals`、`/api/v1/backtest/performance` | `market_data_summary`、`raw_history`、`latest_signal`、`trades`、`performance`、`exit_reason_statistics` |

**统一口径要求**：市场级成交额一律使用 `amount` 字段 + 统一派生（与研发后台 `turnover_metrics` 同口径）；不得一个页面用 `volume`、另一个页面用 `amount`。

## 6. 状态与降级设计（诚实性）

| 状态 | 展示方式 | 出现位置（示例） |
|---|---|---|
| `PARTIAL_UNIVERSE` | 橙色徽章 + 覆盖率数字 + “仅覆盖已加载样本” | 全局顶栏、市场环境 |
| `NOT_AVAILABLE` | 灰色徽章 + 原因说明（不补造数据） | 个股行业归属、空信号日 |
| `PARTIALLY_SUPPORTED` | 橙色徽章 + 一句解释 | Strategy2 Research Gate |
| `NOT READY` | 灰色徽章 | Strategy2 生产状态 |
| `STATISTICAL SYNTHETIC CURVE — NOT PORTFOLIO RISK` | 橙色标记 + 口径说明 | Strategy1 风险、Strategy2 风险 |
| API 不可用 | 错误提示 + “请先启动 API”指引；不展示缓存假数据 | 全局 |
| 数据不足 | “数据不足”文案（不使用 0 代替） | 量能/宽度/覆盖率 |

## 7. 组件体系（设计层，复用现有能力）

| 组件 | 用途 | 实现建议 |
|---|---|---|
| 状态卡（Metric Card） | 单个 KPI + 口径说明 | `st.metric(border=True)` + `caption` |
| 事实→状态→影响卡 | 市场环境的“所以呢” | `st.container(border=True)` 三段式 |
| 徽章行 | 数据状态/研究状态 | `:green-badge[]` / `:orange-badge[]` / `:gray-badge[]` |
| 条件清单 | 个股信号解释（✓/待确认） | Markdown 列表 |
| 小型趋势图 | 成交额/宽度/Regime 轨迹 | `st.line_chart` |
| 证据表 | 策略历史结果 | `st.dataframe(hide_index=True)` |
| 下钻入口 | 卡片→页面 | `st.page_link`（Demo 内页）/ 文字入口 |

## 8. 技术方案与隔离（设计层）

| 项目 | 方案 |
|---|---|
| 目录 | `portfolio_demo/`（独立，不修改 `src/web_dashboard/`） |
| 入口 | `portfolio_demo/streamlit_app.py`（未来创建，待授权） |
| 数据 | 只读调用现有 API（`http://127.0.0.1:8000`），复用 `api_client` 模式（Demo 内自建只读客户端，不修改正式 `api_client`） |
| 派生逻辑 | 复用既有口径（如 `turnover_metrics` 的算法在 Demo 内等价实现，或引用 `src/web_dashboard/presentation.py` 的只读函数） |
| 页面数 | 6 个核心页面 + 1 个详情页 |
| 端口 | 建议 `8503`（与研发后台 `8502`、旧 Demo 区分） |
| 验收 | Demo 自身 smoke test + 确认研发后台 acceptance/Protection Gate 不受影响 |

## 9. 与研发后台的边界（页面级）

| 允许 | 禁止 |
|---|---|
| 只读调用正式 API | 修改 API 字段/路由/语义 |
| 复用已冻结的研究结论与数字 | 重算策略、重跑回测、改 Research Gate |
| 重新组织信息架构与视觉 | 修改正式 Web 页面逻辑 |
| 新增 Demo 专属展示组件 | 新增指标/评分/排序/expected return |
| 诚实展示数据缺口 | 为 Demo 制造假数据或隐藏负结果 |

## 10. 页面原型优先级（供下一阶段授权后排期）

| 优先级 | 页面 | 理由 |
|---|---|---|
| P0 | 首页、策略中心（Strategy1 + Strategy2） | 产品定位与核心叙事 |
| P0 | 今日信号、个股详情 | 决策链路闭环 |
| P1 | 市场环境 | 环境→策略影响 |
| P1 | 板块环境 | 行业上下文（含数据边界展示） |

---

**当前状态**：本文件为设计交付物，**未创建任何页面、未修改任何代码**。等待人工审阅与开发授权。
