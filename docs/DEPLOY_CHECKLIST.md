# 上线执行清单（Launch Checklist）

> 状态标记：✅ 已由代码完成 · 🔑 需要你的凭据/账号操作
> 本清单按顺序执行，预计凭据齐全后 **60 分钟内**可全部完成。

## 0. 已由代码完成的部分（无需再开发）

| 项 | 状态 | 说明 |
|---|---|---|
| Railway 部署配置 | ✅ | `deploy/Dockerfile`（$PORT 自适应 + healthcheck）+ `deploy/railway.toml` |
| Stripe Checkout 生产集成 | ✅ | `POST /api/v1/billing/subscription` 有 Key 时返回支付链接；`POST /api/v1/billing/webhook` 自动开通/降级/欠费标记 |
| Stripe 本地联调模式 | ✅ | 无 Key 时保留本地模拟升降级（演示不断） |
| .env 模板 | ✅ | `backend/.env.example` 全部变量带注释 |
| 属性树 / 客服红线层 / GPSR / 监控 | ✅ | v0.3 + Phase 1 已上线（93/93 测试） |

## 1. 🔑 GitHub 推送（需要你：GitHub 账号 + Personal Access Token）

1. GitHub → Settings → Developer settings → Personal access tokens (classic) → Generate new token，勾选 `repo` 权限
2. 把 token 发我，或自己执行：
   ```bash
   cd D:/Claude/crossbot-ai
   git remote add origin https://github.com/<你的用户名>/crossbot-ai.git
   git push -u origin main
   ```
3. 建议在 GitHub 仓库描述里放 `https://<域名>/skills`（开源引流入口）

## 2. 🔑 Railway 部署（需要你：Railway 账号，可用 GitHub 登录）

1. railway.com → New Project → Deploy from GitHub repo → 选 `crossbot-ai`
2. Railway 自动识别 `deploy/railway.toml`（Dockerfile 构建）
3. Variables 里粘贴环境变量（见 §5 汇总）
4. Settings → Networking → Generate Domain → 得到公网 `https://xxx.up.railway.app`
5. 验证：打开 `https://xxx.up.railway.app/health` 返回 `{"status":"healthy"}`

> ⚠️ 注意：SQLite 在容器重建后数据会丢。MVP 阶段可接受（注册用户少时）；
> 上量后 Railway 挂 Volume 或迁 Postgres（告诉我一声我来改连接串）。

## 3. 🔑 智谱 Key（需要你：open.bigmodel.cn 注册 → API Keys）

1. 注册/登录智谱开放平台 → 创建 API Key
2. 先本地验证再上线（对应方案里「先验证 PL/RO 真实质量」）：
   - 把 Key 告诉我 → 我设置 `LLM_API_KEY` 后跑 `tools/verify_quality.py`
   - 该脚本对 PL/RO/DE/TikTok 四组用例做真实生成 + 评分，输出质量报告
   - 质量达标 → 写入 Railway Variables 上线；不达标 → 先调 prompt 再上线
3. 没有真实 Key 期间全站 Mock 模式可用，但生成质量不是真实 LLM 水平

## 4. 🔑 Stripe 收款（需要你：Stripe 账号，注册免费）

1. dashboard.stripe.com → 注册（可只做测试模式先跑通）
2. **创建产品与价格**（Products → Add product，三个 monthly recurring 价格）：
   - Starter：€29/月 → 复制 price_id（`price_...`）
   - Pro：€79/月 → price_id
   - Business：€199/月 → price_id
3. **创建 Webhook 端点**（Developers → Webhooks → Add endpoint）：
   - URL：`https://<你的域名>/api/v1/billing/webhook`
   - 事件勾选：`checkout.session.completed`、`customer.subscription.deleted`、`invoice.payment_failed`
   - 复制 Signing secret（`whsec_...`）
4. 复制 Secret key（`sk_live_...` 或测试模式 `sk_test_...`）
5. 把 `sk_... / whsec_... / 三个 price_id` 发我或按 §5 填入

## 5. 🔑 环境变量汇总（Railway Variables + 本地 .env）

```
LLM_API_KEY=智谱 Key
GOOGLE_CLIENT_ID=（Google 登录用，可选）
ADMIN_TOKEN=自定义管理令串
STRIPE_SECRET_KEY=sk_test_xxx / sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRICE_BUSINESS=price_xxx
SMTP_HOST=（可选，风险日报邮件）
SMTP_USER= / SMTP_PASSWORD=
```

## 6. 🔑 社群投放（上线后即可执行）

GitHub/Railway/Stripe 就绪后，按 `docs/COMMUNITY_PLAYBOOK.md`：
- 把落地页链接换成公网域名（`https://xxx.up.railway.app/gpsr-check`）
- 带 UTM 参数发 Reddit r/FulfillmentByAmazon、知无不言、PL/RO 卖家社群
- 开源 Skills 链接单独发（比广告更易被接受）

## 验收标准（全绿 = 上线完成）

- [ ] `https://域名/health` → healthy
- [ ] 公网落地页免注册体检可用（PL/RO 版正常）
- [ ] `tools/verify_quality.py` 真实 LLM 模式 4/4 达标
- [ ] Stripe 测试模式：注册 → 升级 Starter → 跳转 Checkout → webhook 开通成功
- [ ] 工作台登录 → 生成 → 监控 → 日报 全链路公网可用
