# TRON 自动归集系统（私有化）

Telegram：@xzpq66    @Telegram频道：https://t.me/NLGH999 

这是一个可本地部署的 TRON 托管钱包归集系统，支持：

- 批量生成 TRON 地址与私钥（私钥加密存储）
- 地址资产管理（TRX + USDT(TRC20)）
- 一键归集任务（异步队列执行）
- Web 管理后台（本地默认免登录，打开即用）
- 审计日志

## 1. 技术栈

- Backend: FastAPI + SQLAlchemy
- Queue: Inline(本地默认) / Redis + RQ Worker
- DB: SQLite(本地默认) / PostgreSQL
- Chain: TronGrid / TronPy
- Frontend: FastAPI Static Web

## 2. 项目结构

```text
.
├─ backend
│  ├─ app
│  │  ├─ api/routes
│  │  ├─ core
│  │  ├─ db
│  │  ├─ models
│  │  ├─ services
│  │  ├─ tasks
│  │  ├─ static
│  │  ├─ main.py
│  │  └─ worker.py
│  ├─ scripts
│  ├─ requirements.txt
│  └─ Dockerfile
├─ docker-compose.yml
├─ .env.local.example
└─ .env.docker.example
```

## 3. 快速启动（Docker）

1. 复制环境变量

```bash
cp .env.docker.example .env
```

2. 生成主加密密钥并写入 `.env`

```bash
python backend/scripts/generate_master_key.py
```

把输出填入：

```env
ENCRYPTION_MASTER_KEY=你的32字节base64
JWT_SECRET=你的强随机字符串
```

3. 启动

```bash
docker compose up -d --build
```

4. 访问

- Web 管理台: `http://localhost:8000/`
- Health: `http://localhost:8000/api/v1/health`

## 4. 本地开发启动（不使用 Docker）

### Windows 一键启动（推荐）

项目根目录双击：

- `一键启动.bat`（中文入口）
- 或 `start_local.bat`

脚本会自动执行：

- 创建/复用 `backend\.venv`
- 安装依赖
- 启动 API（`uvicorn`）
- 当 `.env` 里 `JOB_EXECUTION_MODE=redis` 时自动启动 Worker
- 自动打开浏览器到 `http://localhost:8000/`

1. 复制环境变量（本地版）

```bash
cp .env.local.example .env
```

2. 安装依赖

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows 用 .venv\\Scripts\\activate
pip install -r requirements.txt
```

Windows 如果遇到脚本执行策略限制，跳过 `activate`，直接使用 `.venv\Scripts\python.exe` 执行命令即可。

3. Windows 本地推荐直接用 `inline + SQLite`（无需 PostgreSQL/Redis）：

```bash
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

说明：本地默认 `AUTH_DISABLED=true`，无需登录。

如果你要用 Redis 队列模式：

1. `.env` 设置 `JOB_EXECUTION_MODE=redis`
2. 启动 API 后，再开第二个终端执行：

```bash
cd backend
.venv\Scripts\python.exe -m app.worker
```

## 5. 核心 API

- `POST /api/v1/auth/login`
- `POST /api/v1/addresses/batch-generate`
- `GET /api/v1/addresses`
- `POST /api/v1/assets/sync`
- `GET /api/v1/assets/overview`
- `POST /api/v1/sweep/preview`
- `POST /api/v1/sweep/run`
- `GET /api/v1/sweep/jobs`
- `GET /api/v1/sweep/jobs/{id}`
- `POST /api/v1/sweep/jobs/{id}/retry`
- `GET /api/v1/audit-logs`
- `GET/POST /api/v1/system/topup-source`

## 6. 注意事项

- `TRONGRID_API_KEY` 建议配置，否则可能遇到公共限流
- `USDT_CONTRACT` 默认主网合约地址
- 上线前务必修改默认管理员密码与密钥
