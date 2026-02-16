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
            
            # 保存结果
            result_df.write_csv(output_path)
            print(f"已保存处理结果: {output_path}")
            exit(0)
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
    按30秒聚合数据（polars版本），以价格为键构建平均订单簿

    聚合规则（微观结构严谨做法）：
    1. 收集该30秒时间窗口内所有出现过的价格
    2. 对每个价格计算时间加权平均委托量
    3. 构建30秒级别的"平均 order book"
    4. 按价格排序后取前5档（买方从高到低，卖方从低到高）

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

    # 计算每个快照的持续时间（秒，使用毫秒精度）
    df = df.with_columns([
        pl.when(
            pl.col("datetime").shift(-1).over("minute").is_not_null()
        ).then(
            # 不是最后一个快照：计算到下一个快照的时间（毫秒转秒）
            (pl.col("datetime").shift(-1).over("minute") - pl.col("datetime")).dt.total_milliseconds() / 1000.0
        ).otherwise(
            # 最后一个快照：计算到时间窗口结束的时间（毫秒转秒）
            ((pl.col("minute") + pl.duration(seconds=30)) - pl.col("datetime")).dt.total_milliseconds() / 1000.0
        ).alias("duration")
    ])

    # 保存每个30秒时间窗口的最后时间戳、开盘价和收盘价，用于后续合并
    minute_datetime = df.group_by("minute").agg([
        pl.col("datetime").last().alias("datetime"),
        pl.col("LastPrice").first().alias("open_price"),  # 取第一条记录的LastPrice作为开盘价
        pl.col("LastPrice").last().alias("close_price")   # 取最后一条记录的LastPrice作为收盘价
    ])

    # ========== 计算30秒窗口内的最高价和最低价 ==========
    # 收集所有买价
    all_bid_prices = []
    for i in range(1, 6):
        bid_price_col = f"BidPrice{i}"
        if bid_price_col in df.columns:
            all_bid_prices.append(pl.col(bid_price_col))

    # 收集所有卖价
    all_ask_prices = []
    for i in range(1, 6):
        ask_price_col = f"AskPrice{i}"
        if ask_price_col in df.columns:
            all_ask_prices.append(pl.col(ask_price_col))

    # 合并所有价格列，计算每行的最高价和最低价
    if all_bid_prices and all_ask_prices:
        df_with_prices = df.with_columns([
            pl.max_horizontal(all_bid_prices + all_ask_prices).alias("row_max_price"),
            pl.min_horizontal(all_bid_prices + all_ask_prices).alias("row_min_price")
        ])

        # 按时间窗口聚合，计算整个窗口的最高价和最低价
        high_low_prices = df_with_prices.group_by("minute").agg([
            pl.col("row_max_price").max().alias("high_price"),
            pl.col("row_min_price").min().alias("low_price")
        ])
    else:
        high_low_prices = None

    # ========== 处理买方订单簿 ==========
    # 将5档买价买量展开成长格式
    bid_dfs = []
    for i in range(1, 6):
        bid_price_col = f"BidPrice{i}"
        bid_volume_col = f"BidVolume{i}"
        if bid_price_col in df.columns and bid_volume_col in df.columns:
            bid_df = df.select([
                "minute",
                "duration",
                pl.col(bid_price_col).alias("price"),
                pl.col(bid_volume_col).alias("volume")
            ]).filter(
                # 过滤无效价格
                pl.col("price").is_not_null() & (pl.col("price") > 0) &
                pl.col("volume").is_not_null() & (pl.col("volume") > 0)
            )
            bid_dfs.append(bid_df)

    if bid_dfs:
        # 合并所有买方数据
        all_bids = pl.concat(bid_dfs)

        # 按时间窗口+价格聚合，计算时间加权平均委托量
        bid_agg = all_bids.group_by(["minute", "price"]).agg([
            ((pl.col("volume") * pl.col("duration")).sum() /
             pl.col("duration").sum()).round(0).cast(pl.Int64).alias("volume")
        ])
        print(bid_agg.head(20))

        # 按时间窗口分组，价格从高到低排序，添加档位排名
        bid_agg = bid_agg.sort(["minute", "price"], descending=[False, True])
        bid_agg = bid_agg.with_columns(
            (pl.int_range(pl.len()).over("minute") + 1).alias("level")
        ).filter(pl.col("level") <= 5)
        print(bid_agg.head(20))
        # 转换为宽格式：为每个档位创建价格和数量列
        bid_wide = bid_agg.pivot(
            index="minute",
            columns="level",
            values=["price", "volume"]
        )

        # 重命名列：price_1 -> bid1_price, volume_1 -> bid1_size
        rename_map = {}
        for i in range(1, 6):
            if f"price_{i}" in bid_wide.columns:
                rename_map[f"price_{i}"] = f"bid{i}_price"
            if f"volume_{i}" in bid_wide.columns:
                rename_map[f"volume_{i}"] = f"bid{i}_size"
        if rename_map:
            bid_wide = bid_wide.rename(rename_map)
    else:
        bid_wide = None

    # ========== 处理卖方订单簿 ==========
    # 将5档卖价卖量展开成长格式
    ask_dfs = []
    for i in range(1, 6):
        ask_price_col = f"AskPrice{i}"
        ask_volume_col = f"AskVolume{i}"
        if ask_price_col in df.columns and ask_volume_col in df.columns:
            ask_df = df.select([
                "minute",
                "duration",
                pl.col(ask_price_col).alias("price"),
                pl.col(ask_volume_col).alias("volume")
            ]).filter(
                # 过滤无效价格
                pl.col("price").is_not_null() & (pl.col("price") > 0) &
                pl.col("volume").is_not_null() & (pl.col("volume") > 0)
            )
            ask_dfs.append(ask_df)

    if ask_dfs:
        # 合并所有卖方数据
        all_asks = pl.concat(ask_dfs)

        # 按时间窗口+价格聚合，计算时间加权平均委托量
        ask_agg = all_asks.group_by(["minute", "price"]).agg([
            ((pl.col("volume") * pl.col("duration")).sum() /
             pl.col("duration").sum()).round(0).cast(pl.Int64).alias("volume")
        ])

        # 按时间窗口分组，价格从低到高排序，添加档位排名
        ask_agg = ask_agg.sort(["minute", "price"], descending=[False, False])
        ask_agg = ask_agg.with_columns(
            (pl.int_range(pl.len()).over("minute") + 1).alias("level")
        ).filter(pl.col("level") <= 5)

        # 转换为宽格式
        ask_wide = ask_agg.pivot(
            index="minute",
            columns="level",
            values=["price", "volume"]
        )

        # 重命名列：price_1 -> ask1_price, volume_1 -> ask1_size
        rename_map = {}
        for i in range(1, 6):
            if f"price_{i}" in ask_wide.columns:
                rename_map[f"price_{i}"] = f"ask{i}_price"
            if f"volume_{i}" in ask_wide.columns:
                rename_map[f"volume_{i}"] = f"ask{i}_size"
        if rename_map:
            ask_wide = ask_wide.rename(rename_map)
    else:
        ask_wide = None

    # ========== 合并买卖双方数据 ==========
    result_df = minute_datetime

    # 合并最高价和最低价
    if high_low_prices is not None:
        result_df = result_df.join(high_low_prices, on="minute", how="left")

    if bid_wide is not None:
        result_df = result_df.join(bid_wide, on="minute", how="left")

    if ask_wide is not None:
        result_df = result_df.join(ask_wide, on="minute", how="left")

    # 按时间排序
    result_df = result_df.sort("datetime")

    # 计算连续时间窗口标志
    result_df = result_df.with_columns([
        # 计算当前时间窗口和前一时间窗口的差值（以秒为单位）
        (pl.col("minute") - pl.col("minute").shift(1)).dt.total_seconds().alias("minute_diff")
    ])

    # 判断是否为连续的30秒窗口（差值等于30秒）
    result_df = result_df.with_columns([
        pl.when(pl.col("minute_diff") == 30)
          .then(1)
          .otherwise(0)
          .alias("is_consecutive_minute")
    ])

    # 定义需要的字段列表
    required_columns = ["datetime", "minute", "is_consecutive_minute", "open_price", "high_price", "low_price", "close_price"]

    # 添加买方五档价格和订单量字段
    for i in range(1, 6):
        required_columns.extend([f"bid{i}_price", f"bid{i}_size"])

    # 添加卖方五档价格和订单量字段
    for i in range(1, 6):
        required_columns.extend([f"ask{i}_price", f"ask{i}_size"])

    # 只返回指定的字段（只保留存在的字段）
    available_columns = [col for col in required_columns if col in result_df.columns]
    result_df = result_df.select(available_columns)

    return result_df

