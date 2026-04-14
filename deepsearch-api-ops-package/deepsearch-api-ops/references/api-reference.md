# DeepSearch API Reference

Use this file when the request needs concrete endpoint details.

## Base

- Base URL: `/api/v1`
- Auth: `Authorization: Bearer <access_token>`
- Error detail usually appears in `detail`
- Public share downloads use `/s/{code}` and are not under `/api/v1`

## Auth

### `POST /auth/login`
Body:
```json
{"username":"admin","password":"Akuvox123!"}
```
Returns `access_token`, `refresh_token`, `token_type`, `expires_in`.

### `GET /auth/me`
Return current user profile and role.

### `PUT /auth/password`
Change current user password.

## Search

### `GET /search`
Query params:
- `q`
- `page`
- `page_size`
- `file_type`
- `sort_by` = `created_at | file_size`
- `sort_order` = `asc | desc`

Notes:
- archives only support filename search
- archive snippets return `文件名匹配`

### `POST /search/suggest`
Query params:
- `q`
- `limit`

## Files

### `GET /files`
Query params:
- `page`
- `page_size`
- `file_type`
- `status`
- `keyword`
- `folder`

File row fields include:
- `id`
- `filename`
- `display_name`
- `folder_path`
- `file_type`
- `file_size`
- `file_size_human`
- `source_url`
- `index_status`
- `created_at`

Notes:
- `id` is the file primary key used by file APIs
- If the request starts from search results, use `result.file_id` for follow-up file actions

### `GET /files/{id}`
Use to fetch full file details before a mutation from search context.

### `POST /files/upload`
Multipart fields:
- `file`
- optional `folder_path`

### `POST /files/upload/batch`
Multipart field:
- repeated `files`

### `PUT /files/{id}/rename`
Body:
```json
{"filename":"new-name.png"}
```

### `PUT /files/{id}/move`
Body:
```json
{"target_folder":"/市场营销部素材库/通用"}
```

### `PUT /files/{id}/source-url`
Body:
```json
{"source_url":"https://example.com/original.png"}
```
Clear with:
```json
{"source_url":null}
```

### `GET /files/{id}/share-link`
Query params:
- `ensure` = `true | false`

Behavior:
- with `ensure=true`, auto-creates a share link if one does not already exist
- without `ensure`, returns the active share link or `404`

Response fields include:
- `id`
- `file_id`
- `filename`
- `code`
- `short_url`
- `download_url`
- `is_active`
- `download_count`
- `max_downloads`
- `expires_at`
- `created_at`

### `POST /files/{id}/share-link`
Body:
```json
{"expires_in_hours":24,"max_downloads":null}
```

Notes:
- `expires_in_hours` is optional; default is 24
- `max_downloads` can be omitted or `null` for unlimited

### `DELETE /files/{id}/share-link/{share_id}`
Revokes a share link.

### `GET /s/{code}`
Anonymous public download endpoint for a share link.

Notes:
- returns file content directly
- does not require auth
- if the link is invalid, expired, revoked, or the backing file is missing, it returns `404`

### `POST /files/{id}/retry`
Retry failed or parsed file processing.

### `DELETE /files/{id}`
Delete a single file. Admin only.

### `POST /files/batch-delete`
Body:
```json
{"file_ids":[1,2,3]}
```

## Folders

### `GET /files/folders/tree`
Optional query param:
- `parent`

### `POST /files/folders`
Body:
```json
{"path":"/市场营销部素材库/通用/LOGO"}
```
Admin only.

### `PUT /files/folders/rename`
Body:
```json
{"path":"/市场营销部素材库/通用/LOGO","new_name":"品牌LOGO"}
```
Admin only.

### `GET /files/folders/delete-summary`
Query param:
- `path`

Use this before delete when the user needs impact details.

### `DELETE /files/folders`
Query param:
- `path`

Current behavior:
- supports deleting non-empty folders
- recursively deletes nested files and child folders
- should usually be treated as high-impact

## Admin

### `GET /admin/users`
List users.

### `POST /admin/users`
Create user.

### `PUT /admin/users/{id}/role`
Change role. `super_admin` only for admin-role management.

### `PUT /admin/users/{id}/status`
Enable or disable user.
Notes:
- cannot disable current logged-in user

### `POST /admin/users/{id}/reset-password`
Reset password.

### `GET /admin/stats`
Get system stats.

### `GET /admin/logs`
Supports filters including `action_type`.

## Project-Specific Behavior

- `zip` and `rar` are supported uploads
- archives are not unpacked or OCR-parsed
- archives support filename search, download, delete, move
- source links are file-level metadata
- share links are file-level public download links
- share links default to 24-hour expiry
- current default deployment returns URLs like `http://192.168.10.65:3200/s/{code}`
- source-link editing is admin-only
- search preview may require an extra `GET /files/{id}` call before editing source link
