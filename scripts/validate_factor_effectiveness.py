#!/usr/bin/env python3
"""
Validate factor effectiveness on a generated feather dataset.

Checks included:
1. Basic dataset stats
2. Near-zero variance factors
3. High-correlation factor pairs
4. Univariate IC against future log returns
5. A greedy de-redundant factor shortlist
6. VP-VAE-friendly recommended feature list
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import polars as pl

ROLLING_WINDOWS = [60, 180, 360]
RELATIVE_WINDOWS = [20, 60, 180, 360]
TREND_BASE_COLUMNS = [
    "ask1_price", "bid1_price",
    "buy_spread", "sell_spread",
    "wap_1", "wap_2",
    "buy_vwap", "sell_vwap",
    "volume",
]

DEFAULT_FEATURE_COLUMNS = [
    "kmid",
    "klen",
    "kmid2",
    "kup",
    "klow",
    "ksft",
    "kup2",
    "klow2",
    "ksft2",
    "volume",
    "bid1_size_n",
    "ask1_size_n",
    "bid2_size_n",
    "ask2_size_n",
    "bid3_size_n",
    "ask3_size_n",
    "bid4_size_n",
    "ask4_size_n",
    "bid5_size_n",
    "ask5_size_n",
    "wap_1",
    "wap_2",
    "wap_balance",
    "buy_spread",
    "sell_spread",
    "price_spread",
    "bid_gap_1_2",
    "bid_gap_2_3",
    "bid_gap_3_4",
    "bid_gap_4_5",
    "ask_gap_1_2",
    "ask_gap_2_3",
    "ask_gap_3_4",
    "ask_gap_4_5",
    "bid_gap_count",
    "max_bid_gap",
    "bid_gap_near_far_ratio",
    "ask_gap_count",
    "max_ask_gap",
    "ask_gap_near_far_ratio",
    "gap_count_diff",
    "max_gap_diff",
    "gap_near_far_ratio_diff",
    "buy_volume",
    "sell_volume",
    "volume_imbalance",
    "imbalance_top1",
    "imbalance_top3",
    "imbalance_top5",
    "weighted_imbalance_inv",
    "bid1_queue_concentration",
    "ask1_queue_concentration",
    "top2_depth_share",
    "trade_volume_delta",
    "turnover_delta",
    "avg_trade_price",
    "avg_trade_price_bias",
    "avg_trade_price_mid_bias",
    "avg_trade_price_bias_change",
    "open_interest_change",
    "open_interest_change_ratio",
    "open_interest_change_per_trade",
    "open_interest_price_link",
    "sell_vwap",
    "buy_vwap",
    "log_return_bid1_price",
    "log_return_bid2_price",
    "log_return_ask1_price",
    "log_return_ask2_price",
    "log_return_wap_1",
    "log_return_wap_2",
    "best_spread_duration",
    "best_quote_duration",
    *[f"log_return_wap_1_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"log_return_wap_2_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"log_return_bid1_price_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"price_spread_vol_{window}" for window in ROLLING_WINDOWS],
    "spread_recovery",
    "bid_gap_recovery",
    "ask_gap_recovery",
    "bid_depth_replenishment",
    "ask_depth_replenishment",
    "depth_replenishment_diff",
    "ofi",
    *[f"ofi_{window}" for window in ROLLING_WINDOWS],
    *[f"ofi_vol_{window}" for window in ROLLING_WINDOWS],
    "bid_depth_slope",
    "ask_depth_slope",
    "bid_book_convexity",
    "ask_book_convexity",
    "depth_slope_diff",
    "book_convexity_diff",
    "imbalance_top3_change",
    "weighted_imbalance_inv_change",
    *[f"ofi_zscore_{window}" for window in ROLLING_WINDOWS],
    "bid_depth_slope_change",
    "ask_depth_slope_change",
    *[f"trade_volume_delta_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"turnover_delta_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"avg_trade_price_bias_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"open_interest_change_vol_{window}" for window in ROLLING_WINDOWS],
    *[f"trade_volume_delta_zscore_{window}" for window in ROLLING_WINDOWS],
    *[f"turnover_delta_zscore_{window}" for window in ROLLING_WINDOWS],
    *[f"avg_trade_price_bias_zscore_{window}" for window in ROLLING_WINDOWS],
    *[f"avg_trade_price_mid_bias_zscore_{window}" for window in ROLLING_WINDOWS],
    *[f"open_interest_change_zscore_{window}" for window in ROLLING_WINDOWS],
    *[f"signed_trade_pressure_{window}" for window in ROLLING_WINDOWS],
    *[f"signed_open_interest_pressure_{window}" for window in ROLLING_WINDOWS],
    *[f"trade_ofi_resonance_{window}" for window in ROLLING_WINDOWS],
    *[f"trade_volume_delta_slope_{window}" for window in ROLLING_WINDOWS],
    *[f"turnover_delta_slope_{window}" for window in ROLLING_WINDOWS],
    *[f"avg_trade_price_bias_slope_{window}" for window in ROLLING_WINDOWS],
    *[f"open_interest_slope_{window}" for window in ROLLING_WINDOWS],
    *[
        f"{col}_trend_{window}"
        for window in ROLLING_WINDOWS
        for col in TREND_BASE_COLUMNS
    ],
    *[
        f"{col}_zscore_{window}"
        for window in RELATIVE_WINDOWS
        for col in [
            "close_price", "wap_1", "wap_2", "bid1_price", "ask1_price", "price_spread"
        ]
    ],
    *[
        f"{col}_ratio_{window}"
        for window in RELATIVE_WINDOWS
        for col in [
            "close_price", "wap_1", "volume",
            "trade_volume_delta", "turnover_delta", "open_interest", "klen"
        ]
    ],
    "vol_regime_ratio_20_60",
    "vol_regime_ratio_60_180",
    "vol_regime_ratio_60_360",
    "volume_regime_ratio_60_360",
    "turnover_regime_ratio_60_360",
    "spread_regime_ratio_60_360",
    "depth_near_share",
    "depth_near_share_zscore_60",
    "depth_near_share_zscore_360",
]


VP_VAE_TARGET_COUNT = 0
VP_VAE_CATEGORY_MINIMUMS = {
    "kline_core": 1,
    "spread": 1,
    "trend": 1,
    "distribution": 1,
    "momentum": 1,
    "stability": 1,
    "order_flow": 1,
    "shape": 1,
    "trade_activity": 1,
}
VP_VAE_CATEGORY_MAXIMUMS = {
    "kline_core": 4,
    "kline_aux": 2,
    "spread": 2,
    "trend": 2,
    "distribution": 2,
    "momentum": 2,
    "stability": 1,
    "order_flow": 2,
    "shape": 3,
    "trade_activity": 2,
}


def _trend_to_zscore_name(feature: str) -> str | None:
    match = re.match(r"^(.+)_trend_(\d+)$", feature)
    if not match:
        return None
    return f"{match.group(1)}_zscore_{match.group(2)}"


def parse_horizons(raw: str) -> list[int]:
    horizons = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        value = int(part)
        if value <= 0:
            raise ValueError(f"invalid horizon: {value}")
        horizons.append(value)
    if not horizons:
        raise ValueError("no valid horizons provided")
    return horizons


def available_feature_columns(df: pl.DataFrame, requested: Iterable[str]) -> list[str]:
    return [col for col in requested if col in df.columns]


def matches_suffix(feature: str, prefix: str) -> bool:
    return any(feature == f"{prefix}_{window}" for window in ROLLING_WINDOWS)


def is_trend_feature(feature: str) -> bool:
    return any(feature.endswith(f"_trend_{window}") for window in ROLLING_WINDOWS)


def feature_category(feature: str) -> str:
    if feature in {"ksft2", "kup2", "klow2", "kmid2", "klen"}:
        return "kline_core"
    if feature in {"ksft", "kup", "klow", "kmid"}:
        return "kline_aux"
    if (
        feature.startswith("trade_volume_delta")
        or feature.startswith("turnover_delta")
        or feature.startswith("avg_trade_price")
        or feature.startswith("open_interest")
        or feature.startswith("signed_trade_pressure")
        or feature.startswith("signed_open_interest_pressure")
        or feature.startswith("trade_ofi_resonance")
    ):
        return "trade_activity"
    if feature.startswith("bid_gap_") or feature.startswith("ask_gap_"):
        return "shape"
    if feature in {
        "bid_gap_count",
        "max_bid_gap",
        "bid_gap_near_far_ratio",
        "ask_gap_count",
        "max_ask_gap",
        "ask_gap_near_far_ratio",
        "gap_count_diff",
        "max_gap_diff",
        "gap_near_far_ratio_diff",
        "depth_slope_diff",
        "book_convexity_diff",
    }:
        return "shape"
    if feature in {"imbalance_top3_change", "weighted_imbalance_inv_change"}:
        return "distribution"
    if (
        feature.startswith("imbalance_top")
        or feature.startswith("weighted_imbalance")
        or feature.endswith("_queue_concentration")
        or feature.endswith("_depth_share")
    ):
        return "distribution"
    if feature in {
        "best_spread_duration",
        "best_quote_duration",
        "spread_recovery",
        "bid_gap_recovery",
        "ask_gap_recovery",
        "bid_depth_replenishment",
        "ask_depth_replenishment",
        "depth_replenishment_diff",
    } or any(
        matches_suffix(feature, prefix)
        for prefix in [
            "log_return_wap_1_vol",
            "log_return_wap_2_vol",
            "log_return_bid1_price_vol",
            "price_spread_vol",
        ]
    ):
        return "stability"
    if feature.startswith("ofi"):
        return "order_flow"
    if "slope" in feature or "convexity" in feature:
        return "shape"
    if "spread" in feature:
        return "trend" if is_trend_feature(feature) else "spread"
    if is_trend_feature(feature):
        return "trend"
    if feature.startswith("log_return_"):
        return "momentum"
    if feature.endswith("_size_n") or feature in {"volume_imbalance", "buy_vwap", "sell_vwap", "volume"}:
        return "distribution"
    if feature.startswith("wap_") or feature in {"wap_balance"}:
        return "price_level"
    return "other"


def feature_preference_score(feature: str) -> int:
    score = 0
    if feature.endswith("2"):
        score += 2
    if is_trend_feature(feature):
        score += 1
    if feature.startswith("log_return_"):
        score += 1
    if feature.endswith("_change"):
        score += 1
    if (
        feature.startswith("trade_volume_delta")
        or feature.startswith("turnover_delta")
        or feature.startswith("avg_trade_price")
        or feature.startswith("open_interest")
        or feature.startswith("signed_trade_pressure")
        or feature.startswith("signed_open_interest_pressure")
        or feature.startswith("trade_ofi_resonance")
    ):
        score += 1
    if feature in {"imbalance_top1", "imbalance_top3", "weighted_imbalance_inv", "top2_depth_share"}:
        score += 1
    if (
        any(matches_suffix(feature, prefix) for prefix in ["ofi", "ofi_zscore", "ofi_vol"])
        or any(
            feature == f"{prefix}_{window}"
            for prefix in ["signed_trade_pressure", "signed_open_interest_pressure", "trade_ofi_resonance"]
            for window in ROLLING_WINDOWS
        )
        or any(
            matches_suffix(feature, prefix)
            for prefix in [
                "trade_volume_delta_zscore",
                "turnover_delta_zscore",
                "avg_trade_price_bias_zscore",
                "avg_trade_price_mid_bias_zscore",
                "open_interest_change_zscore",
                "log_return_wap_1_vol",
                "log_return_wap_2_vol",
                "log_return_bid1_price_vol",
                "price_spread_vol",
            ]
        )
    ):
        score += 2
    if (
        "convexity" in feature
        or "slope" in feature
        or feature.startswith("bid_gap_")
        or feature.startswith("ask_gap_")
        or feature in {
            "bid_gap_count",
            "max_bid_gap",
            "bid_gap_near_far_ratio",
            "ask_gap_count",
            "max_ask_gap",
            "ask_gap_near_far_ratio",
            "gap_count_diff",
            "max_gap_diff",
            "gap_near_far_ratio_diff",
            "depth_slope_diff",
            "book_convexity_diff",
        }
    ):
        score += 1
    if feature in {
        "spread_recovery",
        "bid_gap_recovery",
        "ask_gap_recovery",
        "bid_depth_replenishment",
        "ask_depth_replenishment",
        "depth_replenishment_diff",
    }:
        score += 1
    if feature == "imbalance_top5":
        score -= 1
    if feature in {"price_spread", "wap_1", "wap_2"}:
        score -= 2
    if feature in {"ksft2", "kup2", "klow2", "kmid2"}:
        score += 5
    return score


def compute_future_returns(df: pl.DataFrame, price_col: str, horizons: list[int]) -> pl.DataFrame:
    exprs = []
    for horizon in horizons:
        exprs.append(
            ((pl.col(price_col).shift(-horizon) / pl.col(price_col)).log()).alias(f"fwd_ret_{horizon}")
        )
    return df.with_columns(exprs)


def numeric_numpy(df: pl.DataFrame, columns: list[str]) -> np.ndarray:
    return df.select(columns).to_numpy()


def compute_std_report(df: pl.DataFrame, feature_cols: list[str]) -> list[dict]:
    arr = numeric_numpy(df, feature_cols)
    mask = np.isfinite(arr).all(axis=1)
    arr = arr[mask]
    stds = np.std(arr, axis=0)
    return [
        {"feature": col, "std": float(std)}
        for col, std in sorted(zip(feature_cols, stds), key=lambda x: x[1])
    ]


def compute_high_corr_pairs(
    df: pl.DataFrame, feature_cols: list[str], corr_threshold: float, sample_size: int
) -> list[dict]:
    work_df = df
    if len(work_df) > sample_size:
        work_df = work_df.sample(n=sample_size, seed=42)

    arr = numeric_numpy(work_df, feature_cols)
    mask = np.isfinite(arr).all(axis=1)
    arr = arr[mask]
    corr = np.corrcoef(arr, rowvar=False)

    rows: list[dict] = []
    for i in range(len(feature_cols)):
        for j in range(i + 1, len(feature_cols)):
            value = corr[i, j]
            if np.isfinite(value) and abs(value) >= corr_threshold:
                rows.append(
                    {
                        "feature_a": feature_cols[i],
                        "feature_b": feature_cols[j],
                        "corr": float(value),
                        "abs_corr": float(abs(value)),
                    }
                )
    rows.sort(key=lambda item: item["abs_corr"], reverse=True)
    return rows


def compute_ic_table(df: pl.DataFrame, feature_cols: list[str], horizons: list[int]) -> list[dict]:
    rows: list[dict] = []
    for horizon in horizons:
        target_col = f"fwd_ret_{horizon}"
        work_df = df.select(feature_cols + [target_col]).drop_nulls()
        arr = work_df.to_numpy()
        x = arr[:, :-1]
        y = arr[:, -1]

        for idx, feature in enumerate(feature_cols):
            corr = np.corrcoef(x[:, idx], y)[0, 1]
            if np.isfinite(corr):
                rows.append(
                    {
                        "feature": feature,
                        "horizon": horizon,
                        "ic": float(corr),
                        "abs_ic": float(abs(corr)),
                    }
                )

    rows.sort(key=lambda item: (item["horizon"], item["abs_ic"]), reverse=True)
    return rows


def compute_primary_ic_rank(ic_rows: list[dict], primary_horizon: int) -> list[dict]:
    rows = [row for row in ic_rows if int(row["horizon"]) == primary_horizon]
    rows = sorted(rows, key=lambda item: item["abs_ic"], reverse=True)
    ranked = []
    for rank, row in enumerate(rows, start=1):
        ranked.append(
            {
                "rank": rank,
                "feature": row["feature"],
                "horizon": row["horizon"],
                "ic": row["ic"],
                "abs_ic": row["abs_ic"],
                "category": feature_category(str(row["feature"])),
            }
        )
    return ranked


def build_ic_lookup(ic_rows: list[dict]) -> dict[int, dict[str, float]]:
    lookup: dict[int, dict[str, float]] = {}
    for row in ic_rows:
        horizon = int(row["horizon"])
        lookup.setdefault(horizon, {})[str(row["feature"])] = float(row["ic"])
    return lookup


def manual_duplicate_preference(feature: str, component_set: set[str]) -> int:
    """
    为重复特征分组打少量人工偏好分，帮助稳定 tie-break。
    """
    score = 0
    zscore_name = _trend_to_zscore_name(feature)
    if zscore_name and zscore_name in component_set:
        score -= 6

    if feature == "avg_trade_price_mid_bias" and "avg_trade_price_bias" in component_set:
        score -= 6
    if feature == "best_spread_duration" and "best_quote_duration" in component_set:
        score -= 2
    if feature == "imbalance_top5" and "volume_imbalance" in component_set:
        score -= 1
    if feature == "volume_imbalance" and "imbalance_top5" in component_set:
        score += 1
    return score


def deduplicate_exact_corr_features(
    feature_cols: list[str],
    corr_rows: list[dict],
    ic_lookup: dict[str, float],
    exact_corr_threshold: float,
) -> tuple[list[str], list[dict]]:
    """
    对接近完全重复（|corr| >= threshold）特征做组件级去重。
    每个重复组件仅保留一个代表特征：
    1) 主 horizon 的 |IC| 更高
    2) 人工偏好与一般偏好分更高
    """
    feature_set = set(feature_cols)
    adjacency: dict[str, set[str]] = {}
    corr_lookup: dict[tuple[str, str], float] = {}
    for row in corr_rows:
        abs_corr = float(row["abs_corr"])
        if abs_corr < exact_corr_threshold:
            continue
        a = str(row["feature_a"])
        b = str(row["feature_b"])
        if a not in feature_set or b not in feature_set:
            continue
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
        corr_lookup[(a, b)] = abs_corr
        corr_lookup[(b, a)] = abs_corr

    visited: set[str] = set()
    components: list[list[str]] = []
    for feature in feature_cols:
        if feature in visited or feature not in adjacency:
            continue
        stack = [feature]
        visited.add(feature)
        component: list[str] = []
        while stack:
            cur = stack.pop()
            component.append(cur)
            for nxt in adjacency.get(cur, set()):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        if len(component) > 1:
            components.append(component)

    drop_rows: list[dict] = []
    dropped: set[str] = set()
    for component in components:
        comp_set = set(component)
        ranked = sorted(
            component,
            key=lambda f: (
                -abs(float(ic_lookup.get(f, 0.0))),
                -manual_duplicate_preference(f, comp_set),
                -feature_preference_score(f),
                len(f),
                f,
            ),
        )
        kept = ranked[0]
        kept_ic = float(ic_lookup.get(kept, 0.0))
        for feature in ranked[1:]:
            dropped.add(feature)
            drop_rows.append(
                {
                    "feature": feature,
                    "kept_feature": kept,
                    "feature_ic": float(ic_lookup.get(feature, 0.0)),
                    "kept_ic": kept_ic,
                    "abs_corr_with_kept": float(corr_lookup.get((feature, kept), np.nan)),
                    "reason": "exact_corr_dedup",
                }
            )

    kept_features = [feature for feature in feature_cols if feature not in dropped]
    return kept_features, drop_rows


def greedy_select_features(
    df: pl.DataFrame,
    feature_cols: list[str],
    primary_horizon: int,
    corr_threshold: float,
    max_features: int,
) -> list[dict]:
    target_col = f"fwd_ret_{primary_horizon}"
    work_df = df.select(feature_cols + [target_col]).drop_nulls()
    arr = work_df.to_numpy()
    x = arr[:, :-1]
    y = arr[:, -1]

    ic_scores: dict[str, float] = {}
    for idx, feature in enumerate(feature_cols):
        corr = np.corrcoef(x[:, idx], y)[0, 1]
        if np.isfinite(corr):
            ic_scores[feature] = float(corr)

    ranked = sorted(ic_scores.items(), key=lambda item: abs(item[1]), reverse=True)
    selected: list[str] = []
    rows: list[dict] = []

    for feature, ic_value in ranked:
        if len(selected) >= max_features:
            break

        keep = True
        reason = "selected"
        candidate = work_df.select([feature] + selected).to_numpy()
        feat_vec = candidate[:, 0]

        for idx, chosen in enumerate(selected, start=1):
            chosen_vec = candidate[:, idx]
            corr = np.corrcoef(feat_vec, chosen_vec)[0, 1]
            if np.isfinite(corr) and abs(corr) >= corr_threshold:
                keep = False
                reason = f"blocked_by:{chosen}"
                break

        if keep:
            selected.append(feature)

        rows.append(
            {
                "feature": feature,
                "ic": ic_value,
                "abs_ic": abs(ic_value),
                "status": "keep" if keep else "drop",
                "reason": reason,
            }
        )

    return rows


def build_keep_rows(shortlist_rows: list[dict]) -> list[dict]:
    return [row for row in shortlist_rows if row["status"] == "keep"]


def build_vp_vae_recommendation(
    keep_rows: list[dict],
    corr_rows: list[dict],
    category_minimums: dict[str, int],
    category_maximums: dict[str, int],
    target_count: int | None,
) -> list[dict]:
    blocked_pairs = {
        tuple(sorted((str(row["feature_a"]), str(row["feature_b"])))): float(row["abs_corr"])
        for row in corr_rows
    }

    ranked = sorted(
        keep_rows,
        key=lambda row: (row["abs_ic"], feature_preference_score(str(row["feature"]))),
        reverse=True,
    )

    selected: list[str] = []
    selected_set: set[str] = set()
    category_counts = {
        key: 0 for key in set(category_minimums) | set(category_maximums)
    }
    decision_reason: dict[str, str] = {}

    def can_add(feature: str, category: str) -> tuple[bool, str]:
        if category in category_maximums and category_counts[category] >= category_maximums[category]:
            return False, "category_cap_reached"
        for chosen in selected:
            pair = tuple(sorted((feature, chosen)))
            if pair in blocked_pairs:
                return False, f"high_corr_with:{chosen}"
        return True, "selected"

    for category, minimum in category_minimums.items():
        if minimum <= 0:
            continue
        for row in ranked:
            if category_counts[category] >= minimum:
                break
            feature = str(row["feature"])
            if feature in selected_set or feature_category(feature) != category:
                continue
            keep, reason = can_add(feature, category)
            if keep:
                selected.append(feature)
                selected_set.add(feature)
                category_counts[category] += 1
                decision_reason[feature] = "selected_category_minimum"
            else:
                decision_reason.setdefault(feature, reason)

    for row in ranked:
        if target_count is not None and target_count > 0 and len(selected) >= target_count:
            break
        feature = str(row["feature"])
        if feature in selected_set:
            continue
        category = feature_category(feature)
        keep, reason = can_add(feature, category)
        if keep:
            selected.append(feature)
            selected_set.add(feature)
            if category in category_counts:
                category_counts[category] += 1
            decision_reason[feature] = "selected_fill_to_target"
        else:
            decision_reason.setdefault(feature, reason)

    rows: list[dict] = []
    for row in ranked:
        feature = str(row["feature"])
        category = feature_category(feature)
        rows.append(
            {
                "feature": feature,
                "category": category,
                "ic": row["ic"],
                "abs_ic": row["abs_ic"],
                "status": "keep" if feature in selected_set else "drop",
                "reason": decision_reason.get(
                    feature,
                    "target_count_reached" if target_count is not None and target_count > 0 else "category_cap_or_rank_limit",
                ),
            }
        )

    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_feature_list_txt(path: Path, rows: list[dict]) -> None:
    selected = [str(row["feature"]) for row in rows if row["status"] == "keep"]
    path.write_text("\n".join(selected) + ("\n" if selected else ""), encoding="utf-8")


def write_feature_list_md(
    path: Path,
    rows: list[dict],
    horizon: int,
    target_count: int | None,
    title: str = "VP-VAE Recommended Feature List",
) -> None:
    selected = [row for row in rows if row["status"] == "keep"]
    selection_line = (
        f"- Guarantee category coverage first, then fill to fixed target count `{target_count}`"
        if target_count is not None and target_count > 0
        else "- Guarantee category coverage first, then keep remaining shortlisted features within category caps"
    )
    lines = [
        f"# {title}",
        "",
        f"Decision horizon: `{horizon}`",
        "",
        "Selection logic:",
        "",
        "- Prefer higher absolute IC on the decision horizon",
        "- Remove highly correlated duplicates",
        selection_line,
        "- Enforce category caps to avoid one factor family dominating the final set",
        "",
        "## Final Features",
        "",
        "```text",
    ]
    lines.extend(str(row["feature"]) for row in selected)
    lines.extend(
        [
            "```",
            "",
            "## Rationale",
            "",
        ]
    )
    for row in selected:
        lines.append(
            f"- `{row['feature']}`: category={row['category']}, ic={float(row['ic']):.6f}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_strategy_alias_outputs(
    output_dir: Path,
    strategy_name: str,
    horizon: int,
    rows: list[dict],
    target_count: int | None,
) -> None:
    alias_base = output_dir / f"vp_vae_{strategy_name}_feature_list"
    write_feature_list_txt(alias_base.with_suffix(".txt"), rows)
    write_feature_list_md(
        alias_base.with_suffix(".md"),
        rows,
        horizon,
        target_count,
        title=f"VP-VAE {strategy_name.title()} Feature List",
    )
    # 兼容更直观的命名，便于训练脚本直接读取
    simple_base = output_dir / f"final_feature_list_{strategy_name}"
    write_feature_list_txt(simple_base.with_suffix(".txt"), rows)
    write_feature_list_md(
        simple_base.with_suffix(".md"),
        rows,
        horizon,
        target_count,
        title=f"Final Feature List ({strategy_name.title()})",
    )


def build_summary(
    input_path: Path,
    row_count: int,
    feature_cols: list[str],
    std_rows: list[dict],
    corr_rows: list[dict],
    ic_rows: list[dict],
    ic_rank_rows: list[dict],
    shortlist_rows: list[dict],
    vp_vae_rows: list[dict],
    primary_horizon: int,
    exact_dedup_threshold: float,
    dedup_rows_by_horizon: dict[int, list[dict]] | None = None,
    horizon_feature_rows: dict[int, list[dict]] | None = None,
) -> str:
    lines = [
        f"input: {input_path}",
        f"rows: {row_count}",
        f"feature_count: {len(feature_cols)}",
        "",
        "lowest_std_features:",
    ]
    for row in std_rows[:10]:
        lines.append(f"  {row['feature']}: {row['std']:.8f}")

    lines.append("")
    lines.append(f"high_corr_pairs: {len(corr_rows)}")
    for row in corr_rows[:15]:
        lines.append(f"  {row['feature_a']} vs {row['feature_b']}: {row['corr']:.6f}")

    lines.append("")
    lines.append(f"exact_corr_dedup_threshold: {exact_dedup_threshold:.6f}")
    if dedup_rows_by_horizon:
        for horizon, rows in sorted(dedup_rows_by_horizon.items()):
            lines.append(f"  horizon={horizon}: dropped={len(rows)}")
            for row in rows[:8]:
                lines.append(
                    f"    drop {row['feature']} -> keep {row['kept_feature']} (|corr|={float(row['abs_corr_with_kept']):.6f})"
                )
    else:
        lines.append("  horizon_dedup: none")

    lines.append("")
    lines.append("top_ic_by_horizon:")
    by_horizon: dict[int, list[dict]] = {}
    for row in ic_rows:
        by_horizon.setdefault(int(row["horizon"]), []).append(row)
    for horizon, rows in sorted(by_horizon.items()):
        lines.append(f"  horizon={horizon}")
        for row in rows[:10]:
            lines.append(f"    {row['feature']}: {row['ic']:.6f}")

    lines.append("")
    lines.append(f"primary_horizon_ic_rank={primary_horizon}:")
    for row in ic_rank_rows[:10]:
        lines.append(f"  {row['feature']}: {row['ic']:.6f} ({row['category']})")

    lines.append("")
    lines.append(f"greedy_shortlist_primary_horizon={primary_horizon}:")
    for row in shortlist_rows:
        if row["status"] == "keep":
            lines.append(f"  keep {row['feature']}: ic={row['ic']:.6f}")

    lines.append("")
    lines.append("vp_vae_recommended_features:")
    for row in vp_vae_rows:
        if row["status"] == "keep":
            lines.append(
                f"  keep {row['feature']}: ic={row['ic']:.6f} ({row['category']})"
            )

    if horizon_feature_rows:
        lines.append("")
        lines.append("vp_vae_recommended_features_by_horizon:")
        for horizon, rows in sorted(horizon_feature_rows.items()):
            lines.append(f"  horizon={horizon}")
            for row in rows:
                if row["status"] == "keep":
                    lines.append(
                        f"    keep {row['feature']}: ic={row['ic']:.6f} ({row['category']})"
                    )
        strategy_alias = {5: "short", 30: "mid", 70: "long"}
        available_aliases = [f"{name}=horizon{h}" for h, name in strategy_alias.items() if h in horizon_feature_rows]
        if available_aliases:
            lines.append("")
            lines.append("strategy_aliases:")
            for alias in available_aliases:
                lines.append(f"  {alias}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate factor effectiveness and redundancy.")
    parser.add_argument("--input", type=Path, default=Path("output/train.feather"))
    parser.add_argument("--price-col", type=str, default="close_price")
    parser.add_argument("--horizons", type=str, default="5,30,70")
    parser.add_argument("--corr-threshold", type=float, default=0.95)
    parser.add_argument("--sample-size", type=int, default=100000)
    parser.add_argument("--primary-horizon", type=int, default=5)
    parser.add_argument("--max-features", type=int, default=50)
    parser.add_argument("--exact-dedup-threshold", type=float, default=0.9999)
    parser.add_argument("--target-count", type=int, default=VP_VAE_TARGET_COUNT)
    parser.add_argument("--output-dir", type=Path, default=Path("output/factor_validation"))
    args = parser.parse_args()

    horizons = parse_horizons(args.horizons)
    df = pl.read_ipc(args.input)
    feature_cols = available_feature_columns(df, DEFAULT_FEATURE_COLUMNS)
    if not feature_cols:
        raise ValueError("no feature columns found in input file")

    df = compute_future_returns(df, args.price_col, horizons)
    std_rows = compute_std_report(df, feature_cols)
    corr_rows = compute_high_corr_pairs(df, feature_cols, args.corr_threshold, args.sample_size)
    ic_rows = compute_ic_table(df, feature_cols, horizons)
    ic_rank_rows = compute_primary_ic_rank(ic_rows, args.primary_horizon)
    ic_lookup_by_horizon = build_ic_lookup(ic_rows)

    shortlist_rows_by_horizon: dict[int, list[dict]] = {}
    keep_rows_by_horizon: dict[int, list[dict]] = {}
    vp_vae_rows_by_horizon: dict[int, list[dict]] = {}
    dedup_rows_by_horizon: dict[int, list[dict]] = {}
    dedup_feature_pool_by_horizon: dict[int, list[str]] = {}
    for horizon in horizons:
        dedup_feature_pool_by_horizon[horizon], dedup_rows_by_horizon[horizon] = deduplicate_exact_corr_features(
            feature_cols,
            corr_rows,
            ic_lookup_by_horizon.get(horizon, {}),
            args.exact_dedup_threshold,
        )
        shortlist_rows_by_horizon[horizon] = greedy_select_features(
            df,
            dedup_feature_pool_by_horizon[horizon],
            primary_horizon=horizon,
            corr_threshold=args.corr_threshold,
            max_features=args.max_features,
        )
        keep_rows_by_horizon[horizon] = build_keep_rows(shortlist_rows_by_horizon[horizon])
        vp_vae_rows_by_horizon[horizon] = build_vp_vae_recommendation(
            keep_rows_by_horizon[horizon],
            corr_rows,
            category_minimums=VP_VAE_CATEGORY_MINIMUMS,
            category_maximums=VP_VAE_CATEGORY_MAXIMUMS,
            target_count=(args.target_count if args.target_count > 0 else None),
        )

    shortlist_rows = shortlist_rows_by_horizon[args.primary_horizon]
    keep_rows = keep_rows_by_horizon[args.primary_horizon]
    vp_vae_rows = vp_vae_rows_by_horizon[args.primary_horizon]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "feature_std.csv", std_rows, ["feature", "std"])
    write_csv(
        args.output_dir / "high_corr_pairs.csv",
        corr_rows,
        ["feature_a", "feature_b", "corr", "abs_corr"],
    )
    write_csv(
        args.output_dir / "ic_table.csv",
        ic_rows,
        ["feature", "horizon", "ic", "abs_ic"],
    )
    write_csv(
        args.output_dir / "ic_rank_primary.csv",
        ic_rank_rows,
        ["rank", "feature", "horizon", "ic", "abs_ic", "category"],
    )
    write_csv(
        args.output_dir / "greedy_shortlist.csv",
        shortlist_rows,
        ["feature", "ic", "abs_ic", "status", "reason"],
    )
    write_csv(
        args.output_dir / "redundancy_filtered_rank.csv",
        keep_rows,
        ["feature", "ic", "abs_ic", "status", "reason"],
    )
    write_csv(
        args.output_dir / "vp_vae_recommended_features.csv",
        vp_vae_rows,
        ["feature", "category", "ic", "abs_ic", "status", "reason"],
    )
    write_feature_list_txt(
        args.output_dir / "vp_vae_recommended_features.txt",
        vp_vae_rows,
    )
    write_feature_list_md(
        args.output_dir / "vp_vae_recommended_features.md",
        vp_vae_rows,
        args.primary_horizon,
        (args.target_count if args.target_count > 0 else None),
    )
    write_feature_list_txt(
        args.output_dir / "vp_vae_final_feature_list.txt",
        vp_vae_rows,
    )
    write_feature_list_md(
        args.output_dir / "vp_vae_final_feature_list.md",
        vp_vae_rows,
        args.primary_horizon,
        (args.target_count if args.target_count > 0 else None),
        title="VP-VAE Final Feature List",
    )
    for horizon in horizons:
        horizon_rows = vp_vae_rows_by_horizon[horizon]
        write_csv(
            args.output_dir / f"exact_corr_dedup_h{horizon}.csv",
            dedup_rows_by_horizon[horizon],
            ["feature", "kept_feature", "feature_ic", "kept_ic", "abs_corr_with_kept", "reason"],
        )
        write_csv(
            args.output_dir / f"vp_vae_recommended_features_h{horizon}.csv",
            horizon_rows,
            ["feature", "category", "ic", "abs_ic", "status", "reason"],
        )
        write_feature_list_txt(
            args.output_dir / f"vp_vae_final_feature_list_h{horizon}.txt",
            horizon_rows,
        )
        write_feature_list_md(
            args.output_dir / f"vp_vae_final_feature_list_h{horizon}.md",
            horizon_rows,
            horizon,
            (args.target_count if args.target_count > 0 else None),
            title=f"VP-VAE Final Feature List H{horizon}",
        )
        (args.output_dir / f"feature_pool_after_exact_dedup_h{horizon}.txt").write_text(
            "\n".join(dedup_feature_pool_by_horizon[horizon]) + "\n",
            encoding="utf-8",
        )
    strategy_horizon_aliases = {5: "short", 30: "mid", 70: "long"}
    for horizon, alias in strategy_horizon_aliases.items():
        if horizon in vp_vae_rows_by_horizon:
            write_strategy_alias_outputs(
                args.output_dir,
                alias,
                horizon,
                vp_vae_rows_by_horizon[horizon],
                (args.target_count if args.target_count > 0 else None),
            )

    summary = build_summary(
        args.input,
        row_count=len(df),
        feature_cols=feature_cols,
        std_rows=std_rows,
        corr_rows=corr_rows,
        ic_rows=ic_rows,
        ic_rank_rows=ic_rank_rows,
        shortlist_rows=shortlist_rows,
        vp_vae_rows=vp_vae_rows,
        primary_horizon=args.primary_horizon,
        exact_dedup_threshold=args.exact_dedup_threshold,
        dedup_rows_by_horizon=dedup_rows_by_horizon,
        horizon_feature_rows=vp_vae_rows_by_horizon,
    )
    summary_path = args.output_dir / "summary.txt"
    summary_path.write_text(summary, encoding="utf-8")
    print(summary)
    print(f"saved_report_dir: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
