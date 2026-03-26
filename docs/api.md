# DeepSearch API 文档

本文档以当前后端代码实现为准，覆盖 `/api/v1` 下实际可用接口。

在线文档入口：
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

基础信息：
- Base URL: `/api/v1`
- 认证方式: `Authorization: Bearer <access_token>`
- 返回格式:
  - 成功时通常返回 `success / data / message`
  - 校验或业务错误通常返回 `4xx`，错误信息在 `detail`

## 1. 认证 Auth

### `POST /auth/login`
用户登录。

请求体：
```json
{
  "username": "admin",
  "password": "Akuvox123!"
}
```

响应示例：
```json
{
  "access_token": "xxx",
  "refresh_token": "xxx",
  "token_type": "bearer",
  "expires_in": 86400
}
```

说明：
- 连续失败 5 次会锁定 30 分钟
- 登录失败返回 `401`

### `POST /auth/logout`
用户登出，需要登录。

响应示例：
```json
{
  "success": true,
  "message": "登出成功",
  "data": null
}
```

### `POST /auth/refresh`
刷新令牌。当前实现依赖已登录用户上下文。

### `GET /auth/me`
获取当前用户信息。

响应字段：
- `id`
- `username`
- `role`
- `is_active`
- `created_at`
- `updated_at`

### `PUT /auth/password`
修改当前用户密码。

请求体：
```json
{
  "old_password": "OldPass@123",
  "new_password": "NewPass@123"
}
```

规则：
- 新密码至少 8 位
- 需包含大小写字母、数字和特殊字符

## 2. 搜索 Search

### `GET /search`
全文搜索。

查询参数：
- `q`: 必填，关键词
- `page`: 默认 `1`
- `page_size`: 默认 `20`，最大 `100`
- `file_type`: 可选，文件类型过滤
- `sort_by`: 可选，`created_at | file_size`
- `sort_order`: 可选，`asc | desc`，默认 `desc`

响应示例：
```json
{
  "success": true,
  "keyword": "logo",
  "results": [
    {
      "id": "doc_id",
      "file_id": 12,
      "filename": "brand_logo.zip",
      "file_type": "archive",
      "file_size": 102400,
      "file_path": "ab/abcdef.zip",
      "content_snippet": "文件名匹配",
      "score": 0.87,
      "highlights": [],
      "created_at": "2026-03-26T09:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "query_time_ms": 12.3
}
```

说明：
- 支持中文分词
- 支持文件类型筛选与排序
- 压缩包仅建立文件名索引，摘要会返回“文件名匹配”

### `GET /search/{doc_id}`
获取单个索引文档详情。

### `POST /search/suggest`
获取搜索建议。

注意：
- 当前实现是 `POST`
- 参数通过 Query 传入，不是 JSON body

查询参数：
- `q`: 必填
- `limit`: 默认 `5`，最大 `10`

响应示例：
```json
{
  "success": true,
  "query": "lo",
  "suggestions": [
    {
      "keyword": "logo",
      "type": "recent"
    },
    {
      "keyword": "logo pack",
      "type": "popular",
      "count": 8
    }
  ]
}
```

## 3. 搜索历史 History

### `GET /history`
获取当前用户搜索历史。

查询参数：
- `page`
- `page_size`
- `keyword`: 可选，按关键词过滤

### `GET /history/recent`
获取最近搜索历史。

查询参数：
- `limit`: 默认 `10`

### `GET /history/popular`
获取当前用户的热门搜索关键词。

### `GET /history/popular/global`
获取全局热门搜索关键词。

### `DELETE /history/{history_id}`
删除单条搜索历史。

### `DELETE /history`
清空当前用户所有搜索历史。

## 4. 文件 Files

### `POST /files/upload`
上传单个文件，`multipart/form-data`。

表单字段：
- `file`: 必填
- `folder_path`: 可选，目标文件夹路径

响应示例：
```json
{
  "success": true,
  "message": "文件上传成功",
  "file_id": 101,
  "filename": "logo.png",
  "md5_hash": "xxx",
  "is_duplicate": false,
  "task_id": "celery-task-id"
}
```

说明：
- 自动按 MD5 去重
- 支持 `zip / rar`
- 压缩包不解压，只支持文件名搜索

### `POST /files/upload/batch`
批量上传文件，`multipart/form-data`。

表单字段：
- `files`: 多文件

限制：
- 单次最多 10 个文件

返回字段：
- `uploaded_count`
- `duplicate_count`
- `failed_count`
- `results`

### `POST /files/retry-all-failed`
管理员批量重试 `failed / parsed / pending` 文件。

### `GET /files`
获取文件列表。

查询参数：
- `page`
- `page_size`
- `file_type`
- `status`
- `keyword`
- `folder`

单个文件字段：
- `id`
- `filename`
- `file_path`
- `folder_path`
- `display_name`
- `uploaded_by`
- `file_size`
- `file_size_human`
- `file_type`
- `source_url`
- `md5_hash`
- `index_status`
- `created_at`
- `updated_at`

### `GET /files/folders/tree`
获取文件夹树或子文件夹列表。

查询参数：
- `parent`: 可选；不传时返回所有文件夹，传入时返回直接子文件夹

### `POST /files/folders`
管理员创建文件夹。

请求体：
```json
{
  "path": "/市场营销部素材库/通用"
}
```

### `PUT /files/folders/rename`
管理员重命名文件夹。

