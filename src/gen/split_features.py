"""
特征数据分割脚本
将大的特征文件按时间段分割成多个小文件
"""

import polars as pl
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
import logging

from config import SYMBOL, get_symbol_output_root


def setup_logging(level: str = "INFO"):
    """配置日志系统"""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_date_ranges(ranges_str: str) -> List[Tuple[str, str]]:
    """
    解析日期范围字符串

    Args:
        ranges_str: 日期范围字符串，格式: "20230101-20250131,20250201-20250531,20250601-20251031"

    Returns:
        日期范围列表 [(start1, end1), (start2, end2), ...]
    """
    ranges = []
    for range_part in ranges_str.split(','):
        range_part = range_part.strip()
        if '-' in range_part:
            parts = range_part.split('-')
            if len(parts) == 2:
                start_date = parts[0].strip()
                end_date = parts[1].strip()
                try:
                    datetime.strptime(start_date, "%Y%m%d")
                    datetime.strptime(end_date, "%Y%m%d")
                except ValueError as e:
                    raise ValueError(
                        f"无效的日期范围 '{range_part}': {e}\n"
                        f"请检查日期是否存在 (例如: 2月没有29日(非闰年), 4/6/9/11月没有31日)"
                    )
                ranges.append((start_date, end_date))
    return ranges


def normalize_output_filename(filename: str) -> str:
    """
    规范化输出文件名：
    - 支持省略 .feather 后缀
    - 仅允许文件名，不允许目录路径
    """
    normalized = filename.strip()
    if not normalized:
        raise ValueError("输出文件名不能为空")

    if "/" in normalized or "\\" in normalized:
        raise ValueError(f"输出文件名 '{normalized}' 不能包含目录分隔符")

    suffix = Path(normalized).suffix.lower()
    if not suffix:
        normalized = f"{normalized}.feather"
    elif suffix != ".feather":
        raise ValueError(f"输出文件名 '{normalized}' 必须使用 .feather 后缀")

    return normalized


def parse_output_filenames(names_str: str) -> List[str]:
    """
    解析输出文件名列表字符串

    Args:
        names_str: 文件名字符串，格式: "df_train,df_val,df_test"

    Returns:
        文件名列表（带 .feather 后缀）
    """
    filenames = [normalize_output_filename(name) for name in names_str.split(",")]

    if len(set(filenames)) != len(filenames):
        raise ValueError("输出文件名不能重复")

    return filenames


def split_features(
    input_file: Path,
    date_ranges: List[Tuple[str, str]],
    output_dir: Path,
    time_column: str = "candle_begin_time",
    output_filenames: Optional[List[str]] = None,
) -> None:
    """
    按时间段分割特征文件

    Args:
        input_file: 输入文件路径
        date_ranges: 日期范围列表 [(start1, end1), (start2, end2), ...]
        output_dir: 输出目录
        time_column: 时间列名称
        output_filenames: 输出文件名列表，与 date_ranges 一一对应
    """
    logger = logging.getLogger(__name__)

    # 读取数据
    logger.info(f"读取输入文件: {input_file}")
    df = pl.read_ipc(input_file)

    logger.info(f"总数据行数: {len(df)}")
    logger.info(f"时间列: {time_column}")

    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)

    # 确保时间列是datetime类型
    if df[time_column].dtype != pl.Datetime:
        logger.info(f"转换时间列 {time_column} 为 datetime 类型")
        df = df.with_columns(
            pl.col(time_column).str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S")
        )

    # 按时间段分割
    for idx, (start_date, end_date) in enumerate(date_ranges):
        logger.info(f"\n处理时间段: {start_date} 至 {end_date}")

        # 转换日期字符串为 datetime
        try:
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d").replace(hour=23, minute=59, second=59)
        except ValueError as e:
            logger.error(f"无效的日期 '{start_date}' 或 '{end_date}': {e}")
            logger.error("请检查日期是否存在 (例如: 2月没有29日(非闰年), 4/6/9/11月没有31日)")
            continue

        # 过滤数据
        filtered_df = df.filter(
            (pl.col(time_column) >= start_dt) &
            (pl.col(time_column) <= end_dt)
        )
        filtered_df = filtered_df.with_columns(
            pl.col('close_price').alias("close"),           
        )
        logger.info(f"该时间段数据行数: {filtered_df.head(10)}")
        rows_count = len(filtered_df)
        logger.info(f"该时间段数据行数: {rows_count}")

        if rows_count == 0:
            logger.warning(f"时间段 {start_date}-{end_date} 没有数据，跳过")
            continue

        # 生成输出文件名
        if output_filenames:
            output_filename = output_filenames[idx]
        else:
            output_filename = f"split_{start_date}_{end_date}.feather"
        output_path = output_dir / output_filename

        # 保存文件
        logger.info(f"保存到: {output_path}")
        filtered_df.write_ipc(output_path)

        logger.info(f"成功保存 {rows_count} 行数据")

    logger.info("\n所有分割完成！")


