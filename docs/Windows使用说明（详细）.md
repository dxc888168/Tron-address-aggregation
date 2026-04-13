# Windows 使用说明（详细）

## 1. 最快启动方式

1. 下载项目（Git clone 或 ZIP 解压）
2. 双击项目根目录 `一键启动.bat`
3. 首次启动会自动：
   - 创建 `backend\.venv`
   - 安装依赖
   - 启动服务
   - 自动打开 `http://localhost:8000`

## 2. `.env` 文件说明

首次运行时，脚本会自动创建 `.env`（由 `.env.local.example` 复制）。  
你必须检查并填写以下字段：

```env
ADMIN_PASSWORD=你的强密码
JWT_SECRET=你的长随机字符串
ENCRYPTION_MASTER_KEY=你的32字节base64主密钥
TRONGRID_API_KEY=你的TronGrid API Key
```

### 如何生成 `ENCRYPTION_MASTER_KEY`

在项目根目录执行：

```powershell
python backend/scripts/generate_master_key.py
```

把输出值填入 `.env` 的 `ENCRYPTION_MASTER_KEY=...`

## 3. `TRONGRID_API_KEY` 是否必须

- 离线地址管理（生成/导入/标签/导出）不依赖该 key
- 联网余额同步与归集任务强烈建议配置该 key
- 未配置可能触发公共限流（429），导致归集失败

## 4. 功能联网要求

- 可断网使用：地址生成、地址导入、标签管理、导出
- 必须联网：余额同步、TRX/USDT 归集、链上状态查询

## 5. 常见问题

### 5.1 启动时报权限错误（PowerShell 执行策略）

不要执行 `activate`，直接使用：

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5.2 报 `429 Too Many Requests`

1. 检查 `.env` 是否填写 `TRONGRID_API_KEY`
2. 重启服务
3. 再次尝试同步或归集

### 5.3 页面没变化

浏览器按 `Ctrl + F5` 强制刷新缓存。

