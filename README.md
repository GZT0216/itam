# ITAM · IT 资产管理系统

企业级 IT 资产全生命周期管理系统，覆盖资产入库、领用/借用/归还、调拨、维修、报废、盘点、合同、到期提醒、审计与报表。前后端分离，Docker Compose 一键部署。

> 仓库内不包含任何业务数据。按本文部署得到的是一套干净系统：只有初始管理员、角色权限与菜单，资产/单据/审批/合同等业务数据全部为空，需自行初始化部门、分类、型号与资产。

## 技术栈

- 前端：Vue 3 + TypeScript + Element Plus + Pinia + Vue Router + ECharts
- 后端：FastAPI + SQLAlchemy 2.0（async）+ Pydantic V2 + Alembic
- 数据库：MySQL 8.0（InnoDB / utf8mb4）；本地开发可用 SQLite
- 缓存与队列：Redis 7 + Celery
- 认证与权限：JWT 双令牌 + RBAC（菜单 / 操作 / 数据范围 / 字段）
- 部署：Docker Compose（命名 Volume 持久化）

## 功能模块

- 认证与 RBAC：登录/刷新/退出、强制改密、角色与权限、数据范围、字段权限、动态菜单
- 组织与人员：部门树、人员管理、AD/LDAP 同步与域账号登录
- 资产主数据：分类树、自定义字段、型号
- 资产台账：自动编码、软删除、时间线、附件、批量编辑、导入导出、全局搜索
- 资产业务：入库与库存、领用/借用/归还、调拨、维修、报废（含残值）
- 盘点：任务、扫码、盘盈盘亏、盈亏处理与报告
- 审批：可配置审批流程（按部门匹配、多级、或签/会签、兜底审批人）
- 运维与合同：合同台账、到期提醒
- 工作台与报表：指标驾驶舱、分类/部门分布、趋势、导出
- 待办与提醒：统一待办中心、角标、保修/合同/借用/盘点提醒

## 快速部署（Docker Compose）

要求：Docker 24+、Docker Compose v2，服务器可访问镜像源。

```bash
git clone <repo-url> itam
cd itam

cp .env.example .env
# 必填：数据库密码、SECRET_KEY、初始管理员密码
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" .env
sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 16)|" .env
sed -i "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$(openssl rand -hex 16)|" .env
sed -i "s|^DEFAULT_ADMIN_PASSWORD=.*|DEFAULT_ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d '/+=')|" .env

# 如 80 端口被占用，修改 .env 中的 HTTP_PORT
docker compose up -d --build
docker compose ps
```

访问 `http://<服务器IP>`（修改 `HTTP_PORT` 后需带端口）。

初始管理员：

- 用户名：`admin`
- 密码：`.env` 中的 `DEFAULT_ADMIN_PASSWORD`（仓库不提供默认密码，部署时必须自行设置）
- 首次登录后请立即在右上角「修改密码」

API 文档：`http://<服务器IP>/api/docs`

## 初始化数据说明（干净系统）

后端启动时自动执行 `alembic upgrade head` 与 `python -m app.initial_data`，仅创建：

- 数据库表结构（Alembic 迁移）
- 初始管理员 `admin`
- 系统角色（超级管理员/资产管理员/部门管理员/普通员工/审计员/维修人员）及权限、菜单
- 业务配置项（如领用审批设置）

不会创建任何资产、入库单、领用/借用单、审批实例、合同等业务数据。

`SEED_SAMPLE_DATA=false`（默认）时也不会创建示例部门/分类/型号。若本地演示需要示例主数据，可在 `.env` 中设为 `true`，该开关同样不会写入任何资产或业务单据。

部署后需以管理员身份自行创建：部门 → 资产分类 → 型号 → 入库/资产台账。系统没有预置部门与分类，首次进入业务页面为空属正常现象。

## 数据库迁移

```bash
# backend 容器启动时已自动执行；也可手动执行
docker compose exec backend alembic upgrade head

# 重新执行幂等初始化（只补齐管理员/角色/菜单，不会重复插入业务数据）
docker compose exec backend python -m app.initial_data
```

## 常用运维

```bash
docker compose ps
docker compose logs -f backend
docker compose restart backend

# 备份数据库
docker compose exec mysql sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction "$MYSQL_DATABASE"' > itam-backup.sql

# 停止服务（保留数据卷）
docker compose down

# 危险：删除所有数据卷，仅在确认丢弃数据时使用
docker compose down -v
```

数据卷：`mysql_data`、`redis_data`、`uploads_data`、`app_logs`。

## 本地开发

推荐 Node.js 20.19+ / 22.12+、Python 3.12。

后端（SQLite + 内存令牌存储，便于脱离 MySQL 调试）：

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
source .venv/bin/activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt -r requirements-dev.txt

export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
export TOKEN_STORE=memory
export SECRET_KEY="local-dev-secret-key-change-me-0123456789"
export DEFAULT_ADMIN_PASSWORD="ChangeMe@12345"
export SEED_SAMPLE_DATA=true   # 可选：写入示例部门/分类/型号

# SQLite 快速调试：直接按模型建表（Alembic 迁移以 MySQL 为目标）
python - <<'PY'
import asyncio
from app.models import Base
from app.core.database import engine

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(main())
PY

python -m app.initial_data
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install --registry=https://registry.npmmirror.com
npm run dev
```

打开 `http://127.0.0.1:5173`，Vite 已将 `/api` 代理到 `http://127.0.0.1:8000`。

## 目录结构

```
itam/
├── backend/
│   ├── app/{api/v1, core, models, schemas, services, repositories, tasks}
│   ├── alembic/versions/        # 从零建表的迁移
│   ├── tests/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── requirements.txt
├── frontend/
│   ├── src/{api, components, views, stores, router, types, utils, styles}
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## 安全与一致性约束

- 权限判断只在后端可信：接口依赖校验权限码，查询层按数据范围过滤；前端菜单与按钮仅作展示控制。
- 令牌安全：Access Token 30 分钟，Refresh Token 7 天且单次使用自动轮换；退出与改密会使旧令牌立即失效。
- 审计：关键操作与业务写入在同一事务内记录操作人、请求上下文、变更前后值。
- 资产业务：状态只能由业务动作驱动（状态机）；关键操作使用事务与 `version` 乐观锁；历史记录只追加。
- 敏感配置：`.env` 已被 `.gitignore` 排除，请勿提交真实密码、密钥或 AD 地址。

## 部署后自检

```bash
# 1. 管理员可登录
curl -s -X POST http://<服务器IP>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<你设置的密码>"}'

# 2. 业务列表为空（登录后取 token，再调用）
curl -s http://<服务器IP>/api/v1/assets -H "Authorization: Bearer <access_token>"
curl -s http://<服务器IP>/api/v1/asset-requests/review -H "Authorization: Bearer <access_token>"

# 3. 首页指标全为 0，无最近资产/保修提醒
curl -s http://<服务器IP>/api/v1/dashboard/summary -H "Authorization: Bearer <access_token>"
```
