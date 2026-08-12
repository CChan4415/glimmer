# API 端点设计 — Glimmer / 流萤（第一版）

> 状态：**初稿（待拍板）** · 2026-08-12
> 前置依据：[数据模型与隐私设计.md](数据模型与隐私设计.md) §8 端点映射 · [用户故事与验收标准.md](../requirements/用户故事与验收标准.md) · [P0交互细节.md](../requirements/P0交互细节.md)
> 范围：第一版全部 REST 端点，含请求/响应/错误码。认证 token 细节在设计阶段技术栈细化时定。
> 编写方式：按资源分组；每个端点含 URL / Method / Headers / Request Body / 成功响应 / 错误响应；【需决策】点已标出。

---

## 0. 约定

### 0.1 Base URL

```
https://api.glimmer.app/v1
```

### 0.2 通用 Headers

| Header | 值 | 说明 |
| --- | --- | --- |
| `Authorization` | `Bearer <access_token>` | 除 `/auth/*` 外所有端点必带 |
| `Content-Type` | `application/json` | POST/PUT 请求 |
| `Accept` | `application/json` | |

### 0.3 通用错误码

| HTTP 状态码 | 语义 | 响应体格式 |
| --- | --- | --- |
| 400 | 请求参数错误 | `{ "error": { "code": "INVALID_PARAM", "message": "..." } }` |
| 401 | 未认证 / token 过期 | `{ "error": { "code": "UNAUTHORIZED", "message": "请重新登录" } }` |
| 403 | 无权限（访问了非本人的资源） | `{ "error": { "code": "FORBIDDEN", "message": "..." } }` |
| 404 | 资源不存在 | `{ "error": { "code": "NOT_FOUND", "message": "..." } }` |
| 429 | 速率限制 | `{ "error": { "code": "RATE_LIMITED", "message": "请求过于频繁，请稍后再试" } }` |
| 500 | 服务端错误 | `{ "error": { "code": "INTERNAL", "message": "服务暂不可用，请稍后重试" } }` |

### 0.4 分页约定

列表类端点统一使用 cursor-based 分页：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `limit` | int | 每页条数，默认 50，最大 200 |
| `cursor` | string | 上一页最后一条的 id，首页不传 |

响应体：

```json
{
  "data": [ ... ],
  "pagination": {
    "next_cursor": "uuid-of-last-item",
    "has_more": true
  }
}
```

---

## 1. 认证 `/auth`

### 1.1 发送验证码

```
POST /auth/send-code
```

**Request Body**：
```json
{
  "phone": "+8613800138000"
}
```

**成功响应** `200`：
```json
{
  "data": {
    "expires_in": 300,
    "retry_after": 60
  }
}
```

**错误**：
| 状态码 | code | 说明 |
| --- | --- | --- |
| 429 | RATE_LIMITED | 60s 内重复请求 / 单日超 20 条 |
| 400 | INVALID_PHONE | 手机号格式无效 |

---

### 1.2 验证码登录

```
POST /auth/verify
```

**Request Body**：
```json
{
  "phone": "+8613800138000",
  "code": "123456"
}
```

**成功响应** `200`：
```json
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "expires_in": 604800,
    "user": {
      "id": "uuid",
      "nickname": null,
      "is_new": true
    }
  }
}
```

`is_new: true` 时客户端触发引导流程；`false` 直接进入首页。

**错误**：
| 状态码 | code | 说明 |
| --- | --- | --- |
| 400 | INVALID_CODE | 验证码错误 |
| 400 | CODE_EXPIRED | 验证码已过期 |
| 429 | CODE_LOCKED | 连续错误 5 次，锁定 10 分钟 |

---

### 1.3 第三方登录（微信 / Apple）

```
POST /auth/oauth
```

**Request Body**：
```json
{
  "provider": "wechat",
  "code": "oauth-authorization-code",
  "state": "csrf-state"
}
```

**成功响应** `200`：同 1.2（含 token + user 信息）。

**错误**：
| 状态码 | code | 说明 |
| --- | --- | --- |
| 400 | OAUTH_FAILED | 授权失败（code 无效 / 已过期） |
| 409 | BINDING_CONFLICT | 该微信/Apple 已绑定其他账号 → 提示用户解绑或选择主账号 |

---

### 1.4 刷新 token

```
POST /auth/refresh
```

**Request Body**：
```json
{
  "refresh_token": "eyJ..."
}
```

**成功响应** `200`：同 1.2（仅 token 字段，不含 user）。

---

### 1.5 退出登录

```
POST /auth/logout
```

**Request Body**：空（或 `{ "refresh_token": "eyJ..." }` 精确撤销）。

**成功响应** `204`（无 body）。

---

### 1.6 绑定第三方登录

