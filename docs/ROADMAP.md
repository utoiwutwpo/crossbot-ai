# CrossBot AI — 上线路线图

> 对应《上线收费完整方案》Week 1-4 流程。当前 MVP（v0.1）已完成开发与测试，
> 以下为从本仓库到「第一个付费客户」的剩余动作清单。

## 阶段 0：代码入库（当天）

```bash
cd D:\Claude\crossbot-ai
git init && git add -A && git commit -m "CrossBot AI MVP v0.1"
# GitHub 建私有仓库 crossbot-ai 后：
git remote add origin https://github.com/<你>/crossbot-ai.git
git push -u origin main
```

## 阶段 1：云端资源开通（Day 1，全部有免费额度）

| 资源 | 用途 | 地址 |
|------|------|------|
| Railway / Render | 后端部署 | railway.app |
| Supabase | PostgreSQL 数据库 | supabase.com |
| Vercel（可选） | 未来 Next.js 前端 | vercel.com |
| Stripe | 订阅收款 | dashboard.stripe.com |
| 智谱 AI | GLM-4 LLM | open.bigmodel.cn |
| Namecheap/Cloudflare | 域名（crossbot.ai 等） | — |

## 阶段 2：部署（Day 2-3）

1. Railway 新建项目 → 关联 GitHub 仓库 → 使用 `deploy/railway.toml`
2. Supabase 建 `crossbot` 库 → 拿到连接串 → Railway 设环境变量：
   - `DATABASE_URL=postgresql://...`
   - `LLM_API_KEY=...`、`JWT_SECRET=<随机64位>`
   - `CORS_ORIGINS=https://你的域名`
3. 后端容器自动建表（`init_db`），健康检查 `/health` 通过即上线

## 阶段 3：Stripe 生产收费（Day 3-5）

- [ ] Stripe 建 3 个 Price（29/79/199 USD 月订阅），把 Price ID 写入环境变量
- [ ] 实现 `routers/billing.py` 中的生产路径：Checkout Session + webhook
      （`invoice.paid` → 升级、`customer.subscription.deleted` → 降级 free）
- [ ] webhook secret → `STRIPE_WEBHOOK_SECRET`
- [ ] 测试模式跑通一整笔订阅 + 取消

## 阶段 4：冷启动获客（Week 2-4）

按《上线收费方案》第四部分执行：
1. Reddit 软推广（r/AmazonFBA、r/Shopify）：真实案例 + 免费试用链接
2. Facebook 跨境卖家群组（10-20 个）价值分享
3. YouTube 教程短视频 ×3
4. 找 5-10 个跨境卖家内测 → 首月 8 折转付费

## 里程碑

| 时点 | 目标 |
|------|------|
| Week 4 | 第 1 个付费客户 |
| Week 8 | 10 个付费（MRR $790） |
| Week 12 | 50 个付费（MRR $3,950）→ 盈亏平衡（23 个即打平） |
| Month 6 | 欧洲德语区 + 印度英语版（11 语言矩阵已内建） |
