"""
测试和验证脚本
用于检查 main.py 生成的特征数据集的质量和正确性
"""

import polars as pl
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

from config import (
    FEATURES_OUTPUT_DIR,
    OUTPUT_FORMAT,
    get_feature_columns
)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeatureValidator:
    """特征数据验证器"""

    def __init__(self, file_path: Path):
        """
        初始化验证器

        Args:
            file_path: 特征数据文件路径
        """
        self.file_path = file_path
        self.df: Optional[pl.DataFrame] = None
        self.validation_results = {}

    def load_data(self) -> bool:
        """
        加载数据

        Returns:
            是否加载成功
        """
        try:
            logger.info(f"加载数据文件: {self.file_path}")

            if not self.file_path.exists():
                logger.error(f"文件不存在: {self.file_path}")
                return False

            # 根据文件格式加载
            if self.file_path.suffix == ".parquet":
                self.df = pl.read_parquet(self.file_path)
            elif self.file_path.suffix == ".feather":
                self.df = pl.read_ipc(self.file_path)
            elif self.file_path.suffix == ".csv":
                self.df = pl.read_csv(self.file_path)
            else:
                logger.error(f"不支持的文件格式: {self.file_path.suffix}")
                return False

            logger.info(f"数据加载成功: {self.df.shape[0]} 行 × {self.df.shape[1]} 列")
            return True

        except Exception as e:
            logger.error(f"加载数据失败: {str(e)}")
            return False

    def check_basic_info(self) -> Dict:
        """
        检查基本信息

        Returns:
            基本信息字典
        """
        logger.info("\n" + "="*60)
        logger.info("1. 基本信息检查")
        logger.info("="*60)

        info = {
            "行数": len(self.df),
            "列数": len(self.df.columns),
            "文件大小": f"{self.file_path.stat().st_size / (1024*1024):.2f} MB",
            "列名": self.df.columns
        }

        logger.info(f"数据行数: {info['行数']:,}")
        logger.info(f"数据列数: {info['列数']}")
        logger.info(f"文件大小: {info['文件大小']}")

        self.validation_results['basic_info'] = info
        return info

    def check_required_columns(self) -> bool:
        """
        检查必需列是否存在

        Returns:
            是否通过检查
        """
        logger.info("\n" + "="*60)
        logger.info("2. 必需列检查")
        logger.info("="*60)

        required_columns = [
            "timestamp",
            "open_price", "high_price", "low_price", "close_price",
            "bid1_price", "bid1_size", "ask1_price", "ask1_size",
        ]

        missing_columns = []
        for col in required_columns:
            if col not in self.df.columns:
                missing_columns.append(col)

        if missing_columns:
            logger.error(f"缺失必需列: {missing_columns}")
            self.validation_results['required_columns'] = False
            return False
        else:
            logger.info("所有必需列都存在 ✓")
            self.validation_results['required_columns'] = True
            return True

    def check_feature_columns(self) -> Dict:
        """
        检查因子列是否完整

        Returns:
            检查结果
        """
        logger.info("\n" + "="*60)
        logger.info("3. 因子列检查")
        logger.info("="*60)

        expected_features = get_feature_columns()
        existing_features = [col for col in expected_features if col in self.df.columns]
        missing_features = [col for col in expected_features if col not in self.df.columns]
        logger.info(f"数据前100行: {self.df.head(200)}")
        result = {
            "预期因子数": len(expected_features),
            "实际因子数": len(existing_features),
            "缺失因子": missing_features
        }

        logger.info(f"预期因子数: {result['预期因子数']}")
        logger.info(f"实际因子数: {result['实际因子数']}")

        if missing_features:
            logger.warning(f"缺失的因子 ({len(missing_features)}个):")
            for feat in missing_features:
                logger.warning(f"  - {feat}")
        else:
            logger.info("所有因子列都存在 ✓")

        self.validation_results['feature_columns'] = result
        return result

    def check_null_values(self) -> Dict:
        """
        检查空值

        Returns:
            空值统计
        """
        logger.info("\n" + "="*60)
        logger.info("4. 空值检查")
        logger.info("="*60)

        null_counts = self.df.null_count()
        total_nulls = sum(null_counts.row(0))

        # 找出有空值的列
        columns_with_nulls = []
        for col in self.df.columns:
            null_count = self.df[col].null_count()
            if null_count > 0:
                null_pct = (null_count / len(self.df)) * 100
                columns_with_nulls.append({
                    "列名": col,
                    "空值数": null_count,
                    "空值比例": f"{null_pct:.2f}%"
                })

        result = {
            "总空值数": total_nulls,
            "有空值的列数": len(columns_with_nulls),
            "有空值的列": columns_with_nulls
        }

        logger.info(f"总空值数: {total_nulls:,}")
        logger.info(f"有空值的列数: {len(columns_with_nulls)}")

        if columns_with_nulls:
            logger.warning("存在空值的列:")
            for item in columns_with_nulls[:10]:  # 只显示前10个
                logger.warning(f"  {item['列名']}: {item['空值数']} ({item['空值比例']})")

            # 对数收益率第一行有空值是正常的
            log_return_cols = [col for col in columns_with_nulls if 'log_return' in col['列名']]
            if log_return_cols:
                logger.info("注意: 对数收益率因子第一行空值是正常的")

            # 趋势因子前N行有空值是正常的（滚动窗口）
            trend_cols = [col for col in columns_with_nulls if 'trend' in col['列名']]
            if trend_cols:
                logger.info("注意: 趋势因子前60行空值是正常的（滚动窗口大小为60）")

        self.validation_results['null_values'] = result
        return result

    def check_data_ranges(self) -> Dict:
        """
        检查数据范围和合理性

        Returns:
            范围检查结果
        """
        logger.info("\n" + "="*60)
        logger.info("5. 数据范围检查")
        logger.info("="*60)

        issues = []

        # 检查 bid1_price < ask1_price
        if 'bid1_price' in self.df.columns and 'ask1_price' in self.df.columns:
            invalid_spread = self.df.filter(pl.col("bid1_price") >= pl.col("ask1_price"))
            if len(invalid_spread) > 0:
                issues.append({
                    "问题": "bid1_price >= ask1_price",
                    "影响行数": len(invalid_spread),
                    "比例": f"{len(invalid_spread)/len(self.df)*100:.2f}%"
                })
                logger.error(f"发现 {len(invalid_spread)} 行数据 bid1_price >= ask1_price ✗")
            else:
                logger.info("bid1_price < ask1_price 检查通过 ✓")

        # 检查 volume_imbalance 范围 [-1, 1]
        if 'volume_imbalance' in self.df.columns:
            out_of_range = self.df.filter(
                (pl.col("volume_imbalance") < -1) | (pl.col("volume_imbalance") > 1)
            )
            if len(out_of_range) > 0:
                issues.append({
                    "问题": "volume_imbalance 超出 [-1, 1]",
                    "影响行数": len(out_of_range),
                    "比例": f"{len(out_of_range)/len(self.df)*100:.2f}%"
                })
                logger.error(f"发现 {len(out_of_range)} 行 volume_imbalance 超出范围 ✗")
            else:
                logger.info("volume_imbalance 范围检查通过 ✓")

        # 检查价格是否为正（排除对数收益率和趋势因子，因为它们可以为负）
        price_columns = [col for col in self.df.columns
                        if 'price' in col.lower()
                        and 'log_return' not in col.lower()
                        and 'trend' not in col.lower()]
        for col in price_columns:
            negative_count = self.df.filter(pl.col(col) <= 0).shape[0]
            if negative_count > 0:
                issues.append({
                    "问题": f"{col} 存在非正值",
                    "影响行数": negative_count,
                    "比例": f"{negative_count/len(self.df)*100:.2f}%"
                })
                logger.error(f"{col} 存在 {negative_count} 个非正值 ✗")

        # 检查无穷值
        inf_count = 0
        for col in self.df.columns:
            if self.df[col].dtype in [pl.Float32, pl.Float64]:
                inf_in_col = self.df.filter(pl.col(col).is_infinite()).shape[0]
                if inf_in_col > 0:
                    inf_count += inf_in_col
                    issues.append({
                        "问题": f"{col} 存在无穷值",
                        "影响行数": inf_in_col,
                        "比例": f"{inf_in_col/len(self.df)*100:.2f}%"
                    })

        if inf_count > 0:
            logger.error(f"发现 {inf_count} 个无穷值 ✗")
        else:
            logger.info("无穷值检查通过 ✓")

        result = {
            "问题数": len(issues),
            "问题列表": issues
        }

        self.validation_results['data_ranges'] = result
        return result

    def check_statistics(self) -> Dict:
        """
        计算统计信息

        Returns:
            统计信息
        """
        logger.info("\n" + "="*60)
        logger.info("6. 统计信息")
        logger.info("="*60)

        stats = {}

        # 关键因子的统计
        key_features = [
            'volume_imbalance', 'price_spread', 'wap_1',
            'kmid', 'klen', 'buy_vwap', 'sell_vwap'
        ]

        logger.info("\n关键因子统计:")
        for feat in key_features:
            if feat in self.df.columns:
                col_stats = self.df[feat].describe()
                stats[feat] = {
                    "均值": float(self.df[feat].mean()),
                    "标准差": float(self.df[feat].std()),
                    "最小值": float(self.df[feat].min()),
                    "最大值": float(self.df[feat].max())
                }
                logger.info(f"\n{feat}:")
                logger.info(f"  均值: {stats[feat]['均值']:.6f}")
                logger.info(f"  标准差: {stats[feat]['标准差']:.6f}")
                logger.info(f"  范围: [{stats[feat]['最小值']:.6f}, {stats[feat]['最大值']:.6f}]")

        self.validation_results['statistics'] = stats
        return stats

    def check_time_continuity(self) -> Dict:
        """
        检查时间连续性

        Returns:
            时间连续性检查结果
        """
        logger.info("\n" + "="*60)
        logger.info("7. 时间连续性检查")
        logger.info("="*60)

        if 'timestamp' not in self.df.columns:
            logger.warning("没有 timestamp 列，跳过时间连续性检查")
            return {}

        # 计算时间差
        df_sorted = self.df.sort("timestamp")
        time_diffs = df_sorted["timestamp"].diff()

        # 统计时间间隔
        expected_interval = pl.duration(minutes=1)

        # 找出异常间隔
        if len(time_diffs) > 1:
            # 跳过第一个（因为diff的第一个值是null）
            non_null_diffs = time_diffs[1:]

            # 注意：这里需要根据实际数据类型调整
            logger.info(f"总时间点数: {len(df_sorted)}")
            logger.info(f"时间范围: {df_sorted['timestamp'].min()} 至 {df_sorted['timestamp'].max()}")

        result = {
            "总时间点数": len(df_sorted),
            "起始时间": str(df_sorted['timestamp'].min()),
            "结束时间": str(df_sorted['timestamp'].max())
        }

        self.validation_results['time_continuity'] = result
        return result

    def generate_report(self) -> str:
        """
        生成验证报告

        Returns:
            报告文本
        """
        logger.info("\n" + "="*60)
        logger.info("生成验证报告")
        logger.info("="*60)

        report_lines = []
        from datetime import datetime
        report_lines.append("="*80)
        report_lines.append("特征数据验证报告")
        report_lines.append("="*80)
        report_lines.append(f"文件路径: {self.file_path}")
        report_lines.append(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # 1. 基本信息
        if 'basic_info' in self.validation_results:
            info = self.validation_results['basic_info']
            report_lines.append("1. 基本信息")
            report_lines.append(f"   - 数据行数: {info['行数']:,}")
            report_lines.append(f"   - 数据列数: {info['列数']}")
            report_lines.append(f"   - 文件大小: {info['文件大小']}")
            report_lines.append("")

        # 2. 列完整性
        if 'required_columns' in self.validation_results:
            status = "✓ 通过" if self.validation_results['required_columns'] else "✗ 失败"
            report_lines.append(f"2. 必需列检查: {status}")
            report_lines.append("")

        # 3. 因子完整性
        if 'feature_columns' in self.validation_results:
            result = self.validation_results['feature_columns']
            status = "✓ 通过" if len(result['缺失因子']) == 0 else "✗ 失败"
            report_lines.append(f"3. 因子列检查: {status}")
            report_lines.append(f"   - 预期: {result['预期因子数']} 个")
            report_lines.append(f"   - 实际: {result['实际因子数']} 个")
            if result['缺失因子']:
                report_lines.append(f"   - 缺失: {len(result['缺失因子'])} 个")
            report_lines.append("")

        # 4. 空值
        if 'null_values' in self.validation_results:
            result = self.validation_results['null_values']
            report_lines.append("4. 空值检查")
            report_lines.append(f"   - 总空值数: {result['总空值数']:,}")
            report_lines.append(f"   - 有空值的列: {result['有空值的列数']} 个")
            report_lines.append("")

        # 5. 数据范围
        if 'data_ranges' in self.validation_results:
            result = self.validation_results['data_ranges']
            status = "✓ 通过" if result['问题数'] == 0 else f"✗ 发现 {result['问题数']} 个问题"
            report_lines.append(f"5. 数据范围检查: {status}")
            if result['问题列表']:
                for issue in result['问题列表'][:5]:  # 只显示前5个
                    report_lines.append(f"   - {issue['问题']}: {issue['影响行数']} 行")
            report_lines.append("")

        # 总结
        report_lines.append("="*80)
        total_issues = (
            (0 if self.validation_results.get('required_columns', False) else 1) +
            len(self.validation_results.get('feature_columns', {}).get('缺失因子', [])) +
            self.validation_results.get('data_ranges', {}).get('问题数', 0)
        )

        if total_issues == 0:
            report_lines.append("验证结果: ✓ 全部通过")
        else:
            report_lines.append(f"验证结果: ✗ 发现 {total_issues} 个问题")

        report_lines.append("="*80)

        report = "\n".join(report_lines)
        return report

    def run_all_checks(self) -> bool:
        """
        运行所有检查

        Returns:
            是否全部通过
        """
        if not self.load_data():
            return False

        self.check_basic_info()
        self.check_required_columns()
        self.check_feature_columns()
        self.check_null_values()
        self.check_data_ranges()
        self.check_statistics()
        self.check_time_continuity()

        # 生成报告
        report = self.generate_report()
        print("\n" + report)

        # 保存报告
        report_path = self.file_path.parent / f"{self.file_path.stem}_validation_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"\n报告已保存到: {report_path}")

        # 判断是否通过
        total_issues = (
            (0 if self.validation_results.get('required_columns', False) else 1) +
            len(self.validation_results.get('feature_columns', {}).get('缺失因子', [])) +
            self.validation_results.get('data_ranges', {}).get('问题数', 0)
        )

        return total_issues == 0


def find_output_files(output_dir: Path = FEATURES_OUTPUT_DIR) -> List[Path]:
    """
    查找输出目录中的所有特征文件

    Args:
        output_dir: 输出目录

    Returns:
        文件路径列表
    """
    if not output_dir.exists():
        logger.error(f"输出目录不存在: {output_dir}")
        return []

    # 查找所有 parquet、feather 和 csv 文件
    parquet_files = list(output_dir.glob("*.parquet"))
    feather_files = list(output_dir.glob("*.feather"))
    logger.error(f"输出目录{output_dir}文件: {feather_files}")
    csv_files = list(output_dir.glob("*.csv"))

    all_files = parquet_files + feather_files + csv_files
    all_files.sort()

    return all_files


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='验证特征数据集')
    parser.add_argument('--file', type=str, help='指定要验证的文件路径')
    parser.add_argument('--dir', type=str, default=str(FEATURES_OUTPUT_DIR),
                        help='输出目录路径（默认从配置读取）')
    parser.add_argument('--all', action='store_true',
                        help='验证目录中的所有文件')

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("特征数据验证工具")
    logger.info("="*80)

    if args.file:
        # 验证指定文件
        file_path = Path(args.file)
        validator = FeatureValidator(file_path)
        success = validator.run_all_checks()
        return 0 if success else 1

    elif args.all:
        # 验证所有文件
        output_dir = Path("output/features")
        logger.info(f"目录 {output_dir}")
        files = find_output_files(output_dir)

        if not files:
            logger.error("没有找到任何输出文件")
            return 1

        logger.info(f"找到 {len(files)} 个文件")

        all_passed = True
        for i, file_path in enumerate(files, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"验证文件 {i}/{len(files)}: {file_path.name}")
            logger.info(f"{'='*80}")

            validator = FeatureValidator(file_path)
            if not validator.run_all_checks():
                all_passed = False

        logger.info("\n" + "="*80)
        if all_passed:
            logger.info("所有文件验证通过 ✓")
        else:
            logger.warning("部分文件验证失败 ✗")
        logger.info("="*80)

        return 0 if all_passed else 1

    else:
        # 查找并让用户选择
        output_dir = Path(args.dir)
        files = find_output_files(output_dir)

        if not files:
            logger.error("没有找到任何输出文件")
            logger.info(f"请先运行 main.py 生成特征数据")
            return 1

        logger.info(f"\n找到 {len(files)} 个文件:")
        for i, file_path in enumerate(files, 1):
            size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"{i}. {file_path.name} ({size_mb:.2f} MB)")

        # 验证第一个文件
        logger.info(f"\n验证: {files[0].name}")
        validator = FeatureValidator(files[0])
        success = validator.run_all_checks()

        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