```
POST /auth/bind
```

**Headers**：需已登录（含 access_token）。

**Request Body**：
```json
{
  "provider": "wechat",
  "code": "oauth-authorization-code"
}
```

**成功响应** `200`：
```json
{
  "data": {
    "bound_methods": ["phone", "wechat"]
  }
}
```

**错误**：
| 状态码 | code | 说明 |
| --- | --- | --- |
| 409 | ALREADY_BOUND | 该微信已绑定其他账号（需先解绑） |
| 400 | ALREADY_BOUND_THIS | 当前账号已绑定该方式 |

---

### 1.7 解绑第三方登录

```
DELETE /auth/bind/:provider
```

**成功响应** `204`。

> 至少保留一种登录方式（手机号不可解绑，见 D-2）。

---

## 2. 通讯录导入 `/me/contacts`

### 2.1 批量导入联系人

```
POST /me/contacts/batch
```

**Request Body**：
```json
{
  "contacts": [
    {
      "name": "张三",
      "phone": "+8613900139001",
      "group": "colleague"
    },
    {
      "name": "李四",
      "phone": null,
      "group": "ungrouped"
    }
  ]
}
```

- `phone` 为 null 时，联系人有姓名无手机号（D-1 纯手动导入）。
- 服务端对每条 `phone` 做 `HMAC-SHA256(phone, salt)` → 写入 `contacts.phone_hash`。
- 最大单次 500 条（超量分批，见 D-3）。

**成功响应** `200`：
```json
{
  "data": {
    "imported": 128,
    "skipped": 3,
    "skipped_reason": "duplicate",
    "summary": {
      "family": 10,
      "colleague": 52,
      "friend": 60,
      "ungrouped": 6
    }
  }
}
```

**错误**：
| 状态码 | code | 说明 |
| --- | --- | --- |
| 400 | INVALID_BODY | contacts 数组为空或格式错误 |
| 413 | TOO_LARGE | 单次超过上限（500 条），客户端应分批 |
| 429 | RATE_LIMITED | 导入频率过高 |

---

### 2.2 获取我的联系人列表

```
GET /me/contacts?limit=50&cursor=xxx&group=colleague
```

可选 Query：`group` 筛选、`tag` 筛选。

