# 高频交易因子生成系统

一个基于 Polars 的高性能高频交易因子计算工具，用于从 Binance 期货订单簿和 K线数据生成机器学习特征。

## 功能特性

- 从 ZIP 压缩文件直接读取数据，无需解压
- 支持大规模数据处理（3年+日级数据）
- 高性能：使用 Polars 代替 Pandas
- 灵活的输出策略：单文件或按月分割
- 完整的数据验证和质量检查
- 62个精心设计的因子特征

## 数据源

- **交易对**: ETHUSDT
- **数据类型**: Binance 期货数据
- **时间范围**: 2023-01-01 至 2026-01-01
- **数据粒度**: 分钟级

### 数据目录结构

```
data/
├── futures/
│   └── um/
│       └── daily/
│           ├── bookDepth/
│           │   └── ETHUSDT/
│           │       └── ETHUSDT-bookDepth-YYYY-MM-DD.zip
│           └── klines/
│               └── ETHUSDT/
│                   └── 1m/
│                       └── ETHUSDT-1m-YYYY-MM-DD.zip
```

## 因子类别

### 1. K线特征因子 (9个)
- `kmid`, `kmid2`, `klen`, `kup`, `kup2`, `klow`, `klow2`, `ksft`, `ksft2`

### 2. 归一化订单量因子 (11个)
- `volume`, `bid1_size_n` ~ `bid5_size_n`, `ask1_size_n` ~ `ask5_size_n`

### 3. 加权平均价格因子 (3个)
- `wap_1`, `wap_2`, `wap_balance`

### 4. 价差因子 (3个)
- `buy_spread`, `sell_spread`, `price_spread`

### 5. 成交量因子 (3个)
- `buy_volume`, `sell_volume`, `volume_imbalance`

### 6. VWAP因子 (2个)
- `buy_vwap`, `sell_vwap`

### 7. 对数收益率因子 (6个)
- `log_return_bid1_price`, `log_return_bid2_price`, `log_return_ask1_price`,
  `log_return_ask2_price`, `log_return_wap_1`, `log_return_wap_2`

**总计**: 62列（包含时间戳、原始价格和因子）

## 安装

```bash
# 安装依赖
pip install -r requirements.txt
```

## 快速开始

### 1. 基本用法

```bash
# 使用默认配置（按月输出）
python main.py

# 指定日期范围
python main.py --start-date 2023-01-01 --end-date 2023-12-31

# 使用单文件输出策略
python main.py --strategy single

# 调整批处理大小
python main.py --batch-size 60 --strategy single

# 设置日志级别
python main.py --log-level DEBUG
```

### 2. Python API 用法

```python
from data_loader import load_date_range_data, pivot_bookdepth, preprocess_kline, merge_data
from feature_calculator import calculate_all_features

# 加载数据
bookdepth_df, kline_df = load_date_range_data("2023-06-01", "2023-06-30")

# 数据转换
bookdepth_wide = pivot_bookdepth(bookdepth_df)
kline_processed = preprocess_kline(kline_df)

# 合并数据
merged_df = merge_data(bookdepth_wide, kline_processed)

# 计算因子
features_df = calculate_all_features(merged_df)

# 保存结果
features_df.write_parquet("output/features_202306.parquet")
```

### 3. 单独计算特定因子

```python
from feature_calculator import (
    calculate_kline_features,
    calculate_wap_features,
    calculate_volume_features
)

# 只计算K线特征
df = calculate_kline_features(merged_df)

# 只计算WAP特征
df = calculate_wap_features(df)

# 只计算成交量特征
df = calculate_volume_features(df)
```

## 配置

主要配置在 [config.py](config.py) 中：

```python
# 数据路径
BOOKDEPTH_BASE_PATH = "data/futures/um/daily/bookDepth/ETHUSDT"
KLINE_BASE_PATH = "data/futures/um/daily/klines/ETHUSDT/1m"

# 时间范围
START_DATE = "2023-01-01"
END_DATE = "2026-01-01"

# 输出配置
OUTPUT_FORMAT = "parquet"  # 或 "csv"
OUTPUT_STRATEGY = "monthly"  # 或 "single"
BATCH_SIZE_DAYS = 30

# 数据验证
ENABLE_DATA_VALIDATION = True
```

