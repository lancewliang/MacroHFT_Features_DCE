# 高频交易因子特征处理需求文档

## 一、数据源说明

### 1.0 数据概览
- **交易对**: ETHUSDT (以太坊永续合约)
- **数据类型**: Binance 期货数据
- **数据时间范围**: 2023年01月01日 - 2026年01月01日 (约3年)
- **数据粒度**: 分钟级别
- **存储格式**: ZIP 压缩文件（每日一个文件）

### 1.1 订单簿深度数据 (Order Book Depth)
- **数据目录**: `data/futures/um/daily/bookDepth/ETHUSDT/`
- **文件格式**: `ETHUSDT-bookDepth-YYYY-MM-DD.zip`
  - 示例：`ETHUSDT-bookDepth-2023-06-30.zip`
- **文件结构**:
  - 每个 ZIP 文件包含一个 CSV 文件
  - CSV 文件名格式：`ETHUSDT-bookDepth-YYYY-MM-DD.csv`
- **示例数据**: `biance_example/bookdepth.csv` (仅供参考)
- **CSV 数据格式**:
  ```
  timestamp, percentage, depth, notional
  ```
- **字段说明**:
  - `timestamp`: 时间戳（分钟级别）
  - `percentage`: 档位标识
    - `-5, -4, -3, -2, -1`: 买方五档（bid1-bid5）
    - `1, 2, 3, 4, 5`: 卖方五档（ask1-ask5）
  - `depth`: 订单深度（订单数量）
  - `notional`: 名义价值（订单金额）
- **数据特征**:
  - 每个时间戳对应 10 行数据（5个买档 + 5个卖档）
  - 以分钟为单位进行聚合/采样
  - 每日数据量：约 14,400 行 (1440分钟 × 10档位)

### 1.2 K线数据 (Kline/Candlestick)
- **数据目录**: `data/futures/um/daily/klines/ETHUSDT/1m/`
- **文件格式**: `ETHUSDT-1m-YYYY-MM-DD.zip`
  - 示例：`ETHUSDT-1m-2023-06-30.zip`
- **文件结构**:
  - 每个 ZIP 文件包含一个 CSV 文件
  - CSV 文件名格式：`ETHUSDT-1m-YYYY-MM-DD.csv`
- **示例数据**: `biance_example/kline.csv` (仅供参考)
- **CSV 数据格式**:
  ```
  open_time, open, high, low, close, volume, close_time, quote_volume, count,
  taker_buy_volume, taker_buy_quote_volume, ignore
  ```
- **字段说明**:
  - `open_time`: 开盘时间（Unix时间戳，毫秒）
  - `open`: 开盘价
  - `high`: 最高价
  - `low`: 最低价
  - `close`: 收盘价
  - `volume`: 成交量
  - `close_time`: 收盘时间（Unix时间戳，毫秒）
  - `quote_volume`: 计价货币成交量
  - `count`: 成交笔数
  - `taker_buy_volume`: 主动买入成交量
  - `taker_buy_quote_volume`: 主动买入计价货币成交量
  - `ignore`: 忽略字段
- **数据特征**:
  - 每行代表1分钟的K线数据
  - 一分钟一行
  - 每日数据量：约 1,440 行 (1440分钟)

### 1.3 数据处理范围
- **起始日期**: 2023-01-01
- **结束日期**: 2026-01-01
- **总天数**: 约 1,096 天 (3年)
- **预估数据量**:
  - 订单簿数据：约 1,577万行 (1096天 × 1440分钟 × 10档)
  - K线数据：约 158万行 (1096天 × 1440分钟)
  - 最终因子数据：约 158万行 × 62列

---

## 二、数据处理流程

### 2.0 数据读取与解压
**任务**: 从 ZIP 文件中读取每日数据并合并

