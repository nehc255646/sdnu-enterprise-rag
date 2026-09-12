# frontend · Docker Compose 接入

## 产物

- `frontend/Dockerfile`（多阶段：Node 构建 → nginx:alpine）
- `frontend/nginx.conf`：静态资源 + 反代 `/api/` → `http://backend:8000/api/`（SSE：`proxy_buffering off`；上传：`client_max_body_size 20m`）

## 建议服务片段

```yaml
frontend:
  build: ./frontend
  ports:
    - "127.0.0.1:5173:80"   # 或 "127.0.0.1:80:80"
  depends_on:
    - backend
```

浏览器只访问前端端口；构建期用相对路径 `/api`，勿把 `VITE_API` 写成容器内 hostname。

Demo 租户默认 `sdnu-demo`。
