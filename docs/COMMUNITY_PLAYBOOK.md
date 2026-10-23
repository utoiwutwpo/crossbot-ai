# CrossBot AI — 社群投放手册（免费 GPSR 体检钩子）

> 原则：先给价值（免费体检），再谈产品。每个帖子都自带可用价值，不硬广。
> 落地链接规范见文末 UTM 表。**发帖前先自己跑一遍体检，截图放帖子里，转化率翻倍。**

## 一、投放矩阵与优先级

| 优先级 | 社群 | 语言 | 落地页 | 为什么 |
|--------|------|------|--------|--------|
| 🥇 | Allegro 波兰卖家 FB 群 / forum | 波兰语 | `/gpsr-check/pl` | 中国卖家渗透低、GPSR 工具最缺、竞争最小 |
| 🥇 | eMAG 罗马尼亚卖家群 FB/Telegram | 罗马尼亚语 | `/gpsr-check/ro` | 同上；eMAG 审核本来就严 |
| 🥈 | Reddit r/AmazonSeller | 英语 | `/gpsr-check` | 流量大，但 GPSR 话题要挂在「EU expansion」下 |
| 🥈 | 知无不言（www.zhiwuyan.com） | 中文 | `/gpsr-check` | 中国跨境卖家主阵地，欧洲站卖家集中 |
| 🥉 | 卖家精灵社区/公众号投稿 | 中文 | `/gpsr-check` | 有投稿渠道，工具类内容接受度高 |

## 二、发帖模板

### 1. Reddit r/AmazonSeller（英语，纯价值贴）

标题：`PSA: GPSR has been enforceable for 2 years now — quick checklist so your EU listings don't get pulled`

正文要点：
- 先列 GPSR 三大下架触发项（欧代/当地语言警示/CE 标识），一条链接都不放
- 结尾放：`I built a free checker for this (no shop connection needed): <链接>`，声明是自己做的
- ⚠️ Reddit 反广告氛围浓：先参与讨论 1-2 周，用账号 karma；被删帖就换 r/ecommerce / r/FulfillmentByAmazon

### 2. 知无不言 / 卖家精灵社区（中文）

标题：`欧洲站卖家自查：GPSR 强制执行后，你的 listing 缺这 3 样会被下架（附免费自检工具）`

正文骨架：
1. 真实案例开场（某卖家因缺波兰语警示语被 Allegro 下架，损失旺季流量）
2. GPSR 三大触发项逐条讲清「查什么、在哪查」
3. 自检步骤截图（用 `/gpsr-check` 跑一个真实例子，打码关键信息）
4. 文末一句工具链接 + 「免费版只报问题，付费才出修复，不放代码不放盗版」

### 3. Allegro 波兰卖家群（波兰语）

标题：`Darmowy audyt GPSR w 30 sekund — sprawdź, czy Twoja oferta nie zostanie usunięta`

正文骨架：
- GPSR 三触发项（przedstawiciel UE / ostrzeżenia po polsku / oznakowanie CE）
- 强调工具支持 Allegro（波兰语警示语已内置）：`Narzędzie obsługuje Allegro — ostrzeżenia po polsku generowane automatycznie`
- 链接固定发 `/gpsr-check/pl`；每周最多发 1 次，换案例角度

### 4. eMAG 罗马尼亚卖家群（罗马尼亚语）

标题：`Audit GPSR gratuit în 30 de secunde — verifică înainte să-ți șteargă eMAG anunțul`

正文骨架：
- eMAG 审核严是共识，开场直接戳：`eMAG respinge anunțurile lipsite de câmpurile obligatorii — GPSR adaugă încă 3 cerințe`
- 链接固定发 `/gpsr-check/ro`
- 可加一句：`Funcționează și pentru Allegro/Amazon, fără conectarea magazinului`

## 三、UTM 规范（每个渠道独立参数，便于归因）

```
https://<域名>/gpsr-check?utm_source=reddit&utm_campaign=gpsr_launch
https://<域名>/gpsr-check?utm_source=zhiwuyan&utm_campaign=gpsr_launch
https://<域名>/gpsr-check?utm_source=sellersprite&utm_campaign=gpsr_launch
https://<域名>/gpsr-check/pl?utm_source=allegro_fb&utm_campaign=gpsr_launch
https://<域名>/gpsr-check/ro?utm_source=emag_fb&utm_campaign=gpsr_launch
```

衡量指标（周报口径）：
- 访问 → 注册转化率（目标 >25%，体检钩子应远高于普通工具页）
- 注册 → 免费体检完成率（目标 >60%）
- 高风险报告占比（>40% 说明选对了社群；过低说明帖子没打中 CE 类目卖家）
- 免费版看到付费钩子 → 升级点击率（目标 >8%）

## 四、合规与避坑

1. **不制造虚假恐惧**：帖子里的事实以 EU 2023/988 官方文本为准，产品页已带免责声明（工程辅助建议，非法律意见）
2. **不承诺合规结果**：话术统一用「体检报告/自检」，不说「保证不下架」
3. **不留存用户产品数据**：落地页已声明「报告仅自查用」；后端只存标题/关键词与报告，勿扩存联系方式外的个人信息
4. **社群规则优先**：Facebook 群先看群规是否禁工具帖；禁则改用「问答帖」形式（回答他人 GPSR 问题自然带出）
5. **ASIN 数据边界**：ASIN 仅作记录关联，报告判定基于标题/关键词——对外宣传不得声称「自动抓取 Amazon 数据」（SP-API 接入后再说）

## 五、执行节奏（第 1 周）

| 天 | 动作 |
|----|------|
| D1-D2 | 部署上线（Railway），三个落地页可公网访问，UTM 就位 |
| D3 | 中文帖发知无不言 + 卖家精灵社区；自己跑 5 个真实产品体检截图备用 |
| D4-D5 | 英语帖发 Reddit（先挂价值贴）；波兰/罗马尼亚帖找当地卖家朋友或机翻+母语者校对后发 |
| D6-D7 | 看首周数据：哪个渠道注册转化 >25% 就加倍投入，<5% 的换素材或放弃 |