**处理步骤**:
1. **遍历日期范围** (2023-01-01 到 2026-01-01)
2. **订单簿数据读取**:
   - 构建文件路径：`data/futures/um/daily/bookDepth/ETHUSDT/ETHUSDT-bookDepth-{date}.zip`
   - 从 ZIP 中读取 CSV 文件（无需解压到磁盘）
   - 使用 Polars 的 `read_csv()` 直接读取压缩文件
3. **K线数据读取**:
   - 构建文件路径：`data/futures/um/daily/klines/ETHUSDT/1m/ETHUSDT-1m-{date}.zip`
   - 从 ZIP 中读取 CSV 文件
4. **数据合并策略**:
   - 选项 A：逐日处理（内存效率高，适合大数据集）
   - 选项 B：全量读取后处理（速度快，需要更多内存）

**Polars 读取 ZIP 示例**:
```python
import polars as pl
from pathlib import Path

# 方法1：直接读取 ZIP 文件（推荐）
df = pl.read_csv("data/futures/um/daily/bookDepth/ETHUSDT/ETHUSDT-bookDepth-2023-06-30.zip")

# 方法2：使用 Python zipfile 模块
import zipfile
with zipfile.ZipFile(zip_path) as z:
    with z.open(csv_filename) as f:
        df = pl.read_csv(f)
```

**输出**:
- 订单簿 DataFrame: 包含所有日期的订单簿数据
- K线 DataFrame: 包含所有日期的K线数据

### 2.1 订单簿数据预处理
**任务**: 将订单簿深度数据转换为宽表格式

**输入**:
- 原始 bookdepth 数据（长格式，每个时间戳10行）

**处理步骤**:
1. 按 `timestamp` 分组
2. 将 `percentage` 列透视为列名
3. 从 `depth` 和 `notional` 计算价格：
   - `bid1_price = notional / depth` (percentage == -1)
   - `bid1_size = depth` (percentage == -1)
   - `ask1_price = notional / depth` (percentage == 1)
   - `ask1_size = depth` (percentage == 1)
   - 同理计算 bid2-bid5 和 ask2-ask5

**输出**:
```
timestamp, bid1_price, bid1_size, bid2_price, bid2_size, ..., ask5_price, ask5_size
```

### 2.2 K线数据预处理
**任务**: 提取K线基础数据

**输入**:
- 原始 kline.csv

**处理步骤**:
1. 时间戳转换：将 `open_time` 从毫秒转换为可读的时间格式
2. 提取需要的列：
   - `timestamp`: 从 `open_time` 转换
   - `open_price`: 对应 `open`
   - `high_price`: 对应 `high`
   - `low_price`: 对应 `low`
   - `close_price`: 对应 `close`
3. 保留成交数据（可选，用于后续扩展）:
   - `volume`: 成交量
   - `taker_buy_volume`: 主动买入量
   - `count`: 成交笔数

**输出**:
```
timestamp, open_price, high_price, low_price, close_price, volume, taker_buy_volume, count
```

### 2.3 数据对齐与合并
**任务**: 将订单簿数据和K线数据按时间戳对齐

**处理步骤**:
1. 统一时间戳格式（确保两个数据集的时间戳格式一致）
2. 按 `timestamp` 进行内连接 (inner join)
3. 验证数据完整性（检查缺失值）

**输出**:
```
timestamp, open_price, high_price, low_price, close_price,
bid1_price, bid1_size, ..., ask5_price, ask5_size
```

---

## 三、因子计算

### 3.1 K线特征因子
基于合并后的数据，计算以下K线相关因子（参考 factor.md）:

```python
# 基础变量
max_oc = max(open_price, close_price)
min_oc = min(open_price, close_price)

# K线特征
kmid = close_price - open_price
kmid2 = (close_price - open_price) / (high_price - low_price)
klen = high_price - low_price
kup = high_price - max_oc
kup2 = (high_price - max_oc) / (high_price - low_price)
klow = min_oc - low_price
klow2 = (min_oc - low_price) / (high_price - low_price)
ksft = 2 * close_price - high_price - low_price
ksft2 = ksft / (high_price - low_price)
```

