# MCP 调用流程

服务：`https://mcp.mcd.cn`，Streamable HTTP，`Authorization: Bearer <MCP Token>`（在 open.mcd.cn/mcp 登录后申请）。限流 600 次/分钟。工具名可能被宿主加前缀，按语义匹配；参数以宿主拿到的 inputSchema 为准，不猜编码。

## 节气一餐

| 步骤 | 工具 | 说明 |
|---|---|---|
| 1 时间 | `now-time-info` | 作为 `solar_term.py --now` 的输入，避免本机时钟偏差 |
| 2 门店 | `query-nearby-stores`（到店 beType=1，得来速 5）/ `delivery-query-addresses` + `delivery-query-stores`（外送） | 拿 storeCode、beCode、营业时间 |
| 3 活动 | `campaign-calendar`（当天；如节气交节日不同，再查交节日） | 只采用当前有效、适用该门店/渠道的活动 |
| 4 优惠 | `query-store-coupons`；用户关心个人券时 `query-my-coupons` | 不默认领券 |
| 5 菜单 | `query-meals`，套餐用 `query-meal-detail` 展开组件 | 当前版本不支持套餐内换品，按可选轮次如实组合 |
| 6 营养 | `list-nutrition-foods` | 按品名逐项匹配组件；匹配不上标为未知 |
| 7 核价 | `calculate-price` | 每份最终候选都要试算，记录 queried_at |
| 8 排序 | `scripts/pairing.py` | 本地硬约束 + 节气风味打分 |
| 9 卡片 | `scripts/card.py` | 生成 SVG |

## 节气日历

`solar_term.py --now` → 下个节气交节日 → `campaign-calendar(specifiedDate=交节日期)`。该工具返回指定日期前后约三天的活动，只列出覆盖交节日的条目。

## 仅在用户明确要求时

`auto-bind-coupons`（领券后重新 `calculate-price`）、`create-order`（取餐需要试算返回的 takeWayCode；生成订单后由用户自行支付）、`query-order`（下单失败或超时先查状态，不盲目重试）、积分商城相关工具。

## 联调记录

记录日期、客户端、调用的工具、成功/失败、脱敏后的关键结果。不提交 Token、手机号、精确地址、券码、订单号。
