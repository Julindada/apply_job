# Apply Job

## 一、技术栈

- **语言 / 框架**：Python 3.13 + LangGraph
- **LLM**：Alibaba Dashscope（模型 `qwen3.6-plus`，通过 OpenAI 兼容接口调用）
- **职位抓取**：Apify LinkedIn Jobs Scraper actor
- **项目入口**：`src/apply_job/graph.py`，LangGraph 图对象 `graph`
- **运行方式**：LangGraph API（Studio / Cloud），通过 `langgraph.json` 注册

---

## 二、整体流程

```
resolve_url → fetch_jobs → filter_jobs → review_pending → write_csv
```

每个步骤对应 `src/apply_job/nodes/` 下的一个 LangGraph 节点，共享同一个 `AgentState`。

### 必填输入（调用图时传入 state）

| 字段 | 说明 |
|------|------|
| `country` | ISO 国家代码，如 `"DE"`，用于生成 LinkedIn 搜索 URL |
| `data_dir` | 数据目录，如 `"data"`，所有 CSV 均写入此目录 |
| `resume_path` | 简历 PDF 路径，用于 LLM 评分 |

### 可选输入

| 字段 | 说明 |
|------|------|
| `excluded_files` | 覆盖默认的去重文件列表（默认为 `[data_dir/finished_jobs.csv, data_dir/unsuitable.csv]`） |

---

## 三、节点详解

### 1. `resolve_url` — 生成 LinkedIn 搜索 URL

**文件**：`src/apply_job/nodes/resolve_search_url.py`

将 ISO 国家代码映射为 LinkedIn `geoId`，拼接固定搜索参数，写入 `state.search_url`。

支持的国家：DE / NL / ES / AT / CH / BE / FR / PT / GB / SE / DK / PL

固定搜索参数：
- `keywords`：`Backend Java`
- `f_E`：`2,4`（Entry level + Mid-Senior）
- `f_JT`：`F`（Full-time）
- `f_TPR`：`r604800`（最近 7 天发布）
- `sortBy`：`R`（按相关性排序）

---

### 2. `fetch_jobs` — 从 LinkedIn 抓取职位

**文件**：`src/apply_job/nodes/fetch_jobs_from_linkedin.py`  
**工具**：`src/apply_job/tools/fetch_jobs_from_linkedin.py`

调用 Apify actor `curious_coder~linkedin-jobs-scraper`，一次抓取最多 300 条职位，写入 `state.raw_jobs`（`list[dict]`）。

关键 API 参数：
- `count`：300
- `splitByLocation`：false
- `splitCountry`：ISO 国家代码
- HTTP 超时：300 秒（与 Apify 同步运行限制一致）

---

### 3. `filter_jobs` — 两阶段过滤 + LLM 评分

**文件**：`src/apply_job/nodes/filter_jobs.py`  
**工具**：`src/apply_job/tools/filter_jobs.py`  
**Prompt**：`src/apply_job/prompts/evaluate.py`

#### Stage 1：规则过滤（无 LLM）

| 过滤规则 | 说明 |
|---------|------|
| 去重 | 读取 `excluded_files` 中的 job ID，跳过已处理的职位 |
| 语言检测 | 排除德语 / 荷兰语 / 西班牙语 / 波兰语（使用 `langdetect`） |
| 关键词排除 | 排除含 `frontend` / `front end` / `front-end` / `fullstack` / `full stack` / `full-stack` 的职位 |

#### Stage 2：LLM 评分（Dashscope qwen3.6-plus）

将 Stage 1 通过的职位（每批最多 300 条）连同简历文本发给 LLM，按以下规则分类：

| 优先级 | 条件 | 分类 |
|--------|------|------|
| 1 | JD 要求德语 | unsuitable |
| 2 | 要求超过 7 年经验 | unsuitable |
| 3 | 主要技术栈为 frontend/fullstack | unsuitable |
| 4 | 主语言非 JVM 且无 JVM 可替代说明 | unsuitable |
| 5 | JVM 语言为主要语言 | suitable |
| 6 | 技术栈模糊，无法判断 | pending |

LLM 输出字段（每条职位）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `tech_stack` | 0–10 | 技术栈匹配度 |
| `experience_level` | 0–10 | 经验要求匹配度 |
| `language_requirements` | 0–10 | 语言要求匹配度 |
| `domain_fit` | 0–10 | 领域契合度 |
| `overall` | 0–10 | 综合评分 |
| `classification` | string | `suitable` / `unsuitable` / `pending` |
| `summary` | string | 中文两句总结，说明主语言和分类原因 |

---

### 4. `review_pending` — 人工审核 pending 职位

**文件**：`src/apply_job/nodes/review_pending_jobs.py`

Human-in-the-loop 节点。对每条 `pending` 职位，通过 `interrupt()` 暂停图执行，展示职位信息，等待用户输入：

- `s` / `suitable` / `yes` / `y` → 标记为 suitable
- 其他 → 标记为 unsuitable

`suitable` 职位直接透传，无需人工确认。

---

### 5. `write_csv` — 写入 CSV

**文件**：`src/apply_job/nodes/write_jobs_into_csv.py`  
**工具**：`src/apply_job/tools/csv_ops.py`

| 输出文件 | 来源 | 说明 |
|---------|------|------|
| `data_dir/suitable.csv` | `filtered_jobs` | suitable 职位（人工确认后的 pending 也在此） |
| `data_dir/unsuitable.csv` | `unsuitable_jobs` | LLM 或人工判定为 unsuitable 的职位 |

两个文件均写入以下列：  
`id, title, companyName, link, descriptionText, tech_stack, experience_level, language_requirements, domain_fit, overall, classification, summary`

下次运行时，这两个文件作为 `excluded_files` 传入，用于去重。

---

## 四、State 结构

定义于 `src/apply_job/state.py`（`AgentState`）：

```python
country: str              # 输入：ISO 国家代码
search_url: str           # resolve_url 写入
data_dir: str             # 输入：数据目录
excluded_files: list[str] # 输入（可选）：去重文件列表
resume_path: str          # 输入：简历 PDF 路径

raw_jobs: list[dict]        # fetch_jobs 写入
filtered_jobs: list[dict]   # filter_jobs / review_pending 写入（suitable + pending 确认）
unsuitable_jobs: list[dict] # filter_jobs / review_pending 写入
csv_paths: list[str]        # write_csv 写入（追加语义）
```

---

## 五、配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DASHSCOPE_V2_API_KEY` | Dashscope API Key | — |
| `APIFY_API_TOKEN` | Apify API Token | — |
| `LLM_MODEL` | LLM 模型名 | `qwen3.6-plus` |

---

## 六、下游步骤

### 匹配 / 投递（Claude Code Skills）

**job-applier.skill**：读取 `suitable.csv`，打开投递链接，自动填写申请表单
