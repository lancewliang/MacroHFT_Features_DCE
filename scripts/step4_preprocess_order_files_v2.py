#!/usr/bin/env python3
"""
五档行情数据处理脚本（polars版本）
功能：按30秒聚合期货挂单量数据，bidx_price bidx_size askx_price askx_size
使用polars进行高性能数据处理
data/铝/年份/五档行情数据

#### 原始字段列表

| 字段名 | 类型 | 说明 | 映射到 target_factor |
|--------|------|------|---------------------|
| **时间字段** |
| `ActionDay` | Date | 业务日期 | - |
| `TradingDay` | Date | 交易日 | - |
| `UpdateTime` | Time | 更新时间 | - |
| **合约信息** |
| `InstrumentID` | String | 合约代码 (如 y2309) | - |
| **价格字段** |
| `LastPrice` | Float | 最新价 | - |
| `HighPrice` | Float | 最高价 | - |
| `LowPrice` | Float | 最低价 | - |
| `OpenPrice` | Float | 开盘价 | - |
| `ClosePrice` | Float | 收盘价 | - |
| `SettlementPrice` | Float | 结算价 | - |
| `PreSettlementPrice` | Float | 前结算价 | - |
| `PreClosePrice` | Float | 前收盘价 | - |
| **成交量字段** |
| `LastVolume` | Int | 最新成交量 | - |
| `Volume` | Int | 总成交量 | - |
| `Turnover` | Float | 成交额 | - |
| `OpenInterest` | Int | 持仓量 | - |
| `PreOpenInterest` | Int | 前持仓量 | - |
| `OpenInteChange` | Int | 持仓变化 | - |
| `AveragePrice` | Float | 均价 | - |
| **买卖量统计** |
| `BuyVolume` | Int | 买成交量 | - |
| `SellVolume` | Int | 卖成交量 | - |
| `AvgBuyPrice` | Float | 买均价 | - |
| `AvgSellPrice` | Float | 卖均价 | - |
| **买一到买五** |
| `BidPrice1` | Float | 买一价 | `bid1_price` |
| `BidVolume1` | Int | 买一量 | `bid1_size` |
| `DerBidVolume1` | Int | 买一推导量 | - |
| `BidPrice2` | Float | 买二价 | `bid2_price` |
| `BidVolume2` | Int | 买二量 | `bid2_size` |
| `DerBidVolume2` | Int | 买二推导量 | - |
| `BidPrice3` | Float | 买三价 | `bid3_price` |
| `BidVolume3` | Int | 买三量 | `bid3_size` |
| `DerBidVolume3` | Int | 买三推导量 | - |
| `BidPrice4` | Float | 买四价 | `bid4_price` |
| `BidVolume4` | Int | 买四量 | `bid4_size` |
| `DerBidVolume4` | Int | 买四推导量 | - |
| `BidPrice5` | Float | 买五价 | `bid5_price` |
| `BidVolume5` | Int | 买五量 | `bid5_size` |
| `DerBidVolume5` | Int | 买五推导量 | - |
| **卖一到卖五** |
| `AskPrice1` | Float | 卖一价 | `ask1_price` |
| `AskVolume1` | Int | 卖一量 | `ask1_size` |
| `DerAskVolume1` | Int | 卖一推导量 | - |
| `AskPrice2` | Float | 卖二价 | `ask2_price` |
| `AskVolume2` | Int | 卖二量 | `ask2_size` |
| `DerAskVolume2` | Int | 卖二推导量 | - |
| `AskPrice3` | Float | 卖三价 | `ask3_price` |
| `AskVolume3` | Int | 卖三量 | `ask3_size` |
| `DerAskVolume3` | Int | 卖三推导量 | - |
| `AskPrice4` | Float | 卖四价 | `ask4_price` |
| `AskVolume4` | Int | 卖四量 | `ask4_size` |
| `DerAskVolume4` | Int | 卖四推导量 | - |
| `AskPrice5` | Float | 卖五价 | `ask5_price` |
| `AskVolume5` | Int | 卖五量 | `ask5_size` |
| `DerAskVolume5` | Int | 卖五推导量 | - |
| **限价字段** |
| `UpperLimitPrice` | Float | 涨停价 | - |
| `LowerLimitPrice` | Float | 跌停价 | - |
| `LifeHighPrice` | Float | 历史最高价 | - |
| `LifeLowPrice` | Float | 历史最低价 | - |

输出字段：
时间档位 datetime,minute,
是否连续 is_consecutive_minute,
委托价格：open_price,high_price,low_price,close_price,
成交统计：total_trade_volume,turnover,open_interest,
5档委托：bid1_price,bid1_size,bid2_price,bid2_size,bid3_price,bid3_size,bid4_price,bid4_size,bid5_price,bid5_size,ask1_price,ask1_size,ask2_price,ask2_size,ask3_price,ask3_size,ask4_price,ask4_size,ask5_price,ask5_size
"""

