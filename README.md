# SmartOrderingAgent 智能点餐 Agent

用自然语言点餐的 AI 应用：用户像聊天一样说"我想吃辣的""帮我订两个人的位置"，Agent 自己决定调哪个工具去查菜、查 FAQ、写预订，最后把结果返回给前端页面。

前端是一个仿点餐 App 的界面，后端是 FastAPI，中间由 LangChain 的 Agent 驱动多轮工具调用。

## 功能

| 功能 | 说明 |
| --- | --- |
| AI 对话点餐 | 流式输出（SSE），支持多轮上下文 |
| 菜品查询 | 按分类/关键词查 `menu` 库里的菜品 |
| 预订餐桌 | 自然语言预订，直接写回数据库 |
| FAQ 问答 | 地址、电话、营业时间（存在 Redis 里） |
| 按口味找菜 | 依赖 Milvus 向量库，当前**未部署**，见「已知限制」 |
| 距离配送范围 | 走高德 MCP 算路径，前端已接，后端接口**待实现** |

## 技术栈

| 层 | 用了什么 |
| --- | --- |
| 后端 | FastAPI + Uvicorn，SSE 流式返回 |
| Agent | LangChain 1.4（`create_agent` + `@tool`）、LangGraph 状态管理 |
| 大模型 | DeepSeek（OpenAI 兼容接口），可换任意兼容端点 |
| 数据库 | MySQL 8（菜单、桌位、订单、预订） |
| 缓存 | Redis（FAQ 数据） |
| 前端 | Vue 3 + Vite 4 |
| 外部工具 | 高德地图 MCP（SSE 方式接入） |

## 目录结构

```
SmartOrderingAgent/
├── api/main.py                  # FastAPI 入口：/chat /menu/list /faq/suggest /reservation/list
├── agent/
│   ├── langchain_assitant.py    # Agent 核心：模型、工具、MCP 接入
│   ├── redis_data_sync.py       # 把 FAQ 数据同步进 Redis
│   ├── milvus_data_sync.py      # 向量库同步（需 Milvus，当前未启用）
│   └── prompts/system_prompt.txt# AI 人设 / 系统提示词
├── menu.sql                     # 数据库初始化脚本
├── ui/                          # Vue3 前端
├── .vscode/                     # 调试配置、任务、扩展推荐
├── scripts/                     # 各服务的单独启动脚本
├── start.bat                    # 一键启动全部（Redis + 后端 + 前端 + 开浏览器）
└── 启动说明.md                  # 新手版启动教程（含常见报错对照表）
```

## 环境要求

- Python 3.13（用 `uv` 管理依赖）
- Node.js 18+
- MySQL 8.x
- Redis 6+

## 快速开始

### 1. 配置环境变量

在项目根目录新建 `.env`（该文件已被 `.gitignore` 忽略，不会提交）：

```ini
# MySQL
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USERNAME=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=menu

# Redis
REDIS_URL=redis://127.0.0.1:6379

# 大模型（任意 OpenAI 兼容端点）
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-flash

# 向量库（可选，不填则「按口味找菜」不可用）
MILVUS_URI=
MILVUS_TOKEN=
```

### 2. 建库

```bash
mysql -u root -p < menu.sql
```

### 3. 装依赖

```bash
uv sync                     # 后端依赖
cd ui && npm install        # 前端依赖
```

### 4. 启动

**方式 A：VS Code（推荐）**

1. `Ctrl+Shift+P` → `Tasks: Run Task` → `① 启动前端 (Vite)`
2. `Ctrl+Shift+D` → 选 `★ 启动后端（带调试，自动准备 Redis/FAQ）` → `F5`
3. 浏览器打开 http://localhost:3000

**方式 B：一键脚本**

双击根目录的 `start.bat`，它会自动检查 Redis、同步 FAQ、拉起前后端并打开浏览器。

> 详细的步骤、端口说明和报错对照表见 [启动说明.md](./启动说明.md)。

## 相对原仓库做的改造

本仓库基于 [JxKim/SmartOrderingAgent](https://github.com/JxKim/SmartOrderingAgent)，在原代码基础上做了「让它在本地跑起来」的工程化改造：

- **配置全部环境变量化**：数据库地址、Redis 地址、模型名不再硬编码，改读 `.env`
- **密码含 `@` 的坑**：MySQL 连接串对用户名/密码做 `quote_plus()` 编码，否则会被当成 URL 分隔符
- **补齐 VS Code 配置**：`.vscode/` 下加入调试配置、任务、扩展推荐，F5 即可带断点启动
- **加入一键启动脚本**：根目录 `start.bat` + `scripts/` 下各服务独立脚本
- **修复两处启动即报错**：`redis_data_sync.py` 中空的 `if __name__ == "__main__":` 块导致的 IndentationError

## 已知限制

| 问题 | 说明 |
| --- | --- |
| Milvus 未部署 | 「按口味找菜」工具不可用，需要 Docker 或 Zilliz Cloud |
| `POST /delivery` 未实现 | 前端「配送范围」按钮会 404，后端没有对应路由 |
| `thread_id` 写死为 `123` | 所有人共用同一个会话内存，多人同时用会串上下文 |
| MCP 地址硬编码 | 高德 MCP 的 SSE 地址写死在 `agent/langchain_assitant.py` 里，建议后续抽到 `.env` |

## 说明

本项目为学习用途，菜单数据、桌位数量等均为演示数据。
