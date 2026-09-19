# 智能医疗预约诊疗系统

基于 FastAPI、PostgreSQL/pgvector、Celery、Redis Broker 和 DeepSeek 的 AI 应用工程项目，覆盖预约、接诊、检查报告、AI 解读、处方、收费和发药闭环，适合求职展示与学习。

> 本项目使用虚构测试数据，仅用于教学、演示和求职展示，不接入真实患者数据或医保系统。AI 输出仅供参考，不能替代医生诊断。

## 核心能力

- 分诊 Agent：症状理解、RAG 分诊指引检索、真实科室匹配、多轮追问和流式输出。
- 报告解读 Agent：检验科上传 CSV/结构化报告，Celery 异步执行 RAG 检索和 AI 解读，患者可继续流式追问。
- 完整业务流程：预约 → 医生接诊 → 等待检查 → 报告录入 → AI 解读 → 医生补充诊断和处方 → 收费 → 发药。
- RAG 工程化：pgvector 向量检索 + PostgreSQL 全文检索 + RRF 融合；Rerank 保留为可选评测能力，当前链路关闭。
- 统一 LLM 服务：Token 预算、调用日志、超时、重试、降级和安全审核集中处理。
- 角色权限：患者使用前台；医生、药师、收费员、检验科和超级管理员使用后台。

## 技术栈

Python 3.12、FastAPI、SQLAlchemy Async、Alembic、PostgreSQL、pgvector、Redis、Celery、DeepSeek、DashScope Embedding、LangChain 文档切分、Docker Compose、Nginx。

## 架构与目录

```text
app/api                 Client/Backoffice API
app/models              数据模型
app/services/common     LLM、RAG 公共服务
app/services/client     患者侧 Agent 服务
app/schedule/jobs       Celery 异步任务
migrations              Alembic 迁移
scripts/init_data.py    初始化后台测试账号
scripts/seed             基础演示数据
scripts/eval_agents.py   Agent 评测
docs、Study              架构、部署和学习文档
```

分诊 Agent 使用代码驱动的固定工作流：会话加载 → RAG 检索 → 科室查询 → Prompt 构造 → LLM 生成 → 内容审核 → 科室匹配。项目不使用 LangChain `AgentExecutor`，对外可描述为“DeepSeek + 自定义工作流编排 + RAG”。



## 项目边界

这是 AI 应用工程化求职项目，不是可直接用于真实医疗机构的生产系统。真实上线还需要隐私保护、数据脱敏、访问审计、临床验证、医疗合规和专业人员审核等能力。

## 二次开发：轻量单元测试

在 Windows PowerShell 中进入本目录后，可以先只安装 pytest，运行不依赖数据库、模型SDK和FastAPI的纯函数测试：

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-test.txt
& ".\.venv\Scripts\python.exe" -m pytest tests/unit/test_ranking.py -v
```

这一组测试通过只证明 RRF 纯函数符合当前约定，不代表数据库检索、Embedding、Rerank或完整RAG链路已经通过。