import polars as pl
import argparse
import os
import glob
import re
import traceback
from datetime import datetime
from multiprocessing import Pool, cpu_count
from pathlib import Path

def _build_expected_numeric_types():
    """定义预期的数值列类型。"""
    expected_types = {
        "LastPrice": pl.Float64,
        "Volume": pl.Int64,
        "Turnover": pl.Float64,
        "OpenInterest": pl.Int64,
    }
    for i in range(1, 6):
        expected_types[f"BidPrice{i}"] = pl.Float64
        expected_types[f"BidVolume{i}"] = pl.Int64
        expected_types[f"AskPrice{i}"] = pl.Float64
        expected_types[f"AskVolume{i}"] = pl.Int64
    return expected_types


EXPECTED_NUMERIC_TYPES = _build_expected_numeric_types()


def _is_string_dtype(dtype):
    return dtype in (pl.String, pl.Utf8)


def debug_schema(df, stage, source_file, debug=False, max_columns=30):
    """输出DataFrame基础信息，便于定位类型问题。"""
    if not debug:
        return

    shown_columns = df.columns[:max_columns]
    schema_str = ", ".join(f"{col}:{df.schema[col]}" for col in shown_columns)
    if len(df.columns) > max_columns:
        schema_str += ", ..."
    print(
        f"[DEBUG][{stage}] 文件: {source_file}, 行数: {df.height}, 列数: {len(df.columns)}, schema: {schema_str}"
    )


def coerce_numeric_columns(df, source_file, stage, debug=False):
    """
    将关键列转换为预期数值类型，并输出类型修正日志。

    这样即使CSV推断出String（例如整列为null），也能避免后续数值比较报错。
    """
    for col, target_dtype in EXPECTED_NUMERIC_TYPES.items():
        if col not in df.columns:
            continue

        source_dtype = df.schema[col]
        if source_dtype == target_dtype:
            continue

        invalid_count = 0
        invalid_samples = []
        if _is_string_dtype(source_dtype):
            invalid_expr = (
                pl.col(col).is_not_null()
                & (pl.col(col).str.strip_chars() != "")
                & pl.col(col).cast(target_dtype, strict=False).is_null()
            )
            invalid_count = df.select(invalid_expr.sum().alias("invalid_count")).item()
            if invalid_count > 0 and debug:
                invalid_samples = (
                    df.filter(invalid_expr)
                    .select(col)
                    .head(5)
                    .to_series()
                    .to_list()
                )

        nulls_before = df.select(pl.col(col).is_null().sum().alias("nulls_before")).item()
        df = df.with_columns(pl.col(col).cast(target_dtype, strict=False).alias(col))
        nulls_after = df.select(pl.col(col).is_null().sum().alias("nulls_after")).item()
        introduced_nulls = nulls_after - nulls_before

        print(
            f"[类型修正][{stage}] 文件: {source_file}, 列: {col}, "
            f"{source_dtype} -> {target_dtype}, 新增空值: {introduced_nulls}"
        )
        if invalid_count > 0:
            print(
                f"[类型告警][{stage}] 文件: {source_file}, 列: {col}, "
                f"有 {invalid_count} 个非空值无法转换为 {target_dtype}"
            )
            if invalid_samples:
                print(f"[类型告警][{stage}] 文件: {source_file}, 列: {col}, 异常样例: {invalid_samples}")

    return df


