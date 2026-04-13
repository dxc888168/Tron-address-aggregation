# TRON 自动归集系统（私有化）

Telegram：https://t.me/xzpq66  Telegram频道：https://t.me/NLGH999 

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

详细版本请看：`docs/Windows使用说明（详细）.md`

项目根目录双击：

- `一键启动.bat`（中文入口）
- 或 `start_local.bat`

脚本会自动执行：

- 创建/复用 `backend\.venv`
- 安装依赖
- 启动 API（`uvicorn`）
- 当 `.env` 里 `JOB_EXECUTION_MODE=redis` 时自动启动 Worker
- 自动打开浏览器到 `http://localhost:8000/`

### 4.1 首次必须配置的 `.env`（详细）

脚本会在首次启动时自动创建 `.env`（由 `.env.local.example` 复制）。  
你仍需要手工填写关键字段，尤其是下面 4 项：

```env
ADMIN_PASSWORD=你的强密码
JWT_SECRET=长随机字符串
ENCRYPTION_MASTER_KEY=32字节base64主密钥
TRONGRID_API_KEY=你的TronGrid API Key
```

字段说明（本地模式）：

| 字段 | 用途 | 是否必填 | 建议 |
|---|---|---|---|
| `ADMIN_PASSWORD` | 管理员密码 | 是 | 至少 12 位，含大小写数字符号 |
| `JWT_SECRET` | 登录会话签名密钥 | 是 | 长随机字符串，禁止默认值 |
| `ENCRYPTION_MASTER_KEY` | 私钥加密主密钥 | 是 | 使用 `python backend/scripts/generate_master_key.py` 生成 |
| `TRONGRID_API_KEY` | 链上查询与广播通道 | 生产强烈建议必填 | 未配置可能被公共限流（429） |
| `USDT_CONTRACT` | TRC20-USDT 合约地址 | 建议固定 | 主网使用 `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` |
| `JOB_EXECUTION_MODE` | 任务执行模式 | 否 | 本地推荐 `inline` |
| `DATABASE_URL` | 数据库连接 | 否 | 本地默认 SQLite 可直接用 |

说明：

- 断网情况下：可生成/导入/管理地址。
- 联网情况下：才能同步余额与执行归集。
- `TRONGRID_API_KEY` 不影响离线管理，但影响联网归集稳定性。

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

### 4.2 获取 TronGrid API Key（简版）

1. 打开 TronGrid 控制台并登录  
2. 创建 API Key  
3. 填入 `.env`：

```env
TRONGRID_API_KEY=你的key
```

4. 重启服务生效

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

- `TRONGRID_API_KEY` 生产环境强烈建议配置，否则可能遇到公共限流（429）
- `USDT_CONTRACT` 默认主网合约地址
- 上线前务必修改默认管理员密码与密钥
