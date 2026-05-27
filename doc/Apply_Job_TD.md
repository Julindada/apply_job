# Apply Job — Technical Design

## 一、技术栈

- **语言 / 框架**：Python 3.13 + LangGraph
- **LLM**：Alibaba Dashscope（模型 `qwen3.6-plus`，通过 OpenAI 兼容接口调用）
- **职位抓取**：Apify LinkedIn Jobs Scraper actor
- **浏览器自动化**：browser-use（底层 Playwright，通过 CDP 连接宿主机 Chrome）
- **项目入口**：`src/apply_job/graph.py`（发现流水线）、`src/apply_job/apply_graph.py`（投递流水线）
- **运行方式**：Docker 容器；投递时用 `docker exec -it` 交互

---

## 二、整体流程

### 2.1 发现流水线（自动，无人值守）

```
resolve_url → fetch_jobs → rule_filter → llm_score → company_dedup → review_pending → write_csv
```

每个步骤对应 `src/apply_job/nodes/` 下的一个 LangGraph 节点，共享同一个 `AgentState`。运行结果写入 `suitable.csv`，作为投递循环的输入。

### 2.2 投递循环（半自动，人机协作）

```
读取 suitable.csv
      ↓
Agent 新标签打开投递链接（Chrome CDP）
      ↓
用户手动填写基本信息
      ↓
用户按 Enter 触发 Agent
      ↓
LLM 生成 cover letter → 保存为临时 PDF
      ↓
Agent 填写剩余必填字段 / 上传 cover letter / 点击提交
      ↓
Agent 新标签打开下一个链接
      ↓
写入 applied.csv（记录投递结果）        ← 待开发
```

---

## 三、发现流水线节点详解

### 1. `resolve_url` — 生成 LinkedIn 搜索 URL

**文件**：`src/apply_job/nodes/resolve_search_url.py`

将 ISO 国家代码映射为 LinkedIn `geoId`，拼接固定搜索参数，写入 `state.search_url`。

支持的国家：DE / NL / ES / AT / CH / BE / FR / PT / GB / SE / DK / PL

固定搜索参数：
- `keywords`：`Backend Java`
- `f_E`：`2,4`（Entry level + Mid-Senior）
- `f_JT`：`F`（Full-time）
- `f_TPR`：`r1814400`（最近 3 周发布）
- `sortBy`：`DD`（按日期排序）

---

### 2. `fetch_jobs` — 从 LinkedIn 抓取职位

**文件**：`src/apply_job/nodes/fetch_jobs_from_linkedin.py`  
**工具**：`src/apply_job/tools/fetch_jobs_from_linkedin.py`

调用 Apify actor `curious_coder~linkedin-jobs-scraper`，一次抓取最多 300 条职位，写入 `state.raw_jobs`（`list[dict]`）。

---

### 3. `rule_filter` — 规则过滤（无 LLM）

**文件**：`src/apply_job/nodes/rule_filter.py`  
**工具**：`src/apply_job/tools/filter_jobs.py`

| 过滤规则 | 说明 |
|---------|------|
| 去重 | 读取 `excluded_files` 中的 job ID，跳过已处理的职位 |
| 拒绝公司名单 | 读取 `data_dir/rejection_companies_sorted.txt`，按双向子串匹配过滤（大小写不敏感，去除法律后缀） |
| 语言检测 | 排除德语 / 荷兰语 / 西班牙语 / 波兰语（使用 `langdetect`） |
| 关键词排除 | 排除含 `frontend` / `fullstack` 等关键词的职位 |

**拒绝公司名单格式**（`rejection_companies_sorted.txt`）：
```
# 格式：YYYY-MM-DD  公司名
2026-01-06  Delivery Hero
2026-03-23  Canva
```

---

### 4. `llm_score` — LLM 评分与分类

**文件**：`src/apply_job/nodes/llm_score.py`  
**Prompt**：`src/apply_job/prompts/evaluate.py`

将过滤后的职位（每批最多 300 条）连同简历文本发给 LLM，按以下规则分类：

| 优先级 | 条件 | 分类 |
|--------|------|------|
| 1 | JD 要求德语 | unsuitable |
| 2 | 要求超过 7 年经验 | unsuitable |
| 3 | 主要技术栈为 frontend/fullstack | unsuitable |
| 4 | 主语言非 JVM 且无 JVM 可替代说明 | unsuitable |
| 5 | JVM 语言为主要语言 | suitable |
| 6 | 技术栈模糊，无法判断 | pending |

LLM 输出字段：`tech_stack` / `experience_level` / `language_requirements` / `domain_fit` / `overall`（均 0–10）、`classification`、`summary`

---

### 5. `company_dedup` — 公司去重