### 3.2 订单簿基础因子
计算订单簿相关的基础特征:

```python
# 总订单量
volume = sum(bid1_size, bid2_size, ..., bid5_size, ask1_size, ..., ask5_size)

# 归一化订单量
bid1_size_n = bid1_size / volume
bid2_size_n = bid2_size / volume
# ... 同理计算其他档位
ask1_size_n = ask1_size / volume
ask2_size_n = ask2_size / volume
# ... 同理计算其他档位
```

### 3.3 加权平均价格因子
```python
# WAP (Weighted Average Price)
wap_1 = (ask1_size * bid1_price + bid1_size * ask1_price) / (ask1_size + bid1_size)
wap_2 = (ask2_size * bid2_price + bid2_size * ask2_price) / (ask2_size + bid2_size)
wap_balance = abs(wap_1 - wap_2)
```

### 3.4 价差因子
```python
buy_spread = abs(bid1_price - bid5_price)
sell_spread = abs(ask1_price - ask5_price)
price_spread = 2 * (ask1_price - bid1_price) / (ask1_price + bid1_price)
```

### 3.5 成交量因子
```python
buy_volume = sum(bid1_size, bid2_size, bid3_size, bid4_size, bid5_size)
sell_volume = sum(ask1_size, ask2_size, ask3_size, ask4_size, ask5_size)
volume_imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume)
```

### 3.6 VWAP因子
```python
sell_vwap = sum(ask_size_n * ask_price for all 5 levels)
buy_vwap = sum(bid_size_n * bid_price for all 5 levels)
```

### 3.7 对数收益率因子（需要历史数据）
```python
# 价格对数收益率（需要 t-1 时刻的数据）
log_return_bid1_price = log(bid1_price[t] / bid1_price[t-1])
log_return_bid2_price = log(bid2_price[t] / bid2_price[t-1])
log_return_ask1_price = log(ask1_price[t] / ask1_price[t-1])
log_return_ask2_price = log(ask2_price[t] / ask2_price[t-1])

# WAP 对数收益率
log_return_wap_1 = log(wap_1[t] / wap_1[t-1])
log_return_wap_2 = log(wap_2[t] / wap_2[t-1])
```

**注意**: 对数收益率需要使用 Polars 的 `shift()` 函数获取前一时刻的值

---

## 四、最终输出

### 4.1 输出数据结构
最终生成的 DataFrame 应包含以下列（按顺序）:

**1. 时间戳**
- `timestamp`

**2. K线原始数据 (4列)**
- `open_price`
- `high_price`
- `low_price`
- `close_price`

**3. 订单簿原始数据 (20列)**
- `bid1_price, bid1_size, bid2_price, bid2_size, ..., bid5_price, bid5_size`
- `ask1_price, ask1_size, ask2_price, ask2_size, ..., ask5_price, ask5_size`

**4. K线特征因子 (9列)**
- `kmid, kmid2, klen, kup, kup2, klow, klow2, ksft, ksft2`

**5. 归一化订单量因子 (11列，包含volume)**
- `volume`
- `bid1_size_n, bid2_size_n, ..., bid5_size_n`
- `ask1_size_n, ask2_size_n, ..., ask5_size_n`

**6. 加权平均价格因子 (3列)**
- `wap_1, wap_2, wap_balance`

**7. 价差因子 (3列)**
- `buy_spread, sell_spread, price_spread`

**8. 成交量因子 (3列)**
- `buy_volume, sell_volume, volume_imbalance`

**9. VWAP因子 (2列)**
- `buy_vwap, sell_vwap`

**10. 对数收益率因子 (6列)**
- `log_return_bid1_price, log_return_bid2_price`
- `log_return_ask1_price, log_return_ask2_price`
- `log_return_wap_1, log_return_wap_2`

