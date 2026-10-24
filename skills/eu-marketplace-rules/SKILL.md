---
name: eu-marketplace-rules
description: "欧洲 13 电商平台 Listing 规则库：标题字数上限、必需语言、覆盖国家、GPSR 合规要点、入驻注意事项。覆盖 Amazon EU+US / eBay / Cdiscount / Otto / Allegro / eMAG / Fruugo / Walmart / Kaufland / Zalando / bol.com / TikTok Shop。Use when: seller asks about listing requirements, title character limits, required languages, or listing rules for any European marketplace."
---

# 欧洲 13 平台 Listing 规则库

1. **载入数据**：读取本目录 `data/platforms.json`
   （13 个平台的完整规则：覆盖国家、必需语言、字数限制、合规 notes）。
2. **按平台查询**：用户说平台名（中英文/昵称均可，如 "波兰" → allegro，
   "荷兰" → bol）→ 输出该平台规则卡。
3. **矩阵模式**：用户给一个产品要铺多平台 → 逐平台列出差异点
   （字数/语言/GPSR），标注最容易踩的坑。

## 每个平台输出规则卡

```
📦 <display>（<countries>）
- 提交语言：<language> ｜ 标题 ≤ <title_max> 字符
- 五点 <bullets> 条 ｜ 搜索词 ≤ <search_terms_max>
- 详情页 ≤ <description_max>
- ⚠️ 平台合规要点：
  <notes 逐条>
```

## 高频踩坑点（生成 listing 时必须主动检查）

- **Allegro**：必须波兰语；英语 listing 基本无曝光
- **Otto**：必须德语；德国买家对合规与退货政策极敏感
- **Kaufland**：德/奥/捷/斯洛伐克，德语
- **bol.com**：荷兰语；EAN 是商品唯一键，缺失直接建不了 offer
- **Zalando**：主目录英语提交、平台本地化，但仅限时尚类目且需品牌入驻
  （zDirect）；EAN + 尺码网格 + 材质成分必填；纺织品强制 EU 1007/2011
  纤维成分标签
- **Cdiscount / eMAG**：法语 / 罗马尼亚语
- **Amazon EU**：多国同套 listing 但警示语必须按国家本地化
- **TikTok Shop**：英/德/法/意/西，标题 255 字符，内容电商合规内嵌
- **GPSR**：所有 EU 平台自 2024-12-13 起强制欧代 + 当地语言警示语
  （配合 `gpsr-compliance-checker` Skill 做合规块）

## 免责声明

平台规则随政策变化，本数据版本 2026-10-24；上架前请以各平台
Seller Central / 官方文档最新要求为准。
