# Glimmer / 流萤 — 人际网 App（关系发现引擎）

> 基于 AI Agent 协作开发的项目。当前阶段：**M2 实现中**（核心 API 完整化 + Web 看图）。

## 项目来源

项目背景来自一段 ChatGPT 对话（2026-06-24），对话从"各国 App 生态"调研切入，逐步演进为"人际网 / 关系发现引擎"软件 Idea。完整背景见 `context/` 目录。

## 核心定位（一句话）

发现你身边隐藏的关系机会——"展示关系的存在，而不暴露关系的身份"。

## 当前阶段与第一版范围（2026-08-12 更新）

- **阶段**：M1（基础设施 + 数据层）已完成并验证，**M2 进行中**（核心 API 完整化 + Web 看图）。
- **第一版 = 关系资产管理 + 可视化 + 2 度被动浏览**：注册登录（手机号 + 微信[后补] + Apple[M3]）→ 移动端一键导入通讯录 → 精美关系图（分组着色）→ 编辑修正 → 关系资产统计 → 看到朋友的朋友（被动浏览 2 度，化名/授权名）→ 隐私控制（双向全局开关）。
- **Web 为辅**：同一账号，Web 只做精美看图，不做导入。
- **面向中国大陆**：首版中文，安卓 + iOS。
- **第二版**：关系发现（主动搜索）+ 引荐请求 + AI + 3 度 + 失联提醒 + 推送 + 机会市场 + 商业化 + 认领完善。
- **隐私核心原则**：真名私有，化名是公开形象；未注册用户默认化名；认领机制；隐私控制双向全局开关。

## 实现进度

| 里程碑 | 状态 | 内容 |
| --- | --- | --- |
| M1 基础设施 + 数据层 | ✅ 完成 | FastAPI 骨架、5 表 schema、27 端点、Alembic、CI、连上 Supabase |
| M2 核心 API + Web 看图 | 🔄 进行中 | 阿里云 SMS、2 度 Service、React + Cytoscape.js 关系图 |
| M3 移动端 App | ⏳ | Flutter 3 Tab、通讯录导入、关系图、隐私设置 |
| M4 打磨 + 分发 | ⏳ | 视觉、异常流、TestFlight + APK |

详细里程碑见 [plan/开发计划.md](plan/开发计划.md)。

## 技术栈（M1 落地）

| 层 | 选型 |
| --- | --- |
| 后端 | FastAPI 0.115 + Python 3.13 |
| 数据库 | PostgreSQL（Supabase 托管，ap-southeast-1） |
| ORM / 迁移 | SQLAlchemy 2.0 (async) + Alembic |
| 认证 | JWT (python-jose) + HMAC-SHA256 手机号哈希 |
| 测试 / CI | pytest + httpx + GitHub Actions |
| Web（M2） | React + Cytoscape.js |
| 移动端（M3） | Flutter + Riverpod |

## 本地运行

```bash
cd server
source .venv/bin/activate
cp .env.example .env   # 填上 Supabase 配置
alembic upgrade head   # 建表
uvicorn app.main:app --reload   # 启动，访问 http://localhost:8000/docs
```

## 目录结构

| 目录 | 用途 | 状态 |
| --- | --- | --- |
| `context/` | 项目背景资料 | 已有 |
| `requirements/` | 需求文档 / PRD / 决策记录 | 已有 |
| `design/` | 产品与技术设计文档 | 已有 |
| `plan/` | 开发计划、里程碑 | 已有 |
| `server/` | FastAPI 后端 | 已有（M1 完成） |
| `web/` | React 前端（M2） | 待产出 |
| `app/` | Flutter 客户端（M3） | 待产出 |
| `docs/` | 其他文档 | 待产出 |

## 文档地图（新 session 上手顺序）

| 顺序 | 文档 | 内容 |
| --- | --- | --- |
| 1 | [AGENTS.md](AGENTS.md) | 工作指引、核心原则、产出规范 |
| 2 | [requirements/产品决策记录.md](requirements/产品决策记录.md) | **所有已拍板决策的唯一权威记录**（先读） |
| 3 | [requirements/功能地图.md](requirements/功能地图.md) | 完整功能地图（含 P1/P2 backlog） |
| 4 | [plan/开发计划.md](plan/开发计划.md) | 里程碑拆分与开发计划 |
| 5 | [design/技术选型.md](design/技术选型.md) | 技术栈方向 |
| 6 | [design/技术栈细化与采购清单.md](design/技术栈细化与采购清单.md) | 技术栈细化 + 采购链接 |

> 维护要求：任何需求 / 方向 / 决策变更，先记录到 [产品决策记录.md](requirements/产品决策记录.md)，再更新受影响文档，保持本文档地图始终反映最新状态。