**总计**: 1 + 4 + 20 + 9 + 11 + 3 + 3 + 3 + 2 + 6 = **62列**

### 4.2 输出格式
- **数据框**: Polars DataFrame
- **文件格式**: Parquet（推荐，高效压缩和查询）
- **输出目录**: `output/features/`
- **文件命名策略**:
  - **单文件输出**: `features_20230101_20260101.parquet` (全量数据)
  - **分批输出**: `features_YYYYMM.parquet` (按月分割)
  - 示例：`features_202306.parquet`, `features_202307.parquet`
- **推荐方案**: 按月分割，便于增量更新和内存管理

---

## 五、技术要求

### 5.1 编程语言与库
- **主要库**: Polars (代替 Pandas)
- **原因**:
  - 更快的处理速度
  - 更低的内存占用
  - 更好的并行处理能力
  - 懒加载 (Lazy Evaluation) 支持

### 5.2 代码结构建议
```python
import polars as pl
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple

# 1. 数据读取（处理 ZIP 文件）
def load_daily_bookdepth(date: str, base_path: str = "data/futures/um/daily/bookDepth/ETHUSDT") -> pl.DataFrame:
    """读取单日订单簿数据（从ZIP文件）

    Args:
        date: 日期字符串，格式 'YYYY-MM-DD'
        base_path: 数据目录路径

    Returns:
        Polars DataFrame
    """
    pass

def load_daily_kline(date: str, base_path: str = "data/futures/um/daily/klines/ETHUSDT/1m") -> pl.DataFrame:
    """读取单日K线数据（从ZIP文件）

    Args:
        date: 日期字符串，格式 'YYYY-MM-DD'
        base_path: 数据目录路径

    Returns:
        Polars DataFrame
    """
    pass

def load_date_range(start_date: str, end_date: str) -> List[pl.DataFrame]:
    """加载日期范围内的所有数据

    Args:
        start_date: 起始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'

    Returns:
        (bookdepth_dfs, kline_dfs) 元组
    """
    pass

# 2. 数据转换
def pivot_bookdepth(df: pl.DataFrame) -> pl.DataFrame:
    """将订单簿长格式转为宽格式

    输入: timestamp, percentage, depth, notional (长格式)
    输出: timestamp, bid1_price, bid1_size, ..., ask5_price, ask5_size (宽格式)
    """
    pass

def preprocess_kline(df: pl.DataFrame) -> pl.DataFrame:
    """预处理K线数据，提取需要的列并转换时间戳"""
    pass

def merge_data(bookdepth_df: pl.DataFrame, kline_df: pl.DataFrame) -> pl.DataFrame:
    """按时间戳合并订单簿和K线数据"""
    pass

# 3. 因子计算
def calculate_kline_features(df: pl.DataFrame) -> pl.DataFrame:
    """计算K线特征因子

    计算: kmid, kmid2, klen, kup, kup2, klow, klow2, ksft, ksft2
    """
    pass

def calculate_orderbook_features(df: pl.DataFrame) -> pl.DataFrame:
    """计算订单簿特征因子

    计算: volume, size_n, wap, spreads, volume_imbalance, vwap
    """
    pass

def calculate_log_returns(df: pl.DataFrame) -> pl.DataFrame:
    """计算对数收益率因子

    计算: log_return_bid1_price, log_return_ask1_price, log_return_wap_1, etc.
    """
    pass

# 4. 主函数
def generate_features(
    start_date: str = "2023-01-01",
    end_date: str = "2026-01-01",
    output_path: str = "output/features.parquet",
    batch_size: int = 30  # 每次处理30天
) -> None:
    """完整的特征生成流程

    Args:
        start_date: 起始日期
        end_date: 结束日期
        output_path: 输出文件路径
        batch_size: 批处理大小（天数）
    """
    pass
```

### 5.3 性能优化建议
1. 使用 Polars 的懒加载模式 (`pl.scan_csv()`)
2. 链式操作减少中间变量
3. 使用向量化操作避免循环
4. 对大数据集考虑分批处理

