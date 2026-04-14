---
name: deepsearch-api-ops
description: Operate the DeepSearch document system through its REST API from natural-language requests. Use when asked to search files, inspect search results, upload/download files, create or copy share links, manage folders, rename or move files, maintain source links, retry processing, or perform admin/user-management actions in this DeepSearch deployment.
---

# DeepSearch API Ops

Use this skill to turn natural-language requests into concrete DeepSearch API operations.

## Quick Start

1. Set or confirm the target base URL.
   Default to `http://192.168.10.65:3200/api/v1` unless the user or repo context points to another deployment.
2. Authenticate before any protected call.
3. Use `scripts/deepsearch_api.py` instead of hand-writing repeated `curl` commands.
4. Read `references/api-reference.md` when you need endpoint details or request shapes.

## Base URL and Auth

Prefer this order:

- Explicit user-provided URL
- `DEEPSEARCH_BASE_URL`
- `http://192.168.10.65:3200/api/v1`

Authenticate with username/password:

```bash
python3 scripts/deepsearch_api.py login \
  --base-url http://192.168.10.65:3200/api/v1 \
  --username <your-username> \
  --password '<your-password>'
```

Or let the script prompt interactively on first use:

```bash
python3 scripts/deepsearch_api.py login \
  --base-url http://192.168.10.65:3200/api/v1
```

The script caches tokens under `~/.cache/deepsearch-api-ops/` per base URL after login succeeds.

Notes:

- `--base-url` can be placed before the subcommand or after it
- repeat `--query key=value` for multiple query parameters

## Workflow

### 1. Identify the intent

Map the user request to one of these common actions:

- Search: search keywords, filter by type, sort
- File read actions: list files, get file details, preview URL, download URL
- File share actions: get share link, create share link, revoke share link, provide public download URL
- File write actions: upload, rename, move, delete, retry
- Folder actions: create, rename, delete, inspect delete impact
- Source-link actions: view, copy target value, set, clear
- Admin actions: list users, create user, set role, enable/disable user, reset password

### 2. Check privilege level

Treat these as admin-only unless the API reference says otherwise:

- Folder create/rename/delete
- File rename/move/delete
- Source-link write
- Retry processing
- Admin user management

If the request is destructive and the user intent is ambiguous, pause and confirm. If the user clearly asked for the action, proceed.

### 3. Choose the narrowest API call

Examples:

- “搜索 akuvox 图片” -> `GET /search?q=akuvox&file_type=image`
- “把 logo.png 的源链接改成 xxx” -> `PUT /files/{id}/source-url`
- “给我这个文件的短链接” -> `GET /files/{id}/share-link?ensure=true`
- “删除 /市场营销部素材库/通用/LOGO” -> `GET /files/folders/delete-summary` then `DELETE /files/folders`
- “把 admin 提升成超级管理员” -> `PUT /admin/users/{id}/role`

### 4. Prefer structured output back to the user

When reporting results, summarize the important fields instead of dumping raw JSON.

Good examples:

- “找到 23 个结果，其中 18 个是图片，最新一条是 …”
- “文件已移动到 `/市场营销部素材库/LOGO`”
- “源链接已更新，并已同步到当前预览记录”

## Preferred Tooling

### General API call

```bash
python3 scripts/deepsearch_api.py call \
  --base-url http://192.168.10.65:3200/api/v1 \
  --method GET \
  --path /files \
  --query page=1 \
  --query page_size=20
```

### JSON write call

```bash
python3 scripts/deepsearch_api.py call \
  --method PUT \
  --path /files/123/source-url \
  --json '{"source_url":"https://example.com/original.png"}'
```

### Single-file upload

```bash
python3 scripts/deepsearch_api.py upload \
  --file /absolute/path/to/file.png \
  --folder-path /市场营销部素材库/通用/LOGO
```

## Natural-Language Mapping

### Search and discovery

Use:

- `GET /search`
- `POST /search/suggest`
- `GET /history`
- `GET /history/popular/global`

Important detail:

- Search results include `file_id`, and file list rows include `id`; in practice both refer to the file primary key used by file APIs.
- Search results may not contain all file-management fields needed for follow-up mutations. If the user asks to edit source link, create a share link, or perform another file-management action after search, fetch file details with `GET /files/{id}` when needed.

### File operations

Use:

- `GET /files`
- `GET /files/{id}`
- `POST /files/upload`
- `POST /files/upload/batch`
- `PUT /files/{id}/rename`
- `PUT /files/{id}/move`
- `PUT /files/{id}/source-url`
- `POST /files/{id}/retry`
- `DELETE /files/{id}`
- `POST /files/batch-delete`

### Share-link operations

Use:

- `GET /files/{id}/share-link?ensure=true` to fetch or auto-create a share link
- `POST /files/{id}/share-link` to create or refresh a share link with explicit expiry
- `DELETE /files/{id}/share-link/{share_id}` to revoke a link
- `GET /s/{code}` as the public anonymous download URL

Important detail:

- `/s/{code}` is not under `/api/v1`
- The public URL usually comes from `data.short_url`
- In this deployment, public links usually resolve under `http://192.168.10.65:3200/s/{code}` unless the user specifies another host
- When the user wants “the download link” for sharing, prefer returning the share link rather than the authenticated `/files/{id}/download` URL

### Folder operations

Use:

- `GET /files/folders/tree`
- `POST /files/folders`
- `PUT /files/folders/rename`
- `GET /files/folders/delete-summary`
- `DELETE /files/folders`

Recommended delete flow:

1. Fetch delete summary first.
2. Tell the user how many files/folders will be removed if this was not already explicit.
3. Execute delete.

### Source-link operations

Use a single source-link concept everywhere.

- Read source link from file details or file list rows
- Write source link with `PUT /files/{id}/source-url`
- Clear source link by sending `{"source_url": null}`

### Admin operations

Use:

- `GET /admin/users`
- `POST /admin/users`
- `PUT /admin/users/{id}/role`
- `PUT /admin/users/{id}/status`
- `POST /admin/users/{id}/reset-password`
- `GET /admin/logs`
- `GET /admin/stats`

Role rules in this project:

- `super_admin` can manage admins and roles
- `admin` can access backend management but should not manage other admins’ privileges
- admins cannot disable themselves

## Use the Reference File

Open `references/api-reference.md` when you need:

- exact endpoints
- request body shapes
- admin permission boundaries
- DeepSearch-specific quirks such as archive search, source-link behavior, or folder deletion flow

## Example Requests

Open `references/natural-language-examples.md` when you want example user phrasing or need to map conversational requests to concrete API actions quickly.

Typical examples covered there:

- keyword search and filtered search
- upload, retry, rename, move, delete
- share-link fetch, copy, revoke, and share-download workflows
- folder create, rename, delete, and impact checks
- source-link set, clear, copy, and search-to-edit workflows
- admin user-management requests

## Failure Handling

If an API request fails:

1. Report the HTTP status and the `detail` or `message` field.
2. Distinguish auth failure, permission failure, validation failure, and server failure.
3. For user-facing summaries, explain the likely cause in plain language.

Examples:

- `401`: token expired, bad password, or locked account
- `403`: current role cannot perform this admin action
- `400`: invalid payload or protected self-action
- `500`: backend or schema mismatch; surface the exact detail when present
