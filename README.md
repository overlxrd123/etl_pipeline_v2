# 电商数据工程 ETL 管道

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Prefect](https://img.shields.io/badge/Prefect-3.8-purple)
![dbt](https://img.shields.io/badge/dbt--core-latest-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-latest-red)

**全栈数据工程管道** — 从 API 数据采集到业务智能看板，端到端自动化。

## 项目架构

```
Open-Meteo天气API ──┐
Binance/CoinGecko ──┼── Prefect 调度器 ──► SQLite 数据仓库 ──► dbt 转换建模 ──► Streamlit 交互看板
电商交易模拟器 ─────┘       │                      │                    │                   │
                    [数据采集]               [数据加载]           [数据转换]           [数据服务]
```

## 星型模型（7张表）

| 表名 | 类型 | 数据量 | 说明 |
|------|------|--------|------|
| `dim_date` | 维度表 | 3,653 | 10年日历（2023-2032），含财年、周末、节假日 |
| `dim_city` | 维度表 | 5 | 美国主要城市，含经纬度、人口 |
| `dim_product` | 维度表 | 50 | 电子产品，5大品类（手机/笔记本/耳机/平板/手表） |
| `dim_customer` | 维度表 | 500 | 客户信息，含忠诚度等级（Bronze~Platinum） |
| `dim_weather` | 维度表 | 1,825 | 5 城市 × 365 天真实天气（温度/降水/风速/天气类型） |
| `dim_crypto` | 维度表 | 732 | BTC/ETH 每日价格（Binance 历史 K 线 + 实时兜底） |
| `fact_orders` | 事实表 | 147,386 | 订单明细（每行一个订单，关联所有维度） |

## 技术栈

| 层级 | 工具 | 用途 |
|------|------|------|
| 调度编排 | **Prefect 3.x** | 任务调度、失败重试、运行监控 |
| 数据库 | **SQLite + SQLAlchemy** | 本地数据仓库，支持环境变量指定 SQLite 文件 |
| 数据转换 | **dbt-core + dbt-sqlite** | staging → intermediate → marts 三层建模 |
| 数据采集 | **Requests + Pandas** | API 客户端 + 电商数据模拟器 |
| 可视化 | **Streamlit + Plotly** | 6 页交互式分析看板 |
| 测试 | **pytest + dbt tests** | 31 项 dbt 数据测试 + 32 个 pytest 用例 |

## 项目结构

```
etl_pipeline_v2/
├── config/                 # 集中配置、数据库连接工厂
├── src/
│   ├── extract/            # Open-Meteo / CoinGecko API + 交易生成器
│   ├── load/               # staging 维度表加载 + 事实表加载
│   └── warehouse/          # 7 表 ORM 模型 + DDL 参考
├── orchestration/
│   └── flows/              # Prefect 调度（天气/加密/订单/全管道）
├── dbt_project/
│   └── models/
│       ├── staging/        # 5 个模型（1:1 对应源表）
│       ├── intermediate/   # 4 个模型（关联 + 聚合）
│       └── marts/          # 7 个模型（业务就绪）
├── dashboard/
│   ├── app.py              # 主入口
│   └── pages/              # 6 个交互页面
├── seed_data.py            # 初始化 dim_date + dim_city
├── rebuild_demo_data.py    # 一键重建：历史天气/币价 → 驱动订单
├── export_pbi_demo.py      # 导出 Power BI CSV（派生数据，不入库）
└── requirements.txt
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库 + 种子数据
python seed_data.py

# 3. 一键重建演示数据（推荐）
#    抓取订单窗口内的真实天气/币价，并用它们驱动订单生成
python rebuild_demo_data.py
#    需要 Power BI 的 CSV 时，顺便导出：
python rebuild_demo_data.py --pbi

# 4. dbt 建模 + 按依赖执行数据测试
cd dbt_project
dbt build --profiles-dir .
cd ..

# 5. 启动交互看板
streamlit run dashboard/app.py
```

> `--profiles-dir .` 不能省略：项目自带的 dbt profile 在 `dbt_project/profiles.yml`，
> 默认位置 `~/.dbt/profiles.yml` 并不存在。

也可以单独运行各步骤：

```bash
python -m src.extract.transaction_generator   # 用数仓中的天气/币价生成订单 CSV
python -m src.load.staging_to_warehouse       # 加载 CSV 到事实表
python -m orchestration.flows.run_full_pipeline  # Prefect 完整管道
# 已有历史驱动数据时：跳过网络采集，仍执行质量门禁和 dbt
python -m orchestration.flows.run_full_pipeline --offline
# 仅调试入库，不刷新分析结果（必须显式指定）
python -m orchestration.flows.run_full_pipeline --offline --skip-dbt
```

完整管道会初始化缺少的表与种子维度，按 `SIM_START` / `SIM_END` 获取历史天气和币价；已有订单 CSV 时复用原文件，避免重跑时生成另一份随机订单。当前仍为手动触发的 Prefect Flow，没有自动创建定时部署。

## 可靠性与重跑

- **订单幂等加载**：新生成的订单带稳定的 `source_order_id`；上游真实订单也应提供稳定且唯一的该字段。`etl_order_keys` 保存来源标识与事实表订单的映射，订单、映射和批次进度在同一事务中提交。失败后使用同一来源文件重跑，只补齐未提交部分；返回值为本次新增行数。
- **旧数仓兼容**：首次加载会为旧订单建立映射，不修改其业务字段或订单 ID。旧 CSV 缺少来源 ID 时，使用标准化内容指纹与重复序号识别同一文件的重跑，同时保留完全相同的多笔订单。此兼容模式不能代替真实业务 ID：新批次及更正数据应提供稳定来源 ID，同 ID 不同内容会报错，不会静默覆盖。
- **输入校验与审计**：金额计算、数量、折扣、支付信息、时间与日期、维度关联均在订单插入前检查。`etl_load_runs` 记录运行状态、新增/跳过行数和异常类型；健康页展示最近的加载批次。
- **驱动数据更新**：天气按城市与日期更新，币价按币种与 UTC 时间戳去重更新。天气部分城市失败、响应不完整、币价缺少币种或日期时会抛出异常，Prefect 可据此重试。
- **发布门禁**：订单及维度非空、金额和时间合法、无孤儿记录、订单窗口内天气与 BTC/ETH 覆盖完整后，才执行 `dbt build`。不合格输入不会触发新一轮 marts 构建。
- **统一指标**：销售查询使用 `mart_orders` 订单粒度快照，RFM 直接读取 `mart_customer_segments`，最近购买天数以数据最新日期为基准。停用客户和产品的历史订单仍被保留。dbt 额外核对清洗层、订单服务层和日汇总的订单数与营收。
- **显式全量重建**：`rebuild_demo_data.py` 仍是清表重建工具，常规管道不清表。重建前使用 SQLite Backup API 备份，并校验历史驱动覆盖与必要文件；中断后可从备份恢复。多阶段全量重建不等同于一个跨步骤的数据库事务。

首次使用这版代码时，先执行一次 `dbt build --profiles-dir .`，生成新增的 `mart_orders`。订单身份与加载审计表会在下次加载时自动创建。测试命令为 `python -m pytest tests -q`；单元故障测试使用内存数据库，已有数仓的 RFM 集成检查可通过 `ETL_TEST_WAREHOUSE` 指向副本。

当前 dbt 侧共 **16 个模型**（5 staging + 4 intermediate + 7 marts）、**31 项数据测试**；pytest 侧 **32 个用例**，覆盖重复加载、断点续跑、来源 ID 冲突、输入校验与质量门禁。`dbt build` 会按依赖顺序执行模型与测试。

## 模拟效应与数据口径

真实电商订单不公开，因此订单为模拟数据；但**天气和币价来自真实 API**
（Open-Meteo 归档 API + Binance 日 K 线，并带 CoinGecko/Gate.io 兜底）。

为了让"影响分析"可验证，订单生成器读取真实天气/币价并应用显式设定的效应
（参数见 `config/settings.py`）：

| 驱动因素 | 条件 | 效应 |
|---|---|---|
| 天气 | 日降水 ≥ 5mm | 当天该城市订单量 ×0.90 |
| 天气 | 雷暴 / 降雪 | 订单量 ×0.80 |
| 天气 | 最高温 ≥ 35°C | 订单量 ×0.95 |
| 币价 | BTC 日涨幅 > 2% | 加密支付占比 40% |
| 币价 | BTC 日跌幅 > 2% | 加密支付占比 20% |
| 币价 | 其他 | 加密支付占比 30% |

分析口径：

- 天气按 `城市 + 日期` 关联订单，先算城市日订单量，再计算**订单指数**：
  当天该城市订单份额 ÷ 该城市全年平均份额 × 100。
  100 表示平常水平；同一天的季节、周末、节假日波动会被抵消。
- 币价按日关联，比较 BTC 上涨/下跌/震荡三组的加密支付占比
- 结论用于**验证数据管道能否还原设定效应**，不是对现实世界的因果推断
- 分析只使用**有订单的日期**。单独抓取新的天气/币价只会追加维度数据，
  不会改变已有分析；要让新数据参与分析，需要重建订单或调整
  `SIM_START` / `SIM_END` 后重建。看板「管道健康」页会显示两者的覆盖率。

### 验证结果（当前数据：2025-08-11 ~ 2026-08-10）

天气（订单指数，已剔除日期/季节波动）：

| 天气 | 城市天数 | 订单指数 | 相对无雨还原出的乘数 | 设定值 |
|---|---:|---:|---:|---:|
| 无雨 | 1,322 | 102.3 | 1.00（基准） | — |
| 高温 ≥35°C | 191 | 97.8 | 0.96 | 0.95 |
| 雨天 ≥5mm | 228 | 93.8 | 0.92 | 0.90 |
| 雷暴/降雪 | 84 | 85.9 | 0.84 | 0.80 |

> 当前窗口内没有雷暴天气，因此“雷暴/降雪”样本全部为降雪。
> 订单量按整数取整、样本量有限，还原值会有约 ±0.04 的偏差；
> 方向和幅度与设定值一致，说明天气 → 订单 → dbt → 看板整条链路是通的。

币价（加密支付订单占比）：

| BTC 行情 | 天数 | 平均加密支付占比 | 设定值 |
|---|---:|---:|---:|
| 上涨 >2% | 43 | 39.8% | 40% |
| 震荡（±2% 内） | 263 | 29.9% | 30% |
| 下跌 <-2% | 58 | 20.5% | 20% |

## 核心功能

- **2 类真实数据源**（Open-Meteo 天气 + Binance 币价，CoinGecko/Gate.io 自动兜底）— 无需 API Key，开箱即用
- **历史数据对齐** — 用订单同期的 365 天真实天气/币价驱动模拟订单
- **已知效应沙盒** — 效应参数显式设定，分析结果可被验证和还原
- **真实电商数据模拟** — 季节性波动（黑五/圣诞/Prime Day）、周末效应、多种支付方式
- **完整 dbt 管道** — staging → intermediate → marts 三层共 16 个模型、31 项数据测试
- **Prefect 自动化调度** — 失败自动重试、结构化日志、任务依赖管理
- **RFM 客户分层** — 核心客户 / 忠诚客户 / 潜力客户 / 需关注 / 流失风险 / 已流失（分位数打分，适配任意数据规模）
- **天气影响分析** — 按城市日平均比较雨天/高温/雷暴降雪/无雨，并用订单指数剔除季节波动
- **币价影响分析** — BTC 涨跌与加密支付占比的关联
- **管道健康监控** — 数据质量检查、各表行数、最新采集时间

## 数据库支持范围

当前端到端验证针对 SQLite。可以通过 `DATABASE_URL=sqlite:///绝对路径/warehouse.db` 指定另一份数仓；Prefect 的 dbt 阶段会将相同路径传给 profile，也可单独设置 `ETL_SQLITE_PATH` 运行 dbt。迁移 PostgreSQL 还需要适配 dbt adapter、日期函数、类型与备份脚本，并重新验证，不能只修改连接字符串。

## 与旧项目对比

| 维度 | 旧 etl_pipeline | 本项目 |
|------|----------------|--------|
| 代码量 | 1 个文件，205 行 | ~50 个文件，模块化 |
| 数据源 | 1 个爬虫 | 2 个 API + 数据生成器 |
| 数据库 | 1 张平表 | 7 表星型模型 |
| 数据转换 | Pandas 内联处理 | dbt 三层建模 |
| 调度方式 | 手动运行 | Prefect 自动化 |
| 可视化 | 静态 HTML | Streamlit 交互看板 |
| 测试 | 无 | pytest + dbt tests |
