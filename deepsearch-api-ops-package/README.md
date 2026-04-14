# DeepSearch API Ops Skill

这个压缩包用于导入 `deepsearch-api-ops` skill。

导入方式：

1. 解压压缩包
2. 将其中的 `deepsearch-api-ops` 目录复制到：
   - `~/.codex/skills/`
3. 重启或刷新 Codex 会话

首次登录：

- 运行 `login` 时可以直接输入自己的账号密码
- 也可以不带账号密码参数，脚本会交互式提示输入
- 登录成功后 token 会缓存在本机，后续无需重复输入

目录内容：

- `deepsearch-api-ops/SKILL.md`
- `deepsearch-api-ops/agents/openai.yaml`
- `deepsearch-api-ops/references/api-reference.md`
- `deepsearch-api-ops/references/natural-language-examples.md`
- `deepsearch-api-ops/scripts/deepsearch_api.py`

这个 skill 主要用于：

- 用自然语言调用 DeepSearch API
- 搜索文件与查看结果
- 上传、移动、重命名、删除文件
- 管理文件夹
- 设置或清空源链接
- 执行管理员相关操作