---

## 六、数据验证与质量控制

### 6.1 数据完整性检查
- [ ] 检查时间戳是否连续（有无缺失分钟）
- [ ] 检查是否有空值 (null values)
- [ ] 验证订单簿数据每个时间戳是否有完整的10档数据

### 6.2 因子合理性检查
- [ ] `price_spread > 0` (买卖价差应为正)
- [ ] `volume_imbalance` 在 [-1, 1] 范围内
- [ ] `bid1_price < ask1_price` (买价应低于卖价)
- [ ] 所有归一化因子之和应接近 1
- [ ] 检查是否有 inf 或 nan 值（除法时可能出现）

### 6.3 异常值处理
- 价格或数量为 0 或负数的记录
- 极端的价差或订单量
- 除零错误处理（如 `high_price == low_price` 时的比率计算）

---

## 七、可选扩展功能

### 7.1 成交数据特征（来自 kline）
虽然 factor.md 中未提及，但 kline 数据包含成交信息，可以扩展：

```python
# 成交量特征
trade_volume = volume
taker_buy_ratio = taker_buy_volume / volume  # 主动买入占比
trade_count = count  # 成交笔数
avg_trade_size = volume / count  # 平均每笔成交量

# 成交不平衡（基于真实成交）
taker_sell_volume = volume - taker_buy_volume
trade_imbalance = (taker_buy_volume - taker_sell_volume) / volume
```

### 7.2 滚动窗口特征
```python
# 5分钟滚动均值
wap_1_ma5 = wap_1.rolling_mean(window_size=5)
volume_imbalance_ma5 = volume_imbalance.rolling_mean(window_size=5)

# 5分钟滚动标准差（波动率）
price_volatility_5min = close_price.rolling_std(window_size=5)
```

### 7.3 时间特征
```python
hour = timestamp.hour
minute = timestamp.minute
day_of_week = timestamp.day_of_week
```

---

## 八、交付物清单

### 8.1 代码文件
- [ ] `data_loader.py`: 数据读取模块
- [ ] `feature_calculator.py`: 因子计算模块
- [ ] `main.py`: 主执行脚本
- [ ] `config.py`: 配置文件（路径、参数等）
- [ ] `requirements.txt`: 依赖包列表
- [ ] 代码目录为 src/gen_features

### 8.2 文档文件
- [ ] `factor.md`: 因子公式说明（已有）
- [ ] `factor-desc.md`: 因子详细描述（已有）
- [ ] `README.md`: 使用说明
- [ ] `API.md`: 函数接口文档

### 8.3 测试与示例
- [ ] 单元测试脚本
- [ ] 示例运行脚本
- [ ] 输出数据样例

---

## 九、项目里程碑

### Phase 1: 基础功能
- [ ] 数据读取与预处理
- [ ] 订单簿宽表转换
- [ ] K线数据对齐
- [ ] 基础因子计算（不含对数收益率）

### Phase 2: 完整因子
- [ ] 对数收益率因子
- [ ] 数据验证与异常处理
- [ ] 输出功能

### Phase 3: 优化与扩展
- [ ] 性能优化
- [ ] 可选扩展功能
- [ ] 文档完善

---

## 十、注意事项

1. **时间对齐**: bookdepth 和 kline 的时间戳格式不同，需要统一
2. **除零保护**: 计算比率时需要处理分母为0的情况
3. **第一行数据**: 对数收益率因子在第一行会缺失（无 t-1 数据）
4. **数据类型**: 使用 Polars 的适当数据类型（Float64, Int64等）
5. **内存管理**: 对于大规模数据，考虑分批处理或使用懒加载

---

## 十一、参考文档

- [factor.md](factor.md): 因子计算公式
- [factor-desc.md](factor-desc.md): 因子详细说明
- [Polars Documentation](https://pola-rs.github.io/polars-book/)
