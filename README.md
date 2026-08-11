# 电商数据工程 ETL 管道

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Prefect](https://img.shields.io/badge/Prefect-3.8-purple)
![dbt](https://img.shields.io/badge/dbt--core-latest-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-latest-red)

**全栈数据工程管道** — 从 API 数据采集到业务智能看板，端到端自动化。

## 项目架构

```
Open-Meteo天气API ──┐
CoinGecko加密API ───┼── Prefect 调度器 ──► SQLite 数据仓库 ──► dbt 转换建模 ──► Streamlit 交互看板
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
| `dim_weather` | 维度表 | — | 每日天气（温度/降水/风速/天气类型） |
| `dim_crypto` | 维度表 | — | BTC/ETH 实时美元价格 |
| `fact_orders` | 事实表 | 155,000+ | 订单明细（每行一个订单，关联所有维度） |

## 技术栈

| 层级 | 工具 | 用途 |
|------|------|------|
| 调度编排 | **Prefect 3.x** | 任务调度、失败重试、运行监控 |
| 数据库 | **SQLite + SQLAlchemy** | 数据仓库（改环境变量即可切换 PostgreSQL） |
| 数据转换 | **dbt-core + dbt-sqlite** | staging → intermediate → marts 三层建模 |
| 数据采集 | **Requests + Pandas** | API 客户端 + 电商数据模拟器 |
| 可视化 | **Streamlit + Plotly** | 5 页交互式分析看板 |
| 测试 | **pytest + dbt tests** | 数据质量验证 |

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
│       ├── intermediate/   # 3 个模型（关联 + 聚合）
│       └── marts/          # 4 个模型（业务就绪）
├── dashboard/
│   ├── app.py              # 主入口
│   └── pages/              # 5 个交互页面
├── seed_data.py            # 初始化 dim_date + dim_city
└── requirements.txt
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库 + 种子数据
python seed_data.py

# 3. 生成电商数据并加载到数仓
python -m src.extract.transaction_generator
python -m src.load.staging_to_warehouse

# 4.（可选）采集真实天气数据
python -m src.extract.weather_api

# 5. 运行完整 ETL 管道（Prefect 编排）
python -m orchestration.flows.run_full_pipeline

# 6. 启动交互看板
streamlit run dashboard/app.py
```

## dbt 数据转换（可选 — 需安装 dbt-sqlite）

```bash
cd dbt_project
dbt debug                      # 验证数据库连接
dbt run                        # 构建所有模型
dbt test                       # 运行数据质量测试
dbt docs generate && dbt docs serve   # 生成并查看文档
```

## 核心功能

- **2 个真实 API**（Open-Meteo 天气 + CoinGecko 加密价格）— 无需 API Key，开箱即用
- **真实电商数据模拟** — 季节性波动（黑五/圣诞/Prime Day）、周末效应、多种支付方式
- **完整 dbt 管道** — staging → intermediate → marts 三层，附带数据测试
- **Prefect 自动化调度** — 失败自动重试、结构化日志、任务依赖管理
- **RFM 客户分层** — 核心客户 / 忠诚客户 / 潜力客户 / 流失风险 / 已流失
- **天气影响分析** — 不同天气条件的销售额对比、订单分布
- **管道健康监控** — 数据质量检查、各表行数、最新采集时间

## 切换 PostgreSQL

```bash
# 设置环境变量
export DATABASE_URL=postgresql://user:pass@localhost:5432/warehouse

# 安装驱动
pip install psycopg2-binary

# 修改 dbt profile 切换为 postgres adapter
```

SQLAlchemy 抽象了数据库层，代码无需任何修改。

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
