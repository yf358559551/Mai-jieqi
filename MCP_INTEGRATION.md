# 麦·节气 MCP 集成说明

服务：麦当劳中国 MCP Server，`https://mcp.mcd.cn`，Streamable HTTP，客户端私有 Bearer Token。

## 集成方式

本项目是由宿主 AI 助手编排 MCP 调用的 Skill，不内置额外的 HTTP 客户端。助手按 `SKILL.md` 调用麦当劳 MCP，把返回值归一化后交给本地脚本：`solar_term.py` 计算节气，`pairing.py` 做硬约束过滤与节气风味排序，`card.py` 生成分享卡片。脚本不联网，不构造菜单或价格。

## 使用的工具

| 环节 | 工具 | 用途 | 业务价值 |
|---|---|---|---|
| 时间 | `now-time-info` | 取服务端当前时间，计算节气 | 节气与活动判断用同一时钟 |
| 门店 | `query-nearby-stores`、`delivery-query-addresses`、`delivery-query-stores` | 到店/得来速/外送门店 | 推荐只针对用户实际能去的门店 |
| 活动 | `campaign-calendar` | 当天与节气交节日的营销活动 | 把节气节点与真实活动对上，节气日历预告 |
| 优惠 | `query-store-coupons`、`query-my-coupons` | 门店可用券、用户已有券 | 节气餐也能算上划算的优惠 |
| 菜单 | `query-meals`、`query-meal-detail` | 门店在售餐品与套餐组成 | 风味标签基于真实在售品 |
| 营养 | `list-nutrition-foods` | 热量、蛋白质、脂肪等 | 热量档位、蛋白标签、热量上限 |
| 核价 | `calculate-price` | 每份候选试算实付 | 卡片上的价格是真实试算结果 |
| 可选 | `auto-bind-coupons`、`create-order`、`query-order` | 用户明确要求时领券、下单、查单 | 推荐到下单的完整链路，默认不触发 |

## 调用顺序

`now-time-info` → `solar_term.py` → 门店查询 → `campaign-calendar` + `query-store-coupons` → `query-meals` / `query-meal-detail` → `list-nutrition-foods` → 组 4–8 份候选 → 逐份 `calculate-price` → `pairing.py` → 输出推荐 → 问一个体感问题 → 重新排序 → `card.py`。

节气日历：`solar_term.py` 得出下个交节日 → `campaign-calendar(specifiedDate=交节日)` → 列出覆盖该日的活动。

## 当前状态

- 已完成：节气计算（与公开历书对照）、24 节气数据、风味排序、硬约束过滤、卡片生成、离线模拟演示与自动化测试。
- 待完成：用真实 Token 按上述顺序做一次完整联调，并把脱敏结果记入下方。示例卡片和 `examples/demo.json` 均为模拟数据。

## 联调记录

| 日期 | 客户端 | 工具 | 结果（脱敏摘要） |
|---|---|---|---|
| 待填写 | | | |

不记录 Token、手机号、精确地址、券码或订单号。
