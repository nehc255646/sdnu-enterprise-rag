# frontend · compose 接入说明（给 @计划）

## 产物

- `frontend/Dockerfile`（多阶段：Node 构建 → nginx:alpine）
- `frontend/nginx.conf`：静态资源 + 反代
  - `/ingest-api/` → `http://backend1:8001/`
  - `/chat-api/` → `http://backend2:8002/`（SSE：`proxy_buffering off`）

## 建议服务片段

```yaml
frontend:
  build: ./frontend
  ports:
    - "5173:80"   # 或 "80:80"
  depends_on:
    - backend1
    - backend2
```

浏览器只访问前端端口；构建期用相对路径 `/ingest-api`、`/chat-api`，勿把 `VITE_*` 写成容器内 hostname。

Demo 租户默认 `sdnu-demo`。