def auto_split_by_months(
    input_file: Path,
    output_dir: Path,
    start_date: str,
    end_date: str,
    time_column: str = "candle_begin_time"
) -> None:
    """
    按月自动分割特征文件

    Args:
        input_file: 输入文件路径
        output_dir: 输出目录
        start_date: 起始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        time_column: 时间列名称
    """
    logger = logging.getLogger(__name__)

    # 读取数据
    logger.info(f"读取输入文件: {input_file}")
    df = pl.read_ipc(input_file)

    logger.info(f"总数据行数: {len(df)}")

    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)

    # 确保时间列是datetime类型
    if df[time_column].dtype != pl.Datetime:
        logger.info(f"转换时间列 {time_column} 为 datetime 类型")
        df = df.with_columns(
            pl.col(time_column).str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S")
        )

    # 按月分组
    logger.info("\n按月分割数据...")
    df_with_month = df.with_columns(
        pl.col(time_column).dt.strftime("%Y%m").alias("month")
    ) 
    df_with_month = df_with_month.with_columns(
        pl.col('close_price').alias("close"),
        pl.col('open_price').alias("open"),
        pl.col('high_price').alias("high"),
        pl.col('low_price').alias("low")
    )
    print("close price check "+df_with_month.head(10))

    # 获取所有唯一的月份
    months = df_with_month["month"].unique().sort()

    logger.info(f"找到 {len(months)} 个不同的月份")

    # 为每个月保存数据
    for month in months:
        month_str = str(month)
        logger.info(f"\n处理月份: {month_str}")

        # 过滤该月的数据
        month_df = df_with_month.filter(pl.col("month") == month).drop("month")

        rows_count = len(month_df)
        logger.info(f"该月数据行数: {rows_count}")

        if rows_count == 0:
            logger.warning(f"月份 {month_str} 没有数据，跳过")
            continue

        # 生成输出文件名 - 月初到月末
        month_start = f"{month_str}01"

        # 计算月末日期
        year = int(month_str[:4])
        month_num = int(month_str[4:])
        if month_num == 12:
            next_year = year + 1
            next_month = 1
        else:
            next_year = year
            next_month = month_num + 1

        from calendar import monthrange
        last_day = monthrange(year, month_num)[1]
        month_end = f"{month_str}{last_day:02d}"

        output_filename = f"split_{month_start}_{month_end}.feather"
        output_path = output_dir / output_filename

        # 保存文件
        logger.info(f"保存到: {output_path}")
        month_df.write_ipc(output_path)

        logger.info(f"成功保存 {rows_count} 行数据")

    logger.info("\n所有分割完成！")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='分割特征数据文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

1. 按指定时间段分割:
   python split_features.py -i features_20230101_20251231.feather \\
       -r "20230101-20250131,20250201-20250531,20250601-20251031"

2. 指定商品缩写，默认输出到 output/<symbol>/:
   python split_features.py -i features_20230101_20251231.feather \\
       -r "20230101-20250131,20250201-20250531" --symbol fu

