# apply-job

基于 LangGraph 构建的 agent，用于自动化职位研究与投递流程。

## 项目结构

```
apply-job/
├── src/apply_job/          # 核心源码
│   ├── config.py           # 全局配置：加载模型名称、API key、温度等参数（环境变量）
│   ├── state.py            # LangGraph 状态定义（TypedDict），贯穿全图的共享数据结构
│   ├── graph.py            # 图构建入口：组装所有节点，定义边与路由逻辑，返回编译后的图
│   ├── nodes/              # 图节点（每个函数接收 state，返回 state 的增量更新）
│   │   ├── research.py     # 职位研究节点：抓取/分析职位信息
│   │   ├── evaluate.py     # 匹配评估节点：计算简历与职位的匹配度
│   │   └── apply.py        # 自动投递节点：通过浏览器自动填写并提交申请
│   ├── tools/              # Agent 可调用的工具函数
│   │   ├── browser.py      # 浏览器自动化工具（页面导航、表单填写、点击等）
│   │   └── file_ops.py     # 文件读写工具（简历读取、投递结果持久化等）
│   ├── prompts/            # Prompt 模板集中管理，与代码解耦
│   │   ├── research.py     # 职位研究相关的 prompt
│   │   └── evaluate.py     # 简历匹配评估相关的 prompt
│   └── utils/              # 辅助函数与通用工具
├── tests/                  # 单元测试与集成测试
├── main.py                 # 入口文件：加载配置、构建图、运行 agent
└── pyproject.toml          # 项目依赖与构建配置
```

## 核心设计

- **State** — 定义 agent 在流程中传递的共享状态（职位列表、简历、匹配分数等）
- **Nodes** — 每个节点是图中的一个步骤，接收 state 并返回更新，节点间解耦
- **Graph** — 用 `StateGraph` 连接节点，支持条件边（conditional edges）和路由
- **Tools** — agent 通过工具调用与外部世界交互（浏览器、文件系统等）
- **Prompts** — prompt 模板独立管理，方便迭代和 A/B 测试

## 快速开始

```bash
# 安装依赖
uv sync

# 设置环境变量
export ANTHROPIC_API_KEY="your-key-here"

# 运行
uv run python main.py
```