请求体：
```json
{
  "path": "/市场营销部素材库/通用/LOGO",
  "new_name": "品牌LOGO"
}
```

说明：
- 会同步更新该目录下文件的 `folder_path`
- 会同步更新搜索索引中的目录元数据

### `DELETE /files/folders`
管理员删除文件夹。

查询参数：
- `path`: 必填

说明：
- 当前实现支持删除非空文件夹
- 会递归删除其下文件和子文件夹

### `GET /files/folders/delete-summary`
管理员获取删除文件夹前的影响范围统计。

查询参数：
- `path`

响应示例：
```json
{
  "success": true,
  "message": "获取删除摘要成功",
  "data": {
    "path": "/A/B",
    "file_count": 12,
    "subfolder_count": 3
  }
}
```

### `GET /files/{file_id}`
获取单个文件详情。

### `GET /files/{file_id}/download`
下载文件。

### `GET /files/{file_id}/preview`
预览文件。

说明：
- 图片直接返回图片内容
- PDF 以 `inline` 返回
- 其他文件类型前端一般走“说明 + 下载”模式

### `GET /files/{file_id}/status`
获取文件处理状态。

返回字段：
- `id`
- `filename`
- `index_status`
- `error_message`
- `updated_at`

### `DELETE /files/{file_id}`
管理员删除单个文件。

### `POST /files/batch-delete`
管理员批量删除文件。

请求体：
```json
{
  "file_ids": [1, 2, 3]
}
```

### `GET /files/stats/overview`
获取文件统计概览。

返回字段：
- `total_files`
- `total_size`
- `total_size_human`
- `by_status`
- `by_type`

### `POST /files/{file_id}/retry`
重试单个失败文件。

说明：
- 适用于 `failed` 和 `parsed`
- 会检查源文件是否还存在
- 会重新创建解析任务

### `PUT /files/{file_id}/move`
管理员移动文件到指定文件夹。

请求体：
```json
{
  "target_folder": "/市场营销部素材库/通用"
}
```

### `PUT /files/{file_id}/rename`
管理员重命名单个文件。

请求体：
```json
{
  "filename": "new-logo.png"
}
```

说明：
- 当前实现修改业务文件名，不改底层 MD5 存储文件
- 会同步更新搜索索引中的 `filename`

### `PUT /files/{file_id}/source-url`
管理员设置或清空文件源链接。

请求体：
```json
{
  "source_url": "https://example.com/original-asset"
}
```

清空时：
```json
{
  "source_url": null
}
```

规则：
- 仅接受合法 `http / https` URL

## 5. 管理后台 Admin

该分组默认要求管理员登录；部分操作仅 `super_admin` 可执行。

### `GET /admin/users`
获取用户列表。

### `POST /admin/users`
创建用户。

请求体：
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "Pass@1234",
  "role": "user"
}
```

说明：
- 创建 `admin / super_admin` 需要 `super_admin`

### `PUT /admin/users/{user_id}/status`
启用或禁用用户。

请求体：
```json
{
  "is_active": false
}
```

说明：
- 管理员不能禁用自己
- 普通管理员只能管理普通用户

### `PUT /admin/users/{user_id}/role`
更新用户角色，仅 `super_admin` 可用。

请求体：
```json
{
  "role": "admin"
}
```

### `POST /admin/users/{user_id}/reset-password`
重置用户密码。

说明：
- 当前默认重置为 `deepsearch123`

### `DELETE /admin/users/{user_id}`
删除用户。

说明：
- 不能删除当前登录账号

### `GET /admin/stats`
获取系统统计。

返回字段：
- `user_count`
- `file_count`
- `total_file_size`
- `today_search_count`
- `file_type_distribution`
- `index_status`

### `GET /admin/logs`
获取审计日志。

查询参数：
- `page`
- `page_size`
- `action_type`: 可选

说明：
- 代码当前实际过滤参数名是 `action_type`

### `POST /admin/maintenance/backup`
触发备份任务。

### `POST /admin/maintenance/reindex`
触发重建索引任务。

### `POST /admin/maintenance/cleanup`
触发清理任务。

说明：
- 这三个维护接口当前返回“已触发”状态
- 注释里标记为后续接入异步任务

## 6. 健康检查 Health

### `GET /health`
系统健康状态。

响应示例：
```json
{
  "status": "healthy",
  "timestamp": "2026-03-26T09:19:27.741016Z",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 3.37
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 5.12
    },
    "meilisearch": {
      "status": "healthy",
      "latency_ms": 17.48
    }
  }
}
```

### `GET /health/ready`
服务就绪检查。

### `GET /health/live`
服务存活检查。

## 7. 常见状态码

- `200`: 成功
- `400`: 参数错误或业务校验失败
- `401`: 未登录或令牌无效
- `403`: 权限不足
- `404`: 资源不存在
- `422`: 请求体验证失败

## 8. 当前实现备注

- 文件上传支持去重，重复文件会返回 `is_duplicate = true`
- 压缩包文件类型为 `archive`
- 压缩包不做解压解析，只支持文件名搜索、下载、删除、移动
- `search/suggest` 当前使用 `POST + Query 参数`，这是现实现状
- `admin/logs` 当前过滤参数是 `action_type`，不是 `action`
- 远端部署后如果前端容器显示 `health: starting / unhealthy`，需要结合实际访问和 `/api/v1/health` 一起判断
