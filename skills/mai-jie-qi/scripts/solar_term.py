#!/usr/bin/env python3
"""计算当前节气与全年节气时刻（仅标准库）。

使用 Meeus《天文算法》低精度太阳视黄经公式，节气时刻误差通常在 30 分钟以内，
足够判断“今天是哪个节气”。临近交节时刻（前后 1 小时）应以权威历书为准。
"""
import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BJT = timezone(timedelta(hours=8))
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "solar_terms.json"


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def term_by_longitude(data, longitude):
    for term in data["terms"]:
        if term["longitude"] == longitude % 360:
            return term
    raise KeyError(longitude)


def term_by_name(data, name):
    for term in data["terms"]:
        if term["name"] == name:
            return term
    raise KeyError(name)


def _julian_day(dt):
    return dt.astimezone(timezone.utc).timestamp() / 86400.0 + 2440587.5


def sun_longitude(dt):
    """太阳视黄经（度）。dt 必须带时区。"""
    jd = _julian_day(dt) + 69.0 / 86400.0  # TT ≈ UT + 69s
    t = (jd - 2451545.0) / 36525.0
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
         + (0.019993 - 0.000101 * t) * math.sin(2 * m)
         + 0.000289 * math.sin(3 * m))
    omega = math.radians(125.04 - 1934.136 * t)
    return (l0 + c - 0.00569 - 0.00478 * math.sin(omega)) % 360.0


def _signed_diff(a, b):
    d = (a - b) % 360.0
    return d - 360.0 if d > 180.0 else d


def crossing(longitude, near):
    """near 附近（±约 20 天）太阳到达 longitude 的时刻，返回北京时间。"""
    est = near + timedelta(days=_signed_diff(longitude, sun_longitude(near)) / 0.9856)
    lo, hi = est - timedelta(days=3), est + timedelta(days=3)
    for _ in range(50):
        mid = lo + (hi - lo) / 2
        if _signed_diff(sun_longitude(mid), longitude) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + (hi - lo) / 2).astimezone(BJT).replace(microsecond=0)


def _public(term):
    return {k: term[k] for k in ("name", "pinyin", "season", "hou", "climate", "custom", "line")}


def current(now, data=None):
    data = data or load_data()
    lon = sun_longitude(now)
    start_lon = int(lon // 15) * 15
    started = crossing(start_lon, now)
    if started > now:  # 浮点边界保护
        start_lon = (start_lon - 15) % 360
        started = crossing(start_lon, now - timedelta(days=1))
    nxt_lon = (start_lon + 15) % 360
    nxt = crossing(nxt_lon, started + timedelta(days=15))
    today = now.astimezone(BJT).date()
    return {
        "now": now.astimezone(BJT).isoformat(),
        "term": dict(_public(term_by_longitude(data, start_lon)), started_at=started.isoformat(),
                     day_index=(today - started.date()).days + 1),
        "next": dict(_public(term_by_longitude(data, nxt_lon)), at=nxt.isoformat(),
                     days_until=(nxt.date() - today).days),
        "near_boundary": min(abs((now - started).total_seconds()), abs((nxt - now).total_seconds())) < 3600,
    }


def year_table(year, data=None):
    data = data or load_data()
    rows = []
    near = datetime(year, 1, 1, tzinfo=BJT)
    lon = (int(sun_longitude(near) // 15) * 15 + 15) % 360
    while True:
        at = crossing(lon, near)
        if at.year > year:
            break
        if at.year == year:
            rows.append({"name": term_by_longitude(data, lon)["name"], "at": at.isoformat()})
        near = at + timedelta(days=15)
        lon = (lon + 15) % 360
    return rows


def parse_now(text):
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise SystemExit("--now 必须带时区，例如 2026-10-23T12:00:00+08:00")
    return dt


def main(argv=None):
    p = argparse.ArgumentParser(description="计算当前节气或全年节气时刻（北京时间）")
    p.add_argument("--now", help="ISO 8601 带时区时间，默认系统当前时间；应优先使用 MCP now-time-info 的返回")
    p.add_argument("--year", type=int, help="输出该年 24 个节气的交节时刻")
    args = p.parse_args(argv)
    if args.year:
        out = year_table(args.year)
    else:
        out = current(parse_now(args.now) if args.now else datetime.now(BJT))
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