def process_all_years(base_dir, output_base_dir):
    """
    处理所有年份的数据
    
    Args:
        base_dir: 基础数据目录 (data/豆粕/)
        output_base_dir: 输出基础目录
    """
    
    # 查找所有年份目录
    year_pattern = os.path.join(base_dir, "*")
    year_dirs = glob.glob(year_pattern)
    
    for year_dir in year_dirs:
        if os.path.isdir(year_dir):
            year_name = os.path.basename(year_dir)
            order_dir = os.path.join(year_dir, "五档行情数据")
            
            if os.path.exists(order_dir):
                print(f"\n处理年份: {year_name}")
                
                # 创建对应的输出目录
                output_dir = os.path.join(output_base_dir, year_name, "orderbook")
                
                # 处理该年份的数据
                process_order_data(order_dir, output_dir)

def main():
    """主函数"""
    
    # 设置路径
    base_data_dir = "/home/lanceliang/opt/aiwork/MacroHFT_Features_DCE/data/豆粕"
    output_base_dir = "/home/lanceliang/opt/aiwork/MacroHFT_Features_DCE/data/豆粕"
    
    print("开始处理期货五档行情统计数据...")
    
    # 处理所有年份的数据
    process_all_years(base_data_dir, output_base_dir)
    
    print("\n数据处理完成!")

if __name__ == "__main__":
    main()