**文件**：`src/apply_job/nodes/company_dedup.py`

对 `filtered_jobs` 按 `companyName` 分组，同一公司只保留 `overall` 最高的职位，其余丢弃。

---

### 6. `review_pending` — 人工审核

**文件**：`src/apply_job/nodes/review_pending_jobs.py`

Human-in-the-loop 节点。对每条 `pending` 职位，通过 `interrupt()` 暂停图执行，等待用户输入 `s`（suitable）或其他（unsuitable）。

---

### 7. `write_csv` — 写入 CSV

**文件**：`src/apply_job/nodes/write_jobs_into_csv.py`

| 输出文件 | 内容 |
|---------|------|
| `data_dir/suitable.csv` | suitable 职位（含人工确认的 pending） |
| `data_dir/unsuitable.csv` | 不适合的职位（追加写入） |

---

## 四、投递循环模块详解

### 1. `nodes/apply_jobs.py` — 投递节点 ✅ 已实现（待测试）

**文件**：`src/apply_job/nodes/apply_jobs.py`  
**图**：`src/apply_job/apply_graph.py`（单节点图，注册为 `"apply"`）  
**入口**：`apply-job apply`（`docker exec -it apply-job apply-job apply`）

`ApplyState`（定义于同文件）：

```python
class ApplyState(TypedDict):
    csv_path: str
    resume_path: str
```

节点逻辑（每个职位循环一次，使用 `input()` 等待用户，无需 LangGraph interrupt）：

```
for job in jobs:
    1. _browser_session() → Agent 新标签打开链接
    2. input() 等待用户填写基本信息
    3. generate_cover_letter_pdf()
    4. _browser_session() → Agent 填必填字段 + 上传 CL + 提交 + 开下一个链接
```

两次 browser session 分开：第一次仅导航，第二次填写提交。Chrome 保持运行，标签页在两次 session 之间保持打开。

CLI 参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--csv` | 职位 CSV 文件路径 | `data_dir/suitable.csv` |
| `--resume` | 简历 PDF 路径 | `settings.default_resume_path` |

宿主机 Chrome 启动方式：
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --no-first-run
```

**待开发**：
- [ ] CDP 连接失败时的明确错误提示
- [ ] 提交后验证是否出现成功确认信息

---

### 2. `tools/cover_letter.py` — Cover Letter 生成 ✅ 已实现（待测试）

**文件**：`src/apply_job/tools/cover_letter.py`

流程：
1. 用 LLM（`temperature=0.7`）根据职位描述 + 简历生成 3–4 段英文 cover letter
2. 用 `fpdf2` 渲染为 PDF（Helvetica 字体，Latin-1 编码）
3. 保存为临时文件，Agent 上传后由调用方删除

**待开发**：
- [ ] 支持 Unicode 字符（中文简历内容中的特殊字符）
- [ ] Cover letter 质量评估 / 缓存（同一职位不重复生成）

---

---

## 五、State 结构（发现流水线）

定义于 `src/apply_job/state.py`（`AgentState`）：

```python
country: str              # 输入：ISO 国家代码
search_url: str           # resolve_url 写入
excluded_files: list[str] # 输入（可选）：去重文件列表
resume_path: str          # 输入：简历 PDF 路径

raw_jobs: list[dict]        # fetch_jobs 写入
filtered_jobs: list[dict]   # rule_filter / llm_score / company_dedup 逐步写入
unsuitable_jobs: list[dict] # llm_score / review_pending 写入
csv_paths: list[str]        # write_csv 写入
```

---

## 六、配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DASHSCOPE_V2_API_KEY` | Dashscope API Key | — |
| `APIFY_API_TOKEN` | Apify API Token | — |
| `LLM_MODEL` | LLM 模型名 | `qwen3.6-plus` |
| `LLM_BASE_URL` | LLM API 地址 | `https://dashscope-us.aliyuncs.com/compatible-mode/v1` |
| `CDP_URL` | Chrome DevTools Protocol 地址 | `http://host.docker.internal:9222` |
| `DATA_DIR` | 数据目录（容器内） | `/app/data` |
| `DEFAULT_RESUME_PATH` | 默认简历路径 | `/app/data/resume.pdf` |

---

## 七、数据文件

| 文件 | 用途 | 写入方 |
|------|------|--------|
| `suitable.csv` | 发现流水线输出，投递循环输入 | `write_csv` 节点（覆盖写） |
| `unsuitable.csv` | 不合适职位存档，下次去重用 | `write_csv` 节点（追加写） |
| `rejection_companies_sorted.txt` | 拒绝公司名单，手动维护 | 用户 |
| `resume.pdf` | 简历，LLM 评分和 cover letter 生成使用 | 用户 |
