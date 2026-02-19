#!/usr/bin/env python3
"""
五档行情数据处理脚本（polars版本）
功能：按30秒聚合期货挂单量数据，bidx_price bidx_size askx_price askx_size
使用polars进行高性能数据处理
data/豆粕/2023/五档行情数据

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
5档委托：bid1_price,bid1_size,bid2_price,bid2_size,bid3_price,bid3_size,bid4_price,bid4_size,bid5_price,bid5_size,ask1_price,ask1_size,ask2_price,ask2_size,ask3_price,ask3_size,ask4_price,ask4_size,ask5_price,ask5_size
"""

import polars as pl
import os
import glob
from datetime import datetime
from multiprocessing import Pool, cpu_count

def process_order_data(input_dir, output_dir):
    """
    处理期货五档行情统计数据（polars版本）

    Args:
        input_dir: 输入目录路径 (data/豆粕/年份/五档行情数据/)
        output_dir: 输出目录路径
    """

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 查找所有CSV文件
    csv_pattern = os.path.join(input_dir, "*.csv")
    csv_files = glob.glob(csv_pattern)

    print(f"找到 {len(csv_files)} 个CSV文件需要处理")

    for csv_file in csv_files:
        try:
            print(f"正在处理文件: {os.path.basename(csv_file)}")

            # 使用polars读取CSV文件（性能优化）
            df = pl.read_csv(csv_file)

            # 数据预处理
            df = preprocess_data(df)

            # 按30秒聚合数据
            result_df = aggregate_by_minute(df)

            # 生成输出文件名
            output_filename = os.path.basename(csv_file).replace('.csv', '_30s.csv')
            output_path = os.path.join(output_dir, output_filename)

            # 过滤 open/high/low/close 全为 null 的行后保存
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
            print(f"处理文件 {csv_file} 时出错: {str(e)}")
            continue

def preprocess_data(df):
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

    return df

def aggregate_by_minute(df):
    """
    按30秒聚合数据（polars版本），取窗口内最后一行的价格和委托量

    聚合规则：
    1. 取每个30秒时间窗口内最后一条快照的5档买卖价格和委托量
    2. open_price 取窗口内第一条 LastPrice，close_price 取最后一条
    3. high_price / low_price 取窗口内所有快照的5档价格极值

    Args:
        df: 预处理后的DataFrame

    Returns:
        聚合后的DataFrame
    """

    # 提取30秒时间戳
    df = df.with_columns(
        pl.col("datetime").dt.truncate("30s").alias("minute")
    )

    # 按时间窗口和datetime排序，确保时间顺序正确
    df = df.sort(["minute", "datetime"])

    # ========== 取窗口内最后一行快照 ==========
    agg_exprs = [
        pl.col("datetime").last().alias("datetime"),
        pl.col("LastPrice").first().alias("open_price"),
        pl.col("LastPrice").last().alias("close_price"),
    ]

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
        pl.when(pl.col("minute_diff") == 30)
          .then(1)
          .otherwise(0)
          .alias("is_consecutive_minute")
    ])

    # 定义需要的字段列表
    required_columns = ["datetime", "minute", "is_consecutive_minute", "open_price", "high_price", "low_price", "close_price"]

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
        args: 包含 (year_dir, output_base_dir) 的元组

    Returns:
        处理结果的元组 (year_name, success, message)
    """
    year_dir, output_base_dir = args
    year_name = os.path.basename(year_dir)
    order_dir = os.path.join(year_dir, "五档行情数据")

    try:
        if os.path.exists(order_dir):
            print(f"\n[进程 {os.getpid()}] 开始处理年份: {year_name}")

            # 创建对应的输出目录
            output_dir = os.path.join(output_base_dir, year_name, "orderbook")

            # 处理该年份的数据
            process_order_data(order_dir, output_dir)

            print(f"[进程 {os.getpid()}] 完成处理年份: {year_name}")
            return (year_name, True, "成功")
        else:
            return (year_name, False, f"目录不存在: {order_dir}")
    except Exception as e:
        return (year_name, False, f"处理失败: {str(e)}")


def process_all_years(base_dir, output_base_dir, num_processes=None):
    """
    使用多进程并行处理所有年份的数据

    Args:
        base_dir: 基础数据目录 (data/豆粕/)
        output_base_dir: 输出基础目录
        num_processes: 进程数量，默认为 CPU 核心数
    """

    # 查找所有年份目录
    year_pattern = os.path.join(base_dir, "*")
    year_dirs = [d for d in glob.glob(year_pattern) if os.path.isdir(d)]

    if not year_dirs:
        print("未找到年份目录")
        return

    # 准备参数列表
    year_args = [(year_dir, output_base_dir) for year_dir in year_dirs]

    # 确定进程数量
    if num_processes is None:
        num_processes = min(cpu_count(), len(year_dirs))

    print(f"找到 {len(year_dirs)} 个年份目录，将使用 {num_processes} 个进程并行处理")

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

    # 设置路径
    base_data_dir = "/home/lanceliang/opt/aiwork/MacroHFT_Features_DCE/data/豆粕"
    output_base_dir = "/home/lanceliang/opt/aiwork/MacroHFT_Features_DCE/data/豆粕"

    # 设置进程数量（None 表示使用 CPU 核心数，或手动指定如 4）
    num_processes = None  # 自动使用 CPU 核心数

    print("开始处理期货五档行情统计数据...")
    print(f"系统 CPU 核心数: {cpu_count()}")

    # 使用多进程处理所有年份的数据
    process_all_years(base_data_dir, output_base_dir, num_processes=num_processes)

    print("\n数据处理完成!")

if __name__ == "__main__":
    main()