## 输出

### 按月输出（推荐）
```
output/
└── features/
    ├── features_202301.parquet
    ├── features_202302.parquet
    ├── features_202303.parquet
    └── ...
```

### 单文件输出
```
output/
└── features/
    └── features_20230101_20260101.parquet
```

## 性能优化

1. **使用 Parquet 格式**: 比 CSV 快 10-100倍，且文件更小
2. **批处理**: 通过 `--batch-size` 调整内存使用
3. **懒加载**: Polars 自动优化查询
4. **并行处理**: Polars 内部自动并行化

## 数据验证

系统自动执行以下验证：

- 检查空值
- 验证 `bid1_price < ask1_price`
- 检查价格和数量是否为正
- 验证 `volume_imbalance` 在 [-1, 1] 范围内
- 检查无穷值和 NaN

## 日志

日志文件保存在:
```
logs/feature_generation_YYYYMMDD_HHMMSS.log
```

## 测试

### 运行前测试（模块测试）

在运行 main.py 之前，建议先运行模块测试确保所有组件正常工作：

```bash
# 测试所有模块
python test_modules.py
```

这将测试：
- ✓ 配置模块
- ✓ 数据加载模块
- ✓ 因子计算模块
- ✓ 完整流程集成测试

如果所有测试通过，说明代码正常，可以运行 main.py。

### 运行后验证（结果测试）

运行 main.py 生成数据后，使用验证脚本检查结果质量：

```bash
# 验证指定文件
python test_results.py --file output/features/features_202306.parquet

# 验证所有输出文件
python test_results.py --all

# 验证指定目录中的文件
python test_results.py --dir output/features
```

验证内容包括：
1. **基本信息检查**: 行数、列数、文件大小
2. **必需列检查**: 所有必需列是否存在
3. **因子列检查**: 62个因子是否完整
4. **空值检查**: 统计空值数量和分布
5. **数据范围检查**:
   - bid1_price < ask1_price
   - volume_imbalance ∈ [-1, 1]
   - 价格为正
   - 无无穷值
6. **统计信息**: 关键因子的均值、标准差、范围
7. **时间连续性**: 检查时间戳

验证报告会自动保存到与数据文件相同的目录，文件名为 `*_validation_report.txt`。

## 故障排除

### 内存不足
```bash
# 减小批处理大小
python main.py --batch-size 10
```

### 文件不存在
```bash
# 检查数据目录结构
ls -lh data/futures/um/daily/bookDepth/ETHUSDT/
ls -lh data/futures/um/daily/klines/ETHUSDT/1m/
```

### 数据验证失败
```bash
# 查看详细日志
tail -f logs/feature_generation_*.log

# 运行结果验证
python test_results.py --file <生成的文件>
```

### 模块导入错误
```bash
# 确保在正确的目录
cd src/gen

# 或者将目录添加到 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/home/lanceliang/opt/aiwork/MacroHFT_Features/src/gen"
```

## 项目结构

```
src/gen/
├── __init__.py              # 包初始化
├── config.py                # 配置文件
├── data_loader.py           # 数据读取模块
├── feature_calculator.py    # 因子计算模块
├── main.py                  # 主执行脚本
├── requirements.txt         # 依赖包
└── README.md               # 本文件
```

## 依赖

- Python >= 3.8
- Polars >= 0.20.0
- NumPy >= 1.24.0

## 相关文档

- [freatures_process.md](../../docs/freatures_process.md) - 详细的需求文档
- [factor.md](../../docs/factor.md) - 因子公式说明
- [factor-desc.md](../../docs/factor-desc.md) - 因子详细描述

## 许可证

内部项目

## 作者

MacroHFT Features Team
