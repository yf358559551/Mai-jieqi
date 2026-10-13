#!/usr/bin/env python3
"""按节气风味 + 用户体感，对已核价的候选餐进行筛选和排序（仅标准库，不联网）。

输入格式见 references/data-contract.md。脚本不构造菜单、不证明价格或活动有效，
所有候选与报价都必须来自本次真实 MCP 返回（demo=true 的模拟数据除外）。
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import solar_term  # noqa: E402

PROTEIN_TAG_G = 20  # 整份候选蛋白质 ≥ 20g 时自动打“蛋白”标签
DISCLAIMER = "节气风味搭配，仅供点餐参考，不是养生、营养或医疗建议；价格与活动以下单页为准。"


def kcal_band(kcal):
    if kcal is None:
        return "未知"
    if kcal <= 500:
        return "较低"
    if kcal <= 800:
        return "中等"
    return "较高"


def _parse_time(text, field):
    if not text:
        return None
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError(f"{field} 缺少时区：{text}")
    return dt


def _sum(items, key):
    total = 0.0
    for it in items:
        v = it.get(key)
        if v is None:
            return None
        total += float(v) * int(it.get("quantity", 1))
    return round(total, 1)


def build_weights(term, feelings, data):
    weights, unknown, soft_caps = {}, [], []
    for src in (term["prefer"], term["less"]):
        for tag, w in src.items():
            weights[tag] = weights.get(tag, 0) + w
    for f in feelings:
        spec = data["feelings"].get(f)
        if spec is None:
            unknown.append(f)
            continue
        for tag, w in spec["weights"].items():
            weights[tag] = weights.get(tag, 0) + w
        if spec.get("kcal_soft_cap"):
            soft_caps.append(spec["kcal_soft_cap"])
    return weights, unknown, (min(soft_caps) if soft_caps else None)


def evaluate(cand, req, now):
    """返回 (summary, reasons_rejected)。"""
    items = cand.get("items") or []
    quote = cand.get("quote") or {}
    reasons = []
    if not items:
        reasons.append("没有餐品明细")
    if cand.get("available") is not True:
        reasons.append("未确认可售")
    if req.get("require_full_meal", True) and cand.get("meal_complete") is not True:
        reasons.append("不构成完整一餐")
    if quote.get("verified") is not True:
        reasons.append("价格未经试算")
    if quote.get("all_fees_included") is not True:
        reasons.append("未确认已含配送等必要费用")
    total = quote.get("total_yuan")
    if total is None:
        reasons.append("缺少实付金额")
    budget = req.get("budget_yuan")
    if budget is not None and total is not None and float(total) > float(budget) + 1e-9:
        reasons.append(f"超出预算（¥{float(total):.1f} > ¥{float(budget):.1f}）")
    expires = _parse_time(quote.get("expires_at"), "quote.expires_at")
    if expires and expires < now:
        reasons.append("报价或优惠已过期")

    tags = set()
    for it in items:
        tags.update(it.get("tags") or [])
    protein = _sum(items, "protein_g")
    if protein is not None and protein >= PROTEIN_TAG_G:
        tags.add("蛋白")
    hit_avoid = sorted(tags & set(req.get("avoid") or []))
    if hit_avoid:
        reasons.append("含忌口：" + "、".join(hit_avoid))

    kcal = _sum(items, "kcal")
    kcal_max = req.get("kcal_max")
    if kcal_max is not None:
        if kcal is None:
            reasons.append("热量数据不完整，不能判断是否在上限内")
        elif kcal > kcal_max:
            reasons.append(f"热量超出上限（{kcal:.0f} > {kcal_max} kcal）")

    activity = cand.get("activity")
    activity_ok = False
    if activity:
        starts = _parse_time(activity.get("starts_at"), "activity.starts_at")
        ends = _parse_time(activity.get("ends_at"), "activity.ends_at")
        activity_ok = (activity.get("verified") is True and ends is not None and ends >= now
                       and (starts is None or starts <= now))

    summary = {
        "id": cand.get("id"),
        "name": cand.get("name"),
        "items": [{"name": it.get("name"), "quantity": int(it.get("quantity", 1)), "tags": list(it.get("tags") or [])}
                  for it in items],
        "total_yuan": None if total is None else round(float(total), 2),
        "kcal": kcal,
        "kcal_band": kcal_band(kcal),
        "protein_g": protein,
        "tags": sorted(tags),
        "activity": (activity or {}).get("name") if activity_ok else None,
        "activity_ends_at": (activity or {}).get("ends_at") if activity_ok else None,
        "queried_at": quote.get("queried_at"),
        "store_id": quote.get("store_id"),
        "channel": quote.get("channel"),
    }
    return summary, reasons


def score(summary, weights, req, soft_cap):
    s = 0.0
    matched = []
    for tag in summary["tags"]:
        w = weights.get(tag, 0)
        s += w
        if w > 0:
            matched.append((w, tag))
    if summary["activity"]:
        s += 1.0
    budget = req.get("budget_yuan")
    if budget and summary["total_yuan"] is not None:
        s += 0.5 * (1 - summary["total_yuan"] / float(budget))
    if soft_cap and summary["kcal"] is not None and summary["kcal"] > soft_cap:
        s -= (summary["kcal"] - soft_cap) / 200.0
    matched.sort(key=lambda x: -x[0])
    return round(s, 3), [t for _, t in matched]


def reason_text(term, matched, data, summary):
    phrases = [data["tag_phrases"][t] for t in matched if t in data["tag_phrases"]][:3]
    text = f"{term['name']}，{term['climate']}"
    if phrases:
        text += "，这份有" + "、".join(phrases)
    else:
        text += "，这份在已核验候选中最贴近你的要求"
    if summary["activity"]:
        text += f"，还赶上「{summary['activity']}」"
    return text + "。"


def recommend(req, now=None):
    data = solar_term.load_data()
    if now is None:
        now = datetime.now(solar_term.BJT)
    info = solar_term.current(now, data)
    term_name = req.get("term") or info["term"]["name"]
    term = solar_term.term_by_name(data, term_name)
    if term_name == info["term"]["name"]:
        started, day_index = info["term"]["started_at"], info["term"]["day_index"]
    elif term_name == info["next"]["name"]:  # 提前为即将到来的节气配餐
        started, day_index = info["next"]["at"], None
    else:
        started, day_index = None, None
    weights, unknown, soft_cap = build_weights(term, req.get("feelings") or [], data)

    ok, rejected = [], []
    for cand in req.get("candidates") or []:
        summary, reasons = evaluate(cand, req, now)
        if reasons:
            rejected.append({"id": summary["id"], "name": summary["name"], "reasons": reasons})
            continue
        summary["score"], matched = score(summary, weights, req, soft_cap)
        summary["matched_tags"] = matched
        summary["reason"] = reason_text(term, matched, data, summary)
        ok.append(summary)

    ok.sort(key=lambda r: (-r["score"], r["total_yuan"],
                           r["kcal"] if r["kcal"] is not None else 1e9, str(r["id"])))
    demo = bool(req.get("demo"))
    return {
        "demo": demo,
        "label": "模拟数据，不可下单" if demo else None,
        "term": dict({k: term[k] for k in ("name", "pinyin", "season", "hou", "climate", "custom", "line")},
                     started_at=started, day_index=day_index, upcoming=(term_name == info["next"]["name"])),
        "next_term": {"name": info["next"]["name"], "at": info["next"]["at"], "days_until": info["next"]["days_until"]},
        "feelings_used": [f for f in (req.get("feelings") or []) if f not in unknown],
        "feelings_unknown": unknown,
        "pick": ok[0] if ok else None,
        "alternatives": ok[1:3],
        "rejected": rejected,
        "disclaimer": DISCLAIMER,
        "generated_at": now.isoformat(),
    }


def to_markdown(result):
    t = result["term"]
    lines = []
    if result["demo"]:
        lines.append("> ⚠️ 模拟数据，不可下单")
    head = f"**{t['name']}** · {t['season']}"
    if t.get("day_index"):
        head += f" · 第 {t['day_index']} 天"
    lines += [head, "　".join(t["hou"]), ""]
    pick = result["pick"]
    if not pick:
        lines.append("这次核验的候选里没有满足条件的搭配，原因见 rejected。")
    else:
        kcal = "未知" if pick["kcal"] is None else f"约 {pick['kcal']:.0f} kcal"
        lines.append(f"今天更推荐：**{pick['name']}**（¥{pick['total_yuan']:.1f}，{kcal}，热量{pick['kcal_band']}）")
        lines.append("　" + "、".join(f"{i['name']}×{i['quantity']}" for i in pick["items"]))
        lines.append("因为：" + pick["reason"])
        for alt in result["alternatives"]:
            lines.append(f"备选：{alt['name']}（¥{alt['total_yuan']:.1f}，热量{alt['kcal_band']}）")
    lines += ["", f"民俗：{t['custom']}。", f"「{t['line']}」", "", f"_{result['disclaimer']}_"]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description="节气风味搭配排序")
    p.add_argument("input", help="归一化后的候选 JSON")
    p.add_argument("--demo-now", help="仅 demo=true 时可用，固定当前时间（带时区 ISO 8601）")
    p.add_argument("--format", choices=["json", "md"], default="json")
    args = p.parse_args(argv)
    req = json.loads(Path(args.input).read_text(encoding="utf-8"))
    now = None
    if args.demo_now:
        if not req.get("demo"):
            raise SystemExit("--demo-now 只能用于 demo=true 的模拟数据")
        now = solar_term.parse_now(args.demo_now)
    result = recommend(req, now)
    if args.format == "md":
        print(to_markdown(result))
    else:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
