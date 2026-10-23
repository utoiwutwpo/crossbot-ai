# CrossBot AI — 跨境电商AI助手

> **定位：欧洲全平台 Listing 质量 + 合规引擎。**
> 文案是入口，GPSR 合规块与 Rufus 语义评分才是付费理由——不和平台官方免费 AI 拼"写文案"。

## 当前状态（v0.3 — 差异化 + 增长闭环）

| 模块 | 状态 | 说明 |
|------|------|------|
| 用户注册/登录（JWT + PBKDF2 + Google 登录） | ✅ 已完成 | 69/69 测试通过 |
| 产品描述生成专家 | ✅ 已完成 | 11 平台规则校验 + 优化评分 + 16 语言 |
| 🛡️ **GPSR 合规引擎（差异化核心）** | ✅ 已完成 | CE 类目识别（7 类规则库）→ 适用指令 → 当地语言警示语 → 法定检查清单 → 可粘贴合规块；免费体检（只报问题）+ 付费解锁合规块 |
| 🌍 **欧洲多平台矩阵** | ✅ 已完成 | 一次产品 → 11 平台（含 Kaufland/bol.com）批量本地化 |
| 🌳 **平台属性树校验（差异化）** | ✅ 已完成 | Allegro/eMAG/TikTok/Kaufland/bol 必填参数校验：EAN 校验位、硬阻断拦截、完整度评分 |
| 🔄 **差评→Listing 闭环（差异化）** | ✅ 已完成 | 粘贴差评 → 8 类主题定位 → 可粘贴五点修复 + 优先级 |
| 🚨 **客服政策安全红线层（差异化）** | ✅ 已完成 | 差评威胁/退款勒索/伤害索赔识别 → 只安抚不承诺 + 强制转人工留证 |
| 📈 **验证闭环埋点** | ✅ 已完成 | landing_view→guest_check→signup→generate→upgrade 漏斗 + UTM 归因 + /analytics/summary |
| 🔍 **Rufus/iZi 语义搜索适配评分** | ✅ 已完成 | 8 类买家高频问题覆盖度检测 → 语义分 + 缺口清单（全网零竞品） |
| AI 客服专家 | ✅ 已完成 | 意图分类 + 情绪检测 + 红线层 + 高风险转人工 |
| 广告文案专家 | ✅ 已完成 | Facebook/Google/TikTok 字数硬校验 |
| 计费与用量闸门 | ✅ 已完成 | 免费版 5 次/天；GPSR 体检永久免费不计数；功能门控 402 |
| 免费体检落地页 | ✅ 已完成 | `/gpsr-check` 中文主站（支持 ASIN）+ `/gpsr-check/pl` 波兰语（Allegro）+ `/gpsr-check/ro` 罗马尼亚语（eMAG）；均带 "No Shopify required" 对比区 |
| 社群投放手册 | ✅ 已完成 | `docs/COMMUNITY_PLAYBOOK.md`：Reddit/知无不言/卖家精灵/Allegro FB 群/eMAG 群四语发帖模板 + UTM 归因 + 合规避坑 |
| 前端单页（中文） | ✅ 已完成 | 由 FastAPI 直接托管，零构建 |
| 订阅升级/取消 | ✅ 本地模拟 | Stripe 生产集成见「上线路线」 |
| 测试 | ✅ 69 用例 | `pytest`，Mock 模式零外部依赖 |
| 质量门禁 | ✅ 已完成 | `tools/verify_quality.py`：配 Key 后跑真实 PL/RO/DE 文案质量检查 |

## 支持的平台（欧洲主打）

| 平台 | 站点 | listing 语言 | 标题上限 |
|------|------|-------------|---------|
| Amazon 欧洲站 | UK/DE/FR/IT/ES/NL/SE/PL/BE | 英语（德国站德语） | 200 |
| eBay | UK/DE/FR/IT/ES | 英语 | 80 |
| Cdiscount | 法国 | 法语 | 120 |
| Otto | 德国 | 德语 | 70 |
| Allegro | 波兰/捷克/匈牙利 | 波兰语 | 75 |
| eMAG | 罗马尼亚/匈牙利/保加利亚 | 罗马尼亚语 | 150 |
| TikTok Shop ⭐ | UK/US + ES/IT/DE/FR 欧盟 | 英语 | 255 |
| Walmart | 美国 | 英语 | 100 |
| Fruugo（泛欧） | 20+ 国 | 英语主目录（平台自动翻译） | 100 |
| Kaufland ⭐ | 德/奥/捷/斯 | 德语 | 150 |
| bol.com ⭐ | 荷兰/比利时 | 荷兰语 | 120 |
| Shopify | 全球 | 按需 | 255 |

> ⭐ **TikTok Shop 为合规增长主打平台**：欧盟站点同样强制 GPSR/CE，合规块自动内嵌；生成内置平台合规红线（禁夸大功效词/绝对化用语/资质类目提示）。

> 规则数值为工程默认值，平台会不定期调整，上架前以各平台卖家中心文档为准（见 `platform_registry.py`）。

## 快速开始（本地，3 分钟）

```bash
cd backend

# Windows (Git Bash)
python -m venv ../.venv
../.venv/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt
../.venv/Scripts/python -m uvicorn app.main:app --port 8000

# 浏览器打开 http://localhost:8000
```

默认 **Mock 模式**（无需任何 API Key 即可跑通全流程）。
接真实 AI：在 `backend/.env` 写入：

