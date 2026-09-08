# JWT 集成说明（客户端 / ingest 服务 → chat & auth）

本服务（backend2）签发并校验 JWT。ingest 服务或其他后端若需代表用户调用受保护接口，或前端登录后携带同一 token，请按下列约定对接。

## 算法与密钥

| 项 | 值 |
|----|----|
| Algorithm | `HS256` |
| Shared secret | 环境变量 `JWT_SECRET`（两端必须一致） |
| Algorithm env | `JWT_ALGORITHM=HS256`（可选；默认 HS256） |
| Expiry | `JWT_EXPIRE_MINUTES`（默认 1440） |

`.env.example` 中的键：

```
JWT_SECRET=change-me-to-a-long-random-string
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

**禁止**将真实密钥提交进仓库。

## Claims

| Claim | 含义 |
|-------|------|
| `sub` | `user_id`（字符串） |
| `tenant_id` | 租户 ID（字符串，强制） |
| `iat` / `exp` | 标准签发/过期时间 |

示例 payload（解码后）：

```json
{
  "sub": "user-uuid-or-id",
  "tenant_id": "tenant-acme",
  "iat": 1710000000,
  "exp": 1710086400
}
```

## 请求头

所有受保护路由（`/auth/me`、`/sessions*`、`/chat*`）必须同时带：

```
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

- `X-Tenant-Id` 在 OpenAPI 中为 **required**
- 缺头 → `422`（FastAPI 校验）；空值 → `400`（业务校验）。对接文档写 **400/422**，勿硬写死单一码
- 与 JWT `tenant_id` 不一致 → `403`
- 缺 Bearer / 无效 token → `401`

公开路由（无需 JWT）：`POST /auth/register`、`POST /auth/login`、`GET /health`。

## ingest 服务 / 其他后端对接

1. 与本服务共用同一 `JWT_SECRET` / `JWT_ALGORITHM`（同一部署密钥源）。
2. 入库 / 检索请求若需用户上下文：转发前端的 `Authorization` + `X-Tenant-Id`，或自行用相同密钥签发含 `sub` + `tenant_id` 的 token。
3. Qdrant payload 的 `tenant_id` 必须与 JWT / `X-Tenant-Id` 一致，避免跨租户泄漏。
4. 本地调试可用本服务 `POST /api/v1/auth/login` 拿 `access_token`，再调 ingest 或其他受保护接口验证。

## 校验伪代码

```python
from jose import jwt

payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
user_id = payload["sub"]
tenant_id = payload["tenant_id"]
assert header_x_tenant_id == tenant_id
```

签发逻辑参考本服务：`app/core/security.py`（`create_access_token` / `decode_access_token`）。