**成功响应** `200`：
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "张三",
      "phone_hash": "abc123...",
      "group": "colleague",
      "is_manual": false,
      "tags": ["AI", "创业"],
      "last_contacted_at": "2026-06-15T00:00:00Z",
      "matched_user": {
        "id": "uuid",
        "nickname": "张同学"
      },
      "created_at": "2026-08-10T12:00:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "uuid",
    "has_more": true
  }
}
```

`matched_user` 不为 null 表示该联系人已注册（可展开 2 度）；null 表示未注册。

---

### 2.3 获取单个联系人详情

```
GET /me/contacts/:id
```

**成功响应** `200`：同列表项单条，增加完整 `tags` 数组。

**错误**：404（不是我的联系人）。

---

### 2.4 手动新增联系人

```
POST /me/contacts
```

**Request Body**：
```json
{
  "name": "王五",
  "phone": "+8613900139005",
  "group": "friend",
  "tags": ["骑行", "摄影"]
}
```

**成功响应** `201`：返回新联系人完整对象（同详情）。

---

### 2.5 编辑联系人

```
PUT /me/contacts/:id
```

**Request Body**：部分字段可传（部分更新）。

```json
{
  "name": "张三（大学）",
  "group": "friend",
  "tags": ["AI", "创业", "设计"]
}
```

**成功响应** `200`：返回更新后的完整对象。

---

### 2.6 删除联系人

```
DELETE /me/contacts/:id
```

**成功响应** `204`。

---

## 3. 2 度关系浏览 `/me/network`

### 3.1 获取我的已注册 1 度联系人（可展开列表）

```
GET /me/network/first-degree
```

> 相比 `GET /me/contacts` 只返回**已注册**的联系人。2 度浏览功能的前置步骤。

**成功响应** `200`：
```json
{
  "data": [
    {
      "contact_id": "uuid",
      "name": "张三",
      "group": "colleague",
      "matched_user": {
        "id": "uuid",
        "nickname": "张同学",
        "display_level": "pseudonym_only"
      }
    }
  ]
}
```

---

### 3.2 展开某联系人的 2 度（核心 API）

```
GET /me/network/second-degree/:contact_id?limit=50&cursor=xxx
```

**成功响应** `200`：
```json
{
  "data": [
    {
      "id": "uuid",
      "display_name": "陈同学",
      "group": "friend",
      "mutual_count": 2,
      "is_registered": true
    },
    {
      "id": "uuid",
      "display_name": "新朋友",
      "group": "ungrouped",
      "mutual_count": 1,
      "is_registered": false
    }
  ],
  "meta": {
    "source_contact": {
      "id": "uuid",
      "display_name": "张同学"
    },
    "total": 42
  },
  "pagination": {
    "next_cursor": "uuid",
    "has_more": true
  }
}
```

**字段说明**：
| 字段 | 说明 |
| --- | --- |
| `display_name` | **化名**——绝不返回真实姓名。规则见数据模型文档 §6 |
| `group` | 仅当目标用户设置 `display_level = pseudonym_with_group` 时才返回；否则为 null |
| `mutual_count` | 共同好友数（搜索者还有多少其他 1 度也认识此人） |
| `is_registered` | true = 已注册（可进一步展开其 2 度）；false = 未注册（不可展开） |

**错误**：
| 状态码 | code | 说明 |
| --- | --- | --- |
| 404 | NOT_FOUND | contact_id 不存在或不是我的联系人 |
| 403 | PRIVACY_BLOCKED | 中间人或目标关闭了隐私开关 → 返回空列表 + 提示"对方设置了隐私保护" |
| 403 | NOT_REGISTERED | 该联系人未注册，无法展开其 2 度 |
| 403 | NO_REGISTERED_CONTACTS | 1 度已注册联系人数为 0 → 引导邀请朋友 |

---

## 4. 关系图数据 `/me/graph`

### 4.1 获取关系图数据（含统计）

```
GET /me/graph
```

> 比 `GET /me/contacts` 轻量——仅返回图的节点+边所需字段，不含手机号哈希等敏感字段。

**成功响应** `200`：
```json
{
  "data": {
    "nodes": [
      {
        "id": "uuid",
        "name": "张三",
        "group": "colleague",
        "is_registered": true,
        "is_matched": true,
        "display_name": "张同学",
        "tags": ["AI"],
        "degree": 1
      },
      {
        "id": "uuid",
        "name": "陈同学",
        "group": "friend",
        "is_registered": true,
        "is_matched": false,
        "display_name": "陈同学",
        "tags": null,
        "degree": 2
      }
    ],
    "edges": [
      {"from": "me", "to": "uuid-of-zhangsan"},
      {"from": "uuid-of-zhangsan", "to": "uuid-of-chen"}
    ],
    "stats": {
      "total_contacts": 128,
      "family": 10,
      "colleague": 52,
      "friend": 60,
      "ungrouped": 6,
      "by_tag": {
        "AI": 15,
        "创业": 8,
        "骑行": 12
      }
    }
  }
}
```

**字段说明**：
| 字段 | 说明 |
| --- | --- |
| `degree` | 1 = 我的直接联系人；2 = 朋友的朋友（仅当已在图中展开时返回） |
| `is_matched` | 该节点是否是"我自己"（`matched_user.id == me`）——用于"我出现在朋友网络中"的视图 |
| `name` | **仅 degree=1 时返回真实姓名**；degree=2 时此字段为 null |
| `display_name` | 化名——对外展示用，源数据来自数据模型文档 §6 规则 |
| `stats` | 按分组 + 按前 10 标签的聚合统计 |

> 此端点结合 3.2 实现：关系图首页一次性返回 1 度节点 + 已缓存的 2 度节点 + 统计，前端按需展开 2 度时调 3.2 增量加载。

---

## 5. 隐私设置 `/me/privacy`

### 5.1 查看隐私设置

```
GET /me/privacy
```

**成功响应** `200`：
```json
{
  "data": {
    "allow_contacts_visible": true,
    "allow_appear_in_network": true,
    "display_level": "pseudonym_only",
    "nickname": "张同学"
  }
}
```

---

### 5.2 更新隐私设置

```
PUT /me/privacy
```

**Request Body**：
```json
{
  "allow_contacts_visible": true,
  "allow_appear_in_network": true,
  "display_level": "pseudonym_with_group"
}
```

**成功响应** `200`：同 5.1。

**错误**：
| 状态码 | code | 说明 |
| --- | --- | --- |
| 400 | INVALID_PARAM | display_level 值无效 |

---

### 5.3 更新昵称

```
PUT /me/nickname
```

**Request Body**：
```json
{
  "nickname": "小明"
}
```

**成功响应** `200`：返回更新后的昵称。

> 化名生成优先级：nickname（用户主动设）> 自动生成规则（姓氏+朋友）> "新朋友"。后端在返回 display_name 时自动应用此优先级。

---

## 6. 账号管理 `/me/account`

### 6.1 获取账号信息

```
GET /me/account
```

**成功响应** `200`：
```json
{
  "data": {
    "id": "uuid",
    "phone": "+86138****8000",
    "auth_methods": ["phone", "wechat"],
    "created_at": "2026-08-10T12:00:00Z"
  }
}
```

---

### 6.2 导出数据

```
POST /me/export
```

**成功响应** `202`：
```json
{
  "data": {
    "export_id": "uuid",
    "status": "processing",
    "estimated_ready_at": "2026-08-13T12:00:00Z"
  }
}
```

> 异步处理；生成 CSV 文件后通知用户下载。`GET /me/export/:id` 查询状态。

---

### 6.3 删除账号

```
DELETE /me/account
```

**Request Body**：
```json
{
  "confirmation": "DELETE"
}
```

**成功响应** `202`：
```json
{
  "data": {
    "deleted_at": "2026-09-11T12:00:00Z",
    "message": "账号已标记删除，30 天内可撤销。到期后数据将彻底清除。"
  }
}
```

---

### 6.4 撤销删除

```
POST /me/account/restore
```

**成功响应** `200`：
```json
{
  "data": {
    "message": "账号已恢复。"
  }
}
```

> 仅在 30 天冷静期内有效。

---

## 7. 标签 `/tags`

### 7.1 获取预设标签库

```
GET /tags/presets
```

**成功响应** `200`：
```json
{
  "data": [
    { "tag": "骑行", "category": "兴趣" },
    { "tag": "摄影", "category": "兴趣" },
    { "tag": "AI", "category": "职业" },
    { "tag": "程序员", "category": "职业" },
    { "tag": "留学生", "category": "生活" }
  ]
}
```

> 预设标签库来自 `tag_presets` 表，用于前端标签选择器展示。用户自定义标签通过联系人编辑接口直接写入 `contact_tags`，不修改预设库。

---

## 8. 端点汇总

| # | 端点 | 方法 | 认证 | 说明 |
| --- | --- | --- | --- | --- |
| 1.1 | `/auth/send-code` | POST | 无 | 发送验证码 |
| 1.2 | `/auth/verify` | POST | 无 | 验证码登录/注册 |
| 1.3 | `/auth/oauth` | POST | 无 | 微信/Apple 登录 |
| 1.4 | `/auth/refresh` | POST | 无 | 刷新 access token |
| 1.5 | `/auth/logout` | POST | 有 | 退出登录 |
| 1.6 | `/auth/bind` | POST | 有 | 绑定第三方登录 |
| 1.7 | `/auth/bind/:provider` | DELETE | 有 | 解绑第三方登录 |
| 2.1 | `/me/contacts/batch` | POST | 有 | 批量导入联系人 |
| 2.2 | `/me/contacts` | GET | 有 | 联系人列表（分页/筛选） |
| 2.3 | `/me/contacts/:id` | GET | 有 | 联系人详情 |
| 2.4 | `/me/contacts` | POST | 有 | 手动新增联系人 |
| 2.5 | `/me/contacts/:id` | PUT | 有 | 编辑联系人 |
| 2.6 | `/me/contacts/:id` | DELETE | 有 | 删除联系人 |
| 3.1 | `/me/network/first-degree` | GET | 有 | 已注册 1 度列表 |
| 3.2 | `/me/network/second-degree/:contact_id` | GET | 有 | **展开 2 度（核心）** |
| 4.1 | `/me/graph` | GET | 有 | 关系图数据（含统计） |
| 5.1 | `/me/privacy` | GET | 有 | 查看隐私设置 |
| 5.2 | `/me/privacy` | PUT | 有 | 更新隐私设置 |
| 5.3 | `/me/nickname` | PUT | 有 | 更新昵称 |
| 6.1 | `/me/account` | GET | 有 | 账号信息 |
| 6.2 | `/me/export` | POST | 有 | 导出数据（异步） |
| 6.3 | `/me/account` | DELETE | 有 | 删除账号 |
| 6.4 | `/me/account/restore` | POST | 有 | 撤销删除 |
| 7.1 | `/tags/presets` | GET | 无 | 获取预设标签库 |

---

## 9. 决策记录（本文档）

| # | 决策点 | 决定 | 日期 |
| --- | --- | --- | --- |
| D-1 | CSRF 保护策略 | 不设独立 CSRF token；移动端 Bearer token 免疫，Web SameSite=Strict | 2026-08-12 |
| D-2 | 手机号不可解绑 | 手机号不可解绑（主账号）；微信/Apple 可解绑但至少保留一种 | 2026-08-12 |
| D-3 | 批量导入上限 | 500 条/次 | 2026-08-12 |
| D-4 | graph 2 度策略 | 仅返回已展开 2 度；完整 2 度走 3.2 增量加载 | 2026-08-12 |

---

> 下一篇产出：《UI 信息架构》（客户端页面层级 + 主要页面线框草图）。
