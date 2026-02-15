#!/usr/bin/env python3
"""
五档行情数据处理脚本（polars版本） 
功能：按分钟聚合期货挂单量数据，bidx_price bidx_size askx_price askx_size
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
            
            # 按分钟聚合数据
            result_df = aggregate_by_minute(df)
            
            # 生成输出文件名
            output_filename = os.path.basename(csv_file).replace('.csv', '_minute.csv')
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
    按分钟聚合数据（polars版本）
    
    Args:
        df: 预处理后的DataFrame
        
    Returns:
        聚合后的DataFrame
    """
    
    # 提取分钟时间戳
    df = df.with_columns(
        pl.col("datetime").dt.truncate("1m").alias("minute")
    )
    
    # 按分钟分组，获取每分钟的最大时间戳
    max_minute_stats = df.group_by("minute").agg(       
        pl.col("datetime").max().alias("max_datetime")
    )
    
    # 只保留每分钟 datetime 最大的行（最后一行）
    df = df.join(max_minute_stats, on="minute")
    df = df.filter(pl.col("datetime") == pl.col("max_datetime"))
    
    # 计算连续分钟标志
    df = df.with_columns([
        # 获取前一行的分钟时间戳
        pl.col("minute").shift(1).alias("prev_minute"),
        # 计算当前分钟和前一分钟的差值（以分钟为单位）
        (pl.col("minute") - pl.col("minute").shift(1)).dt.total_minutes().alias("minute_diff")
    ])
    
    # 判断是否为连续的一分钟（差值等于1分钟）
    df = df.with_columns([
        pl.when(pl.col("minute_diff") == 1)
          .then(1)
          .otherwise(0)
          .alias("is_consecutive_minute")
    ])
    
    # 原始字段名映射到目标字段名
    field_mapping = {
        # 买方五档价格
        "BidPrice1": "bid1_price", "BidPrice2": "bid2_price", "BidPrice3": "bid3_price", 
        "BidPrice4": "bid4_price", "BidPrice5": "bid5_price",
        # 买方五档订单量
        "BidVolume1": "bid1_size", "BidVolume2": "bid2_size", "BidVolume3": "bid3_size",
        "BidVolume4": "bid4_size", "BidVolume5": "bid5_size",
        # 卖方五档价格
        "AskPrice1": "ask1_price", "AskPrice2": "ask2_price", "AskPrice3": "ask3_price",
        "AskPrice4": "ask4_price", "AskPrice5": "ask5_price",
        # 卖方五档订单量
        "AskVolume1": "ask1_size", "AskVolume2": "ask2_size", "AskVolume3": "ask3_size",
        "AskVolume4": "ask4_size", "AskVolume5": "ask5_size"
    }
    
    # 重命名字段
    for old_name, new_name in field_mapping.items():
        if old_name in df.columns:
            df = df.rename({old_name: new_name})
    
    # 定义需要的字段列表
    required_columns = ["datetime", "minute", "is_consecutive_minute"]
    
    # 添加买方五档价格和订单量字段
    for i in range(1, 6):
        required_columns.extend([f"bid{i}_price", f"bid{i}_size"])
    
    # 添加卖方五档价格和订单量字段
    for i in range(1, 6):
        required_columns.extend([f"ask{i}_price", f"ask{i}_size"])
    
    # 只返回指定的字段（只保留存在的字段）
    available_columns = [col for col in required_columns if col in df.columns]
    df = df.select(available_columns)
    
    return df

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