3. 按月自动分割:
   python split_features.py -i features_20230101_20251231.feather --auto-monthly --symbol fu

4. 指定输出目录:
   python split_features.py -i features_20230101_20251231.feather \\
       -r "20230101-20250131,20250201-20250531" -o ./split_output

5. 指定每个切割文件名:
   python split_features.py -i features_20230101_20251231.feather \\
       -r "20230101-20250131,20250201-20250531,20250601-20251031" \\
       --symbol fu -n "df_train,df_val,df_test"
        """
    )

    parser.add_argument(
        '-i', '--input',
        type=str,
        required=True,
        help='输入特征文件路径 (feather格式)'
    )

    parser.add_argument(
        '--symbol',
        type=str,
        default=SYMBOL,
        help=f'品种缩写 (默认: {SYMBOL})'
    )

    parser.add_argument(
        '-r', '--ranges',
        type=str,
        help='日期范围，用逗号分隔，格式: "20230101-20250131,20250201-20250531"'
    )

    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default=None,
        help='输出目录（默认: output/<symbol>/）'
    )

    parser.add_argument(
        '-n', '--output-names',
        type=str,
        default=None,
        help='按 --ranges 指定切割文件名，用逗号分隔并与时间段一一对应；例如: "df_train,df_val,df_test"'
    )

    parser.add_argument(
        '-c', '--time-column',
        type=str,
        default='candle_begin_time',
        help='时间列名称 (默认: candle_begin_time)'
    )

    parser.add_argument(
        '--auto-monthly',
        action='store_true',
        help='自动按月分割'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别 (默认: INFO)'
    )

    args = parser.parse_args()

    # 配置日志
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # 验证输入文件
    input_file = Path(args.input)
    if not input_file.exists():
        logger.error(f"输入文件不存在: {input_file}")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else get_symbol_output_root(args.symbol)

    logger.info("="*80)
    logger.info("特征数据分割工具")
    logger.info("="*80)
    logger.info(f"输入文件: {input_file}")
    logger.info(f"品种缩写: {args.symbol}")
    logger.info(f"输出目录: {output_dir}")
    logger.info(f"时间列: {args.time_column}")
    logger.info("="*80)

    try:
        if args.auto_monthly:
            if args.output_names:
                logger.error("--output-names 仅支持与 --ranges 一起使用，--auto-monthly 模式下不可用")
                return 1

            # 自动按月分割
            logger.info("使用自动按月分割模式")
            auto_split_by_months(
                input_file=input_file,
                output_dir=output_dir,
                start_date="",
                end_date="",
                time_column=args.time_column
            )
        elif args.ranges:
            # 按指定范围分割
            date_ranges = parse_date_ranges(args.ranges)

            if not date_ranges:
                logger.error("未提供有效的日期范围")
                logger.error('格式示例: "20230101-20250131,20250201-20250531"')
                return 1

            output_filenames = None
            if args.output_names:
                output_filenames = parse_output_filenames(args.output_names)
                if len(output_filenames) != len(date_ranges):
                    logger.error(
                        f"--output-names 数量({len(output_filenames)}) 与 "
                        f"--ranges 时间段数量({len(date_ranges)}) 不一致"
                    )
                    return 1

            logger.info(f"将分割为 {len(date_ranges)} 个时间段:")
            for idx, (start, end) in enumerate(date_ranges):
                if output_filenames:
                    logger.info(f"  - {start} 至 {end} -> {output_filenames[idx]}")
                else:
                    logger.info(f"  - {start} 至 {end}")

            split_features(
                input_file=input_file,
                date_ranges=date_ranges,
                output_dir=output_dir,
                time_column=args.time_column,
                output_filenames=output_filenames,
            )
        else:
            logger.error("请指定 --ranges 或 --auto-monthly 参数")
            return 1

    except Exception as e:
        logger.error(f"分割过程发生错误: {str(e)}", exc_info=True)
        return 1

    logger.info("="*80)
    logger.info("分割完成！")
    logger.info("="*80)

    return 0


if __name__ == "__main__":
    exit(main())
