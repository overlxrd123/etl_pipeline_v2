"""
数据质量检查 — 自定义验证器
"""
import pandas as pd
from typing import Callable


def check_not_null(df: pd.DataFrame, column: str) -> dict:
    """检查列是否有空值"""
    null_count = df[column].isna().sum()
    return {
        "check": "not_null",
        "column": column,
        "passed": null_count == 0,
        "details": f"{null_count} nulls out of {len(df)} rows",
    }


def check_unique(df: pd.DataFrame, column: str) -> dict:
    """检查列是否唯一"""
    dup_count = df[column].duplicated().sum()
    return {
        "check": "unique",
        "column": column,
        "passed": dup_count == 0,
        "details": f"{dup_count} duplicates out of {len(df)} rows",
    }


def check_positive(df: pd.DataFrame, column: str) -> dict:
    """检查数值列是否全为正"""
    neg_count = (df[column] <= 0).sum()
    return {
        "check": "positive",
        "column": column,
        "passed": neg_count == 0,
        "details": f"{neg_count} non-positive values out of {len(df)} rows",
    }


def check_range(df: pd.DataFrame, column: str, lo: float, hi: float) -> dict:
    """检查数值列是否在范围内"""
    out_of_range = ((df[column] < lo) | (df[column] > hi)).sum()
    return {
        "check": "range",
        "column": column,
        "passed": out_of_range == 0,
        "details": f"{out_of_range} values outside [{lo}, {hi}]",
    }


def run_all_checks(df: pd.DataFrame, checks: list[dict]) -> list[dict]:
    """
    批量运行检查。
    checks 格式: [{"type": "not_null", "column": "col1"}, ...]
    """
    results = []
    type_map: dict[str, Callable] = {
        "not_null": lambda c: check_not_null(df, c),
        "unique":   lambda c: check_unique(df, c),
        "positive": lambda c: check_positive(df, c),
    }

    for check in checks:
        ctype = check["type"]
        col = check["column"]

        if ctype in type_map:
            result = type_map[ctype](col)
        elif ctype == "range":
            result = check_range(df, col, check["lo"], check["hi"])
        else:
            result = {"check": ctype, "column": col, "passed": False, "details": "unknown check type"}

        results.append(result)

    return results


def print_check_results(results: list[dict]):
    """打印检查结果"""
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    for r in results:
        symbol = "✅" if r["passed"] else "❌"
        print(f"  {symbol} [{r['check']}] {r['column']}: {r['details']}")
    print(f"\n  通过: {passed}/{total}")
