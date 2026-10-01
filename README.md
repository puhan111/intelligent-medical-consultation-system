# 智能医疗预约诊疗系统

[![CI](https://github.com/puhan111/intelligent-medical-consultation-system/actions/workflows/ci.yml/badge.svg)](https://github.com/puhan111/intelligent-medical-consultation-system/actions/workflows/ci.yml)

覆盖「预约 → 分诊 → 接诊 → 检查报告 → AI 解读 → 处方 → 收费 → 发药」完整业务闭环的全栈 AI 应用工程项目。后端基于 FastAPI + PostgreSQL/pgvector + Celery，前端包含患者端与管理后台两个独立 Vue3 应用，AI 能力由 DeepSeek + RAG 提供，支持 Docker Compose 一键部署。

## 功能总览

**患者端（medical-client）**
- 注册登录、科室/医生浏览、在线预约挂号
- 分诊 Agent 多轮对话（流式输出，支持中断恢复）
- 检查报告查看、AI 报告解读与追问（流式）
- 处方查看、在线缴费（支付回调由 Celery 延迟任务模拟）

**管理后台（medical-admin）**
- 科室、医生、药品、预约、账单、处方全流程管理
- RAG 知识库管理（分诊指引、医学参考资料分库维护）
- RAG 检索质量评测：命中率 / Recall / MRR 指标计算与回归对比
- AI 运行监控：LLM 调用日志、耗时与 Token 消耗追踪

**后端 AI 与工程能力（backend）**
- RAG 链路：向量检索（pgvector）+ RRF 融合排序 + Rerank + Token 预算控制
- 只读 MCP 服务：向外部 Agent 暴露安全的数据库只读查询能力
- 限流、内容审核、邮件通知（Brevo）、S3 兼容对象存储
- Alembic 迁移、pytest 单元/集成测试、GitHub Actions CI

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI · SQLAlchemy · Alembic · Celery · Redis |
| 数据 | PostgreSQL 16 + pgvector |
| AI | DeepSeek API · RAG · MCP（只读） |
| 前端 | Vue 3 · TypeScript · Vite · Element Plus（管理端） |
| 运维 | Docker Compose · Nginx · GitHub Actions |

## 目录结构

```
├── backend/            FastAPI 后端（api / services / models 三层架构）
│   ├── app/prompts/    分诊、报告解读等 Prompt 模板（带版本管理）
│   ├── app/services/   业务逻辑，common/ 内含 RAG、评测、MCP 等核心服务
│   ├── migrations/     Alembic 数据库迁移
│   ├── scripts/        RAG/Agent 评测脚本与知识库源文档
│   └── tests/          pytest 单元与 API 测试
├── medical-admin/      管理后台（Vue3 + Element Plus）
├── medical-client/     患者端（Vue3）
├── 部署文档.md          完整部署说明
```

## 快速开始

```bash
cd backend
cp .env.example .env        # 填入 DeepSeek API Key 等配置
docker compose up -d --build
```

启动后：患者端与管理后台经 Nginx 统一入口访问，Flower（Celery 监控）随栈提供。详细虚拟机/本地部署步骤见 [部署文档.md](部署文档.md)，本地开发调试说明见 [backend/README.md](backend/README.md)。

## 测试与质量

```bash
cd backend
pip install -r requirements-dev.txt -c constraints.txt
pytest -q                    # 单元 + API 测试
python scripts/eval_rag_retrieval.py   # RAG 检索质量评测
```

CI 流水线（见 [.github/workflows/ci.yml](.github/workflows/ci.yml)）在每次推送时执行：后端 lint + pytest、双前端 TypeScript 检查与构建、Docker Compose 配置校验、空库迁移至 head 并比对模型一致性。
