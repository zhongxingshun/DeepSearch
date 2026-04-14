# Natural-Language Request Examples

Use these examples to map user intent to DeepSearch API actions.

## Search

- 搜索 akuvox 相关的图片
- 搜索最近上传的 logo 压缩包
- 帮我找一下文件名里带 S560 的 PNG
- 搜索 PDF 文件里提到门口机的内容
- 按时间倒序搜索产品三视图
- 查一下有哪些 rar 文件
- 给我 akuvox 的热门搜索词
- 找我最近搜索过的内容

## File Listing and Inspection

- 列出 `/市场营销部素材库/通用/LOGO` 下面的文件
- 看一下这个文件夹里有哪些子文件夹
- 查这个文件的详情
- 这个文件有没有源链接
- 这个文件的 `file_id` 是多少
- 帮我看一下这个文件现在是什么处理状态

## Upload and Retry

- 上传这个文件到 `/市场营销部素材库/通用/LOGO`
- 把这个压缩包上传到产品素材目录
- 批量上传这些图片到当前文件夹
- 重试这个失败的文件
- 把所有失败的文件重新处理一遍

## File Mutations

- 把这个文件重命名为 `S560-R-主图.png`
- 把这个文件移动到 `/市场营销部素材库/Akuvox/产品三视图`
- 删除这个文件
- 批量删除这 5 个文件
- 清空这个文件的源链接
- 把这个文件的源链接改成 https://example.com/source.png

## Share Link Workflows

- 给这个文件生成一个短链接
- 把这张图的分享下载地址给我
- 如果没有短链接就创建一个
- 复制这个文件的短链接
- 让别人也能直接下载这个文件
- 把这个文件的分享链接失效掉
- 帮我把搜索结果里第一张图的短链接拿出来
- 找到最新的产品图，然后把分享短链接发我

## Folder Operations

- 新建一个 `/市场营销部素材库/通用/品牌规范` 文件夹
- 把 `LOGO` 文件夹重命名为 `品牌LOGO`
- 删除 `/市场营销部素材库/通用/旧素材`
- 先告诉我删除这个文件夹会影响多少文件，再决定删不删
- 查看 `/市场营销部素材库` 下一级有哪些文件夹

## Source Link Workflows

- 给这个文件设置源链接
- 这个图片有没有原图链接
- 复制这个文件的源链接
- 把搜索结果里这张图的源链接改掉
- 把这个文件的源链接清空

## Admin and User Management

- 列出所有用户
- 创建一个普通用户，用户名是 alice
- 把 bob 提升为管理员
- 把 admin 提升为超级管理员
- 禁用这个用户
- 重置这个用户的密码
- 查一下最近谁删除过文件
- 看下系统统计信息

## Multi-Step Requests

- 搜索 akuvox 的图片，然后把第一张结果的源链接改成这个地址
- 先列出 `/市场营销部素材库/通用` 下的文件，再把 logo.png 移动到品牌目录
- 看一下这个文件夹准备删除时会删多少文件，如果不多于 20 个就直接删
- 找出失败文件并逐个重试
- 搜索带 S560 的文件，把最新的一份下载链接给我
- 先搜索门口机图片，再把第一条结果的短链接给我
- 列出这个目录里的文件，并把每个文件的分享链接都查出来

## Good Follow-Up Behavior

When the user refers to “这个文件” or “第一条结果”, resolve the target from current context before calling a mutation endpoint.

When the request starts from search results and later needs editing or share-link generation, use `file_id` from the search result, or fetch `GET /files/{id}` first if more context is needed.
