#!/usr/bin/env python3
"""
期货成交量统计数据处理脚本（polars版本）
功能：按分钟聚合期货成交量数据，计算收盘价、最高价、最低价
使用polars进行高性能数据处理
data/铝/年份/期货成交量统计


| 字段名 | 类型 | 说明 | 映射到 target_factor |
|--------|------|------|---------------------|
| **时间字段** |
| `ActionDay` | Date | 业务日期 | - |
| `TradingDay` | Date | 交易日 | - |
| `UpdateTime` | Time | 更新时间 | - |
| **合约信息** |
| `InstrumentID` | String | 合约代码 | - |
| **价位1** |
| `Price1` | Float | 价格1 | - |
| `BuyOpenVol1` | Int | 买开仓量1 | - |
| `BuyCloseVol1` | Int | 买平仓量1 | - |
| `SellOpenVol1` | Int | 卖开仓量1 | - |
| `SellCloseVol1` | Int | 卖平仓量1 | - |
| **价位2** |
| `Price2` | Float | 价格2 | - |
| `BuyOpenVol2` | Int | 买开仓量2 | - |
| `BuyCloseVol2` | Int | 买平仓量2 | - |
| `SellOpenVol2` | Int | 卖开仓量2 | - |
| `SellCloseVol2` | Int | 卖平仓量2 | - |
| **价位3** |
| `Price3` | Float | 价格3 | - |
| `BuyOpenVol3` | Int | 买开仓量3 | - |
| `BuyCloseVol3` | Int | 买平仓量3 | - |
| `SellOpenVol3` | Int | 卖开仓量3 | - |
| `SellCloseVol3` | Int | 卖平仓量3 | - |
| **价位4** |
| `Price4` | Float | 价格4 | - |
| `BuyOpenVol4` | Int | 买开仓量4 | - |
| `BuyCloseVol4` | Int | 买平仓量4 | - |
| `SellOpenVol4` | Int | 卖开仓量4 | - |
| `SellCloseVol4` | Int | 卖平仓量4 | - |
| **价位5** |
| `Price5` | Float | 价格5 | - |
| `BuyOpenVol5` | Int | 买开仓量5 | - |
| `BuyCloseVol5` | Int | 买平仓量5 | - |
| `SellOpenVol5` | Int | 卖开仓量5 | - |
| `SellCloseVol5` | Int | 卖平仓量5 | - |
"""

import polars as pl
import os
import glob
from datetime import datetime

def process_futures_data(input_dir, output_dir):
    """
    处理期货成交量统计数据（polars版本）
    
    Args:
        input_dir: 输入目录路径 (data/豆粕/年份/期货成交量统计/)
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
    
        
    df = df.with_columns([
        # 收集所有非零价格
        pl.concat_list([
            pl.when(pl.col("Price1") > 0).then(pl.col("Price1")),
            pl.when(pl.col("Price2") > 0).then(pl.col("Price2")),
            pl.when(pl.col("Price3") > 0).then(pl.col("Price3")),
            pl.when(pl.col("Price4") > 0).then(pl.col("Price4")),
            pl.when(pl.col("Price5") > 0).then(pl.col("Price5"))
        ]).list.drop_nulls().alias("valid_prices")
    ])
    

    
    
    # 提取分钟时间戳
    df = df.with_columns(
        pl.col("datetime").dt.truncate("1m").alias("minute")
    )
   
    # 计算最高价和最低价，并将valid_prices转为逗号分隔的字符串
    df = df.with_columns([
        pl.col("Price1").alias("close_price"),
        pl.col("valid_prices").list.max().alias("high_price"),
        pl.col("valid_prices").list.min().alias("low_price"),
        pl.col("valid_prices").list.eval(pl.element().cast(pl.Utf8)).list.join("|").alias("valid_prices_str")
    ])
     
    # 按分钟分组，获取每分钟的最早和最晚时间
    max_minute_stats = df.group_by("minute").agg(       
        pl.col("datetime").max().alias("max_datetime")
    )
    first_minute_stats = df.group_by("minute").agg(      
        pl.col("datetime").min().alias("min_datetime") 
    )
    
    min_price_df = df.join(first_minute_stats, on="minute")
    min_price_df = min_price_df.filter(pl.col("datetime") == pl.col("min_datetime"))
    min_price_df= min_price_df.with_columns([
        pl.col("Price1").alias("min_first_price1")
    ])
    min_price_df = min_price_df.drop(["Price1"])
    # 只保留每分钟 datetime 最大的行（最后一行）
    df = df.join(max_minute_stats, on="minute")
    df = df.filter(pl.col("datetime") == pl.col("max_datetime"))
    
    # 合并每分钟最早的价格
    df = df.join(min_price_df, on="minute")
    
    #df 变成分钟级别
    
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
    
    # 计算开盘价：如果分钟连续，开盘价为上一分钟的收盘价
    df = df.with_columns([
        # 获取上一分钟的收盘价
        pl.col("close_price").shift(1).alias("prev_close_price")
    ])
    
    # 设置开盘价：连续分钟使用上一分钟的收盘价，非连续分钟使用当前分钟的min_first_price1
    df = df.with_columns([
        pl.when(pl.col("is_consecutive_minute") == 1)
          .then(pl.col("prev_close_price"))
          .otherwise(pl.col("min_first_price1"))
          .alias("open_price")
    ]) 
    
     # 只返回指定的字段
    required_columns = ["datetime", "minute", "open_price", "high_price", "low_price", 
                       "close_price", "is_consecutive_minute"]
    df = df.select(required_columns)
    
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
            futures_dir = os.path.join(year_dir, "期货成交量统计")
            
            if os.path.exists(futures_dir):
                print(f"\n处理年份: {year_name}")
                
                # 创建对应的输出目录
                output_dir = os.path.join(output_base_dir, year_name, "ohlc")
                
                # 处理该年份的数据
                process_futures_data(futures_dir, output_dir)
               

def main():
    """主函数"""
    
    # 设置路径
    base_data_dir = "/home/lanceliang/opt/aiwork/MacroHFT_Features_SH/data/铝"
    output_base_dir = "/home/lanceliang/opt/aiwork/MacroHFT_Features_SH/data/铝"
    
    print("开始处理期货成交量统计数据...")
    
    # 处理所有年份的数据
    process_all_years(base_data_dir, output_base_dir)
    
    print("\n数据处理完成!")

if __name__ == "__main__":
    main()