def process_order_data(input_dir, output_dir, interval="30s", debug=False):
    """
    处理期货五档行情统计数据（polars版本）

    Args:
        input_dir: 输入目录路径 (data/豆粕/年份/五档行情数据/)
        output_dir: 输出目录路径
        interval: 聚合时间间隔，支持 "30s" 或 "1m"
    """

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 查找所有CSV文件
    csv_pattern = os.path.join(input_dir, "*.csv")
    csv_files = glob.glob(csv_pattern)

    print(f"找到 {len(csv_files)} 个CSV文件需要处理")

    for csv_file in csv_files:
        current_step = "初始化"
        df = None
        result_df = None
        try:
            print(f"正在处理文件: {os.path.basename(csv_file)}")

            # 使用polars读取CSV文件（性能优化）
            current_step = "读取CSV"
            df = pl.read_csv(csv_file)
            debug_schema(df, current_step, csv_file, debug=debug)

            # 数据预处理
            current_step = "数据预处理"
            df = preprocess_data(df, source_file=csv_file, debug=debug)
            debug_schema(df, current_step, csv_file, debug=debug)

            # 按指定间隔聚合数据
            current_step = "按间隔聚合"
            result_df = aggregate_by_minute(df, interval=interval, source_file=csv_file, debug=debug)
            debug_schema(result_df, current_step, csv_file, debug=debug)

            # 生成输出文件名（根据间隔命名，如 _30s.csv 或 _1m.csv）
            suffix = interval.replace("s", "s").replace("m", "m")
            output_filename = os.path.basename(csv_file).replace('.csv', f'_{suffix}.csv')
            output_path = os.path.join(output_dir, output_filename)

            # 过滤 open/high/low/close 全为 null 的行后保存
            current_step = "结果过滤与写出"
            result_df = result_df.filter(
                ~pl.all_horizontal(
                    pl.col("open_price").is_null(),
                    pl.col("high_price").is_null(),
                    pl.col("low_price").is_null(),
                    pl.col("close_price").is_null(),
                )
            )
            result_df.write_csv(output_path)
            print(f"已保存处理结果: {output_path}")
            # exit(0)
        except Exception as e:
            print(f"处理文件 {csv_file} 在步骤 [{current_step}] 时出错: {str(e)}")
            print("详细异常堆栈如下：")
            print(traceback.format_exc())
            if df is not None:
                debug_schema(df, f"{current_step}-失败时输入", csv_file, debug=True, max_columns=50)
            if result_df is not None:
                debug_schema(result_df, f"{current_step}-失败时输出", csv_file, debug=True, max_columns=50)
            continue

def preprocess_data(df, source_file="", debug=False):
    """
    数据预处理（polars版本）

    Args:
        df: 原始数据DataFrame

    Returns:
        预处理后的DataFrame
    """

    # 创建时间戳列 (ActionDay + UpdateTime)
    df = df.with_columns(
        pl.concat_str([
            pl.col("ActionDay").cast(pl.Utf8),
            pl.lit(" "),
            pl.col("UpdateTime")
        ]).alias("datetime_str")
    )

    # 转换时间格式
    df = df.with_columns(
        pl.col("datetime_str").str.strptime(pl.Datetime, format="%Y%m%d %H:%M:%S%.f").alias("datetime")
    )

    # 过滤无效的时间数据并排序
    df = df.filter(pl.col("datetime").is_not_null()).sort("datetime")

    # 修正关键数值列类型，避免 String 与 Float 比较报错
    df = coerce_numeric_columns(df, source_file=source_file, stage="preprocess_data", debug=debug)
    # 打印所有的列名字
    # print(df.columns)
    return df

def interval_to_seconds(interval):
    """
    将间隔字符串转换为秒数。

    支持格式：
    - 10s / 30s
    - 1m / 5m
    - 1h
    """
    match = re.fullmatch(r"(\d+)([smh])", interval.strip())
    if not match:
        raise ValueError(f"无效间隔格式: {interval}，请使用如 30s / 1m / 1h")

    value = int(match.group(1))
    unit = match.group(2)
    unit_to_seconds = {"s": 1, "m": 60, "h": 3600}

    return value * unit_to_seconds[unit]