```
LLM_API_KEY=你的智谱APIKey        # https://open.bigmodel.cn/
LLM_MODEL=glm-4-plus
JWT_SECRET=换成一个随机长字符串
```

生产换 PostgreSQL：`DATABASE_URL=postgresql://user:pass@host/crossbot`

### Google 登录（Sign up / Log in with Google）

未配置时 `/signin` `/signup` 页的 Google 按钮会给引导提示（不影响邮箱注册登录）。开启步骤：

1. 到 [Google Cloud Console](https://console.cloud.google.com/apis/credentials) 创建 **OAuth 2.0 客户端 ID**（类型：Web 应用）
2. 「已获授权的 JavaScript 来源」填你的站点地址（本地开发填 `http://localhost:8000`）
3. `backend/.env` 写入：`GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com`，重启服务
4. 前端自动加载 Google Identity Services 弹窗；后端 `POST /users/google` 用 Google tokeninfo 服务端校验 `aud`/`email_verified`，同邮箱老账号自动关联，新邮箱自动注册（free 档）

## 目录结构

```
crossbot-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口（托管前端 + /api/v1/*）
│   │   ├── config.py            # 环境变量配置（.env）
│   │   ├── database.py          # SQLAlchemy 模型（用户/描述/客服/广告/用量）
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── auth.py              # JWT + PBKDF2 认证
│   │   ├── billing.py           # 套餐定义 + 用量闸门 + 升降级
│   │   ├── llm.py               # 智谱 GLM-4 客户端（无 Key 自动 Mock 降级）
│   │   ├── experts/             # 三大 AI 专家
│   │   │   ├── product_description.py
│   │   │   ├── customer_service.py
│   │   │   └── ad_copy.py
│   │   ├── routers/             # users / products / customer_service / ads / billing
│   │   └── static/index.html    # 前端单页（中文）
│   └── tests/                   # pytest 验收测试
├── deploy/                      # Dockerfile / railway.toml
├── docs/ROADMAP.md              # 上线路线图（Stripe/部署/获客）
└── README.md
```

## API 一览（/api/v1）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /users/register · /users/login | 注册/登录，返回 JWT |
| GET  | /users/google-config | Google 登录可用性与 Client ID |
| POST | /users/google | Google ID token 登录/注册（自动关联同邮箱账号） |
| GET  | /users/me | 当前用户 |
| POST | /products/gpsr/check | **GPSR 合规体检（免费不计数）**：风险等级+指令+检查清单；付费版含合规块 |
| POST | /products/descriptions/generate | 生成产品描述（平台合规+GPSR 块+语义评分） |
| POST | /products/descriptions/market-matrix | 欧洲多平台矩阵批量生成 |
| GET  | /products/platforms · /products/descriptions | 平台注册表 / 生成历史 |
| POST | /customer-service/messages | 买家咨询 → AI 回复 + 意图/情绪/转人工 |
| POST | /ads/generate | 广告文案（Facebook/Google/TikTok） |
| GET  | /billing/plans · /billing/subscription | 价目表 / 当前订阅与用量 |
| POST/DELETE | /billing/subscription | 升级 / 取消订阅 |
| GET  | /gpsr-check（页面） | 免费 GPSR 体检获客落地页 |
| GET  | /health | 健康检查 |

## 运行测试

```bash
cd backend && ../.venv/Scripts/python -m pytest tests/ -v
```

## 定价（三地差异化，见市场专项分析）

| 套餐 | 全球基准 | 欧洲 | 印度 | 中东 |
|------|---------|------|------|------|
| Starter | $29 | €29 | ₹299 | AED 99 |
| Professional | $79 | €79 | ₹799 | AED 249 |
| Business | $199 | €199 | ₹1,999 | AED 599 |

## 上线路线

见 `docs/ROADMAP.md`。执行顺序（本周→之后）：

1. **推 GitHub**（私有仓起步）：
   ```bash
   cd D:/Claude/crossbot-ai
   git init && git add -A && git commit -m "CrossBot AI v0.2: GPSR compliance + market matrix + semantic score"
   gh repo create crossbot-ai --private --source=. --push
   ```
2. **部署**：Railway（`deploy/railway.toml` 已备）+ Supabase Postgres（`DATABASE_URL`）+ 域名
3. **真实 AI**：`backend/.env` 填智谱 `LLM_API_KEY`，Mock → 真实生成
4. **Stripe 收款**：建 3 档 Price → `billing.py` 补 webhook 生产路径（接口已预留）→ 换掉本地模拟升级
5. **获客验证**：按 `docs/COMMUNITY_PLAYBOOK.md` 执行——优先波兰语/罗马尼亚语社群（`/gpsr-check/pl`、`/gpsr-check/ro`），再打 Reddit/知无不言；每渠道独立 UTM，首周看注册转化率决定投入

## 竞品定位（见 `D:/Claude/跨境电商AI助手_欧洲市场竞品扫描与差异化机会.md`）

- Helium 10（$129/月起）只做 Amazon/Walmart/TikTok，且砍掉了低价档
- Marqetir 覆盖欧洲平台但必须绑 Shopify 店
- 合规工具（hellotax/AVASK）不管 listing、文案工具不管合规
- **没人做 GPSR×Listing 一体化 + Rufus 语义评分 + 不绑店的独立工作台 —— 这三件事是本项目的护城河**
