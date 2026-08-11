"""
日期工具 — 生成日期维度数据 & 日期计算
"""
from datetime import date, timedelta
from calendar import month_name, day_name, isleap


def generate_date_dimension(start: date, end: date) -> list[dict]:
    """
    生成日期维度数据，每条记录对应一天。
    包含年/季/月/周/是否周末/财年等字段。
    """
    rows = []
    current = start
    while current <= end:
        rows.append({
            "date_id":      int(current.strftime("%Y%m%d")),
            "full_date":    current,
            "year":         current.year,
            "quarter":      (current.month - 1) // 3 + 1,
            "month":        current.month,
            "day":          current.day,
            "day_of_week":  current.weekday(),        # 0=Mon
            "day_of_year":  current.timetuple().tm_yday,
            "week_of_year": current.isocalendar()[1],
            "is_weekend":   current.weekday() >= 5,
            "is_holiday":   False,
            "month_name":   month_name[current.month],
            "day_name":     day_name[current.weekday()],
            "fiscal_year":  current.year if current.month < 7 else current.year + 1,
            "fiscal_quarter": ((current.month + 5) // 3) % 4 + 1,
        })
        current += timedelta(days=1)
    return rows