def aggregate_by_minute(df, interval="30s", source_file="", debug=False):
    """
    按指定间隔聚合数据（polars版本），取窗口内最后一行的价格和委托量

    聚合规则：
    1. 取每个时间窗口内最后一条快照的5档买卖价格和委托量
    2. open_price 取窗口内第一条 LastPrice，close_price 取最后一条
    3. high_price / low_price 取窗口内所有快照的5档价格极值

    Args:
        df: 预处理后的DataFrame
        interval: 聚合时间间隔，格式如 "30s"、"1m"、"1h"

    Returns:
        聚合后的DataFrame
    """

    # 计算连续窗口判断阈值（秒）
    interval_seconds = interval_to_seconds(interval)

    # 再次兜底类型修正，确保窗口极值计算参与列均为数值类型
    df = coerce_numeric_columns(df, source_file=source_file, stage="aggregate_by_minute", debug=debug)

    # 提取时间戳（按指定间隔截断）
    df = df.with_columns(
        pl.col("datetime").dt.truncate(interval).alias("minute")
    )

    # 按时间窗口和datetime排序，确保时间顺序正确
    df = df.sort(["minute", "datetime"])

    # ========== 取窗口内最后一行快照 ==========
    agg_exprs = [
        pl.col("datetime").last().alias("datetime"),
        pl.col("LastPrice").first().alias("open_price"),
        pl.col("LastPrice").last().alias("close_price"),
    ]

    if "Volume" in df.columns:
        agg_exprs.append(pl.col("Volume").last().alias("total_trade_volume"))
    if "Turnover" in df.columns:
        agg_exprs.append(pl.col("Turnover").last().alias("turnover"))
    if "OpenInterest" in df.columns:
        agg_exprs.append(pl.col("OpenInterest").last().alias("open_interest"))

    for i in range(1, 6):
        if f"BidPrice{i}" in df.columns:
            agg_exprs.append(pl.col(f"BidPrice{i}").last().alias(f"bid{i}_price"))
        if f"BidVolume{i}" in df.columns:
            agg_exprs.append(pl.col(f"BidVolume{i}").last().alias(f"bid{i}_size"))

    for i in range(1, 6):
        if f"AskPrice{i}" in df.columns:
            agg_exprs.append(pl.col(f"AskPrice{i}").last().alias(f"ask{i}_price"))
        if f"AskVolume{i}" in df.columns:
            agg_exprs.append(pl.col(f"AskVolume{i}").last().alias(f"ask{i}_size"))

    result_df = df.group_by("minute").agg(agg_exprs)

    # ========== 计算30秒窗口内的最高价和最低价 ==========
    all_bid_prices = [pl.col(f"BidPrice{i}") for i in range(1, 6) if f"BidPrice{i}" in df.columns]
    all_ask_prices = [pl.col(f"AskPrice{i}") for i in range(1, 6) if f"AskPrice{i}" in df.columns]

    if all_bid_prices and all_ask_prices:
        df_with_prices = df.with_columns([
            pl.max_horizontal(all_bid_prices + all_ask_prices).alias("row_max_price"),
            pl.min_horizontal(all_bid_prices + all_ask_prices).alias("row_min_price")
        ])
        high_low_prices = df_with_prices.group_by("minute").agg([
            pl.col("row_max_price").max().alias("high_price"),
            pl.col("row_min_price").min().alias("low_price")
        ])
        result_df = result_df.join(high_low_prices, on="minute", how="left")

    # 按时间排序
    result_df = result_df.sort("datetime")

    # 计算连续时间窗口标志
    result_df = result_df.with_columns([
        (pl.col("minute") - pl.col("minute").shift(1)).dt.total_seconds().alias("minute_diff")
    ])

    result_df = result_df.with_columns([
        pl.when(pl.col("minute_diff") == interval_seconds)
          .then(1)
          .otherwise(0)
          .alias("is_consecutive_minute")
    ])

    # 定义需要的字段列表
    required_columns = [
        "datetime",
        "minute",
        "is_consecutive_minute",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "total_trade_volume",
        "turnover",
        "open_interest",
    ]

    for i in range(1, 6):
        required_columns.extend([f"bid{i}_price", f"bid{i}_size"])

    for i in range(1, 6):
        required_columns.extend([f"ask{i}_price", f"ask{i}_size"])

    available_columns = [col for col in required_columns if col in result_df.columns]
    result_df = result_df.select(available_columns)

    return result_df

