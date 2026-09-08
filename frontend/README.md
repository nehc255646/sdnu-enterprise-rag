# SDNU Enterprise RAG — Frontend

React + TypeScript + Vite + Ant Design。

## 启动

```bash
cd frontend
cp .env.example .env
npm i
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`。

Demo 租户：`sdnu-demo`（登录/注册表单默认填这个）。

## 代理

| 前缀 | 目标 |
|------|------|
| `/ingest-api` | `http://127.0.0.1:8001`（ingest 服务） |
| `/chat-api` | `http://127.0.0.1:8002`（chat 服务） |

也可在 `.env` 设置 `VITE_INGEST_API` / `VITE_CHAT_API` 直连。

## 安全说明

JWT 目前存在浏览器 `localStorage`，XSS 场景可被窃取。当前 Demo 可接受；生产环境建议改为 HttpOnly Cookie + CSRF 防护，或短期内存令牌。
