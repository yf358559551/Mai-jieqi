# 本地数据契约（pairing.py 输入）

这是 skill 内部的归一化格式，不是官方 MCP 接口格式。助手调用真实 MCP 后，把返回值整理成下面的 JSON 再运行脚本。输入与输出可能含个人偏好，放在私有临时目录，不提交仓库。

## 顶层

| 字段 | 必填 | 说明 |
|---|---|---|
| demo | 否 | 模拟数据必须为 true；只有 true 才能用 `--demo-now` 固定时钟 |
| term | 否 | 指定节气名（如“霜降”）；省略则按当前时间计算 |
| feelings | 否 | 体感数组，取值：怕冷、怕热、想清淡、怕油腻、想扛饿、嘴馋想甜、没胃口、想提神。未知值会出现在 `feelings_unknown`，不影响排序 |
| budget_yuan | 否 | 实付上限（元），超出即排除 |
| kcal_max | 否 | 整份热量上限；设置后营养不完整的候选会被排除 |
| avoid | 否 | 忌口标签数组，命中即排除 |
| require_full_meal | 否 | 默认 true，要求候选构成完整一餐 |
| candidates | 是 | 候选数组 |

## 候选

```json
{
  "id": "唯一ID", "name": "展示名",
  "available": true, "meal_complete": true,
  "items": [{"id": "规格ID", "name": "品名", "quantity": 1, "tags": ["热饮"], "kcal": 160, "protein_g": 8, "fat_g": 7}],
  "quote": {"total_yuan": 32.5, "verified": true, "all_fees_included": true,
            "store_id": "门店编码", "channel": "pickup|delivery", "queried_at": "带时区ISO", "expires_at": "可选"},
  "activity": {"name": "活动名", "verified": true, "starts_at": "可选", "ends_at": "带时区ISO"}
}
```

- 套餐展开成最终选定的组件；营养为**每份**数值，脚本乘数量汇总，未知填 null，不按 0 计算。
- `quote.verified=true` 只能来自本次 `calculate-price` 成功返回；`total_yuan` 是整单实付。
- `activity` 只有核验了门店/渠道适用和有效期才写 `verified=true`；过期或未开始的活动不加分。

## 输出

`term`（名称、物候、民俗、交节时间、第几天）、`next_term`、`pick`、最多两个 `alternatives`、`rejected`（逐条原因）、`disclaimer`。`--format md` 输出可直接发给用户的文字版；`card.py` 读取 JSON 输出生成卡片。
