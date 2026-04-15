# apply-job

基于 LangGraph 构建的职位抓取与筛选 pipeline，自动从 LinkedIn 抓取职位、规则过滤、LLM 评分，并支持人工审核 pending 职位。

## 流程

```
resolve_url → fetch_jobs → filter_jobs → review_pending → write_csv
```

1. **resolve_url** — 将 ISO 国家代码映射为 LinkedIn 搜索 URL
2. **fetch_jobs** — 调用 Apify actor 抓取最多 300 条职位
3. **filter_jobs** — 规则过滤（去重 / 语言检测 / 关键词排除）+ LLM 评分分类
4. **review_pending** — Human-in-the-loop：人工审核 LLM 无法判断的职位
5. **write_csv** — 将结果写入 `suitable.csv` 和 `unsuitable.csv`

## 项目结构

```
apply-job/
├── src/apply_job/
│   ├── config.py           # 全局配置（LLM 模型、API key）
│   ├── state.py            # AgentState：贯穿全图的共享状态
│   ├── graph.py            # 图构建入口，注册于 langgraph.json
│   ├── nodes/              # 各节点实现
│   │   ├── resolve_search_url.py
│   │   ├── fetch_jobs_from_linkedin.py
│   │   ├── filter_jobs.py
│   │   ├── review_pending_jobs.py
│   │   └── write_jobs_into_csv.py
│   ├── tools/              # LangChain 工具
│   │   ├── fetch_jobs_from_linkedin.py  # Apify API 调用
│   │   ├── filter_jobs.py               # 规则过滤
│   │   └── csv_ops.py                   # CSV 读写
│   └── prompts/
│       └── evaluate.py     # LLM 评分 prompt
├── tests/                  # 单元测试
├── data/                   # 运行时数据（gitignore）
│   ├── suitable.csv        # 匹配职位
│   └── unsuitable.csv      # 不匹配职位（下次运行用于去重）
├── doc/Apply Job.md        # 详细设计文档
├── langgraph.json          # LangGraph API 注册配置
└── pyproject.toml
```

## 快速开始

**1. 安装依赖**

```bash
uv sync
```

**2. 配置环境变量**

复制 `.env.example` 并填入密钥：

```bash
cp .env.example .env
```

```env
APIFY_API_TOKEN=your-apify-token
DASHSCOPE_V2_API_KEY=your-dashscope-key
LLM_MODEL=qwen3.6-plus        # 可选，默认 qwen3.6-plus
```

**3. 启动 LangGraph 开发服务器**

```bash
uvx --from "langgraph-cli[inmem]" langgraph dev
```

然后在 LangGraph Studio 中传入以下 state 触发运行：

```json
{
  "country": "DE",
  "data_dir": "data",
  "resume_path": "data/resume.pdf"
}
```

支持的国家：`DE` `NL` `ES` `AT` `CH` `BE` `FR` `PT` `GB` `SE` `DK` `PL`

## 运行测试

```bash
uv run pytest
```