def process_single_year(args):
    """
    处理单个年份的数据（用于多进程）

    Args:
        args: 包含 (year_dir, output_base_dir, interval) 的元组

    Returns:
        处理结果的元组 (year_name, success, message)
    """
    year_dir, output_base_dir, interval, debug = args
    year_name = os.path.basename(year_dir)
    order_dir = os.path.join(year_dir)

    try:
        if os.path.exists(order_dir):
            print(f"\n[进程 {os.getpid()}] 开始处理年份: {year_name}")

            # 创建对应的输出目录
            output_dir = os.path.join(output_base_dir, year_name, "orderbook", interval)

            # 处理该年份的数据
            process_order_data(order_dir, output_dir, interval=interval, debug=debug)

            print(f"[进程 {os.getpid()}] 完成处理年份: {year_name}")
            return (year_name, True, "成功")
        else:
            return (year_name, False, f"目录不存在: {order_dir}")
    except Exception as e:
        return (year_name, False, f"处理失败: {str(e)}")


def process_all_years(base_dir, output_base_dir, num_processes=None, interval="30s", debug=False):
    """
    使用多进程并行处理所有年份的数据

    Args:
        base_dir: 基础数据目录 (data/豆粕/)
        output_base_dir: 输出基础目录
        num_processes: 进程数量，默认为 CPU 核心数
        interval: 聚合时间间隔，格式如 "30s"、"1m"、"1h"
    """

    # 查找所有年份目录
    year_pattern = os.path.join(base_dir, "*")
    year_dirs = [d for d in glob.glob(year_pattern) if os.path.isdir(d)]

    if not year_dirs:
        print("未找到年份目录")
        return

    # 准备参数列表（含 interval）
    year_args = [(year_dir, output_base_dir, interval, debug) for year_dir in year_dirs]

    # 确定进程数量
    if num_processes is None:
        num_processes = min(cpu_count(), len(year_dirs))

    print(f"找到 {len(year_dirs)} 个年份目录，将使用 {num_processes} 个进程并行处理，聚合间隔: {interval}")

    # 使用进程池并行处理
    with Pool(processes=num_processes) as pool:
        results = pool.map(process_single_year, year_args)

    # 输出处理结果摘要
    print("\n" + "="*60)
    print("处理结果摘要:")
    print("="*60)
    success_count = 0
    for year_name, success, message in results:
        status = "✓" if success else "✗"
        print(f"{status} {year_name}: {message}")
        if success:
            success_count += 1

    print(f"\n总计: {success_count}/{len(results)} 个年份处理成功")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="按指定间隔聚合期货五档委托数据")
    parser.add_argument(
        "--commodity",
        type=str,
        default="铝",
        help="品种名称（默认：铝，例如：燃料油）"
    )
    parser.add_argument(
        "--interval",
        type=str,
        default="30s",
        help="聚合时间间隔（默认：30s，示例：10s、20s、30s、1m）"
    )
    parser.add_argument(
        "--base-data-dir",
        type=str,
        help="输入基础目录（可选，默认：项目目录/data/{品种}）"
    )
    parser.add_argument(
        "--output-base-dir",
        type=str,
        help="输出基础目录（可选，默认：与输入基础目录相同）"
    )
    parser.add_argument(
        "--num-processes",
        type=int,
        default=None,
        help="并行进程数（可选，默认自动使用 CPU 核心数）"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="打印详细调试日志（字段类型、类型修正、异常堆栈）"
    )
    args = parser.parse_args()

    try:
        interval_seconds = interval_to_seconds(args.interval)
    except ValueError as exc:
        parser.error(str(exc))

    project_root = Path(__file__).resolve().parent.parent

    # 设置路径
    if args.base_data_dir:
        base_data_dir = args.base_data_dir
    else:
        base_data_dir = str(project_root / "data" / args.commodity)

    if args.output_base_dir:
        output_base_dir = args.output_base_dir
    else:
        output_base_dir = base_data_dir

    print("开始处理期货五档行情统计数据...")
    print(f"品种: {args.commodity}")
    print(f"聚合间隔: {args.interval} ({interval_seconds} 秒)")
    print(f"系统 CPU 核心数: {cpu_count()}")
    print(f"输入目录: {base_data_dir}")
    print(f"输出目录: {output_base_dir}")
    print(f"调试模式: {'开启' if args.debug else '关闭'}")

    if not os.path.exists(base_data_dir):
        print(f"输入目录不存在: {base_data_dir}")
        return

    # 使用多进程处理所有年份的数据
    process_all_years(
        base_data_dir,
        output_base_dir,
        num_processes=args.num_processes,
        interval=args.interval,
        debug=args.debug
    )

    print("\n数据处理完成!")

if __name__ == "__main__":
    main()
