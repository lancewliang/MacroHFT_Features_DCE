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
from pathlib import Path
from typing import Iterable

import numpy as np
import polars as pl

ROLLING_WINDOWS = [60, 180, 360]
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
    "avg_trade_price_bias_change",
    "open_interest_change",
    "open_interest_change_ratio",
    "open_interest_change_per_trade",
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
    "ofi",
    *[f"ofi_{window}" for window in ROLLING_WINDOWS],
    *[f"ofi_vol_{window}" for window in ROLLING_WINDOWS],
    "bid_depth_slope",
    "ask_depth_slope",
    "bid_book_convexity",
    "ask_book_convexity",
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
]


VP_VAE_CATEGORY_QUOTAS = {
    "kline_core": 4,
    "spread": 2,
    "trend": 2,
    "distribution": 1,
    "momentum": 1,
    "stability": 1,
    "order_flow": 1,
    "shape": 1,
    "trade_activity": 1,
}


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
    if feature in {"imbalance_top3_change", "weighted_imbalance_inv_change"}:
        return "distribution"
    if (
        feature.startswith("imbalance_top")
        or feature.startswith("weighted_imbalance")
        or feature.endswith("_queue_concentration")
        or feature.endswith("_depth_share")
    ):
        return "distribution"
    if feature in {"best_spread_duration", "best_quote_duration"} or any(
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
                "open_interest_change_zscore",
                "log_return_wap_1_vol",
                "log_return_wap_2_vol",
                "log_return_bid1_price_vol",
                "price_spread_vol",
            ]
        )
    ):
        score += 2
    if "convexity" in feature or "slope" in feature:
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
    quotas: dict[str, int],
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
    category_counts = {key: 0 for key in quotas}
    rows: list[dict] = []

    def can_add(feature: str, category: str) -> tuple[bool, str]:
        if category not in quotas:
            return False, "category_not_used"
        if category_counts[category] >= quotas[category]:
            return False, "category_quota_full"
        for chosen in selected:
            pair = tuple(sorted((feature, chosen)))
            if pair in blocked_pairs:
                return False, f"high_corr_with:{chosen}"
        return True, "selected"

    for row in ranked:
        feature = str(row["feature"])
        category = feature_category(feature)
        keep, reason = can_add(feature, category)
        if keep:
            selected.append(feature)
            category_counts[category] += 1
        rows.append(
            {
                "feature": feature,
                "category": category,
                "ic": row["ic"],
                "abs_ic": row["abs_ic"],
                "status": "keep" if keep else "drop",
                "reason": reason,
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
    primary_horizon: int,
    title: str = "VP-VAE Recommended Feature List",
) -> None:
    selected = [row for row in rows if row["status"] == "keep"]
    lines = [
        f"# {title}",
        "",
        f"Primary decision horizon: `{primary_horizon}`",
        "",
        "Selection logic:",
        "",
        "- Prefer higher absolute IC on the primary horizon",
        "- Remove highly correlated duplicates",
        "- Keep category diversity for VP-VAE inputs",
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

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate factor effectiveness and redundancy.")
    parser.add_argument("--input", type=Path, default=Path("output/train.feather"))
    parser.add_argument("--price-col", type=str, default="close_price")
    parser.add_argument("--horizons", type=str, default="1,5,10")
    parser.add_argument("--corr-threshold", type=float, default=0.95)
    parser.add_argument("--sample-size", type=int, default=100000)
    parser.add_argument("--primary-horizon", type=int, default=1)
    parser.add_argument("--max-features", type=int, default=15)
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
    shortlist_rows = greedy_select_features(
        df,
        feature_cols,
        primary_horizon=args.primary_horizon,
        corr_threshold=args.corr_threshold,
        max_features=args.max_features,
    )
    keep_rows = build_keep_rows(shortlist_rows)
    vp_vae_rows = build_vp_vae_recommendation(
        keep_rows,
        corr_rows,
        quotas=VP_VAE_CATEGORY_QUOTAS,
    )

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
    )
    write_feature_list_txt(
        args.output_dir / "vp_vae_final_feature_list.txt",
        vp_vae_rows,
    )
    write_feature_list_md(
        args.output_dir / "vp_vae_final_feature_list.md",
        vp_vae_rows,
        args.primary_horizon,
        title="VP-VAE Final Feature List",
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
    )
    summary_path = args.output_dir / "summary.txt"
    summary_path.write_text(summary, encoding="utf-8")
    print(summary)
    print(f"saved_report_dir: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
