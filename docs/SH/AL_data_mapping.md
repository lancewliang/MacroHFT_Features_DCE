# SH 铝原始数据列说明及字段映射关系

本文档按当前 SH/AL 数据样例、预处理脚本和因子实现说明字段映射关系。

适用范围：

- 原始样例文件：[AL_example.csv](./AL_example.csv)
- 原始字段说明：[原始五档行情数据.md](./原始五档行情数据.md)
- 因子定义：[target_factor.md](./target_factor.md)
- 因子解释：[factor-desc.md](./factor-desc.md)

---

## 一、当前实现的数据处理链路

当前 SH/AL 因子生成并不是直接从原始交易所 CSV 计算因子，而是分成两步：

```text
原始五档行情 CSV
    ↓
scripts/step4_preprocess_order_files_v2.py
    ↓
按 10s / 20s / 30s / 1m 聚合后的 orderbook CSV
    ↓
src/gen/data_loader.py
    ↓
src/gen/feature_calculator.py
    ↓
最终特征数据
```

这意味着字段映射需要区分两层：

1. 原始五档行情字段 -> 聚合后的 orderbook 基础字段
2. orderbook 基础字段 -> target factor 衍生因子

---

## 二、原始文件与样例文件

### 2.1 原始字段说明文档中的标准字段

[`原始五档行情数据.md`](./原始五档行情数据.md) 描述了一套较完整的五档行情字段，包含：

- 时间字段：`ActionDay`、`TradingDay`、`UpdateTime`
- 成交相关字段：`LastPrice`、`OpenPrice`、`HighPrice`、`LowPrice`、`ClosePrice`、`Volume`、`Turnover` 等
- 五档盘口字段：`BidPrice1~5`、`BidVolume1~5`、`AskPrice1~5`、`AskVolume1~5`
- 部分扩展字段：`DerBidVolume*`、`DerAskVolume*`、`BuyVolume`、`SellVolume`、`AvgBuyPrice`、`AvgSellPrice`、`LifeHighPrice`、`LifeLowPrice`

### 2.2 AL 样例文件的实际字段

[`AL_example.csv`](./AL_example.csv) 当前样例头部实际包含以下字段：

```text
InstrumentID, TradingDay, ActionDay, UpdateTime,
LastPrice, PreSettlementPrice, PreClosePrice, PreOpenInterest,
OpenPrice, HighPrice, LowPrice, Volume, Turnover, OpenInterest,
ClosePrice, SettlementPrice, UpperLimitPrice, LowerLimitPrice,
PreDelta, CurrDelta, AveragePrice,
BidPrice1, BidVolume1, BidPrice2, BidVolume2, BidPrice3, BidVolume3, BidPrice4, BidVolume4, BidPrice5, BidVolume5,
AskPrice1, AskVolume1, AskPrice2, AskVolume2, AskPrice3, AskVolume3, AskPrice4, AskVolume4, AskPrice5, AskVolume5
```

说明：

- 样例文件中没有 `LastVolume`
- 样例文件中没有 `DerBidVolume*` / `DerAskVolume*`
- 样例文件中没有 `BuyVolume` / `SellVolume` / `AvgBuyPrice` / `AvgSellPrice`
- 样例文件中多出 `PreDelta` / `CurrDelta`

因此，SH/AL 实际使用的原始 schema 是“交易所完整字段定义”的一个子集，而不是完全等同于说明文档中的 57 列版本。

---

## 三、原始字段到 orderbook 基础字段的映射

### 3.1 时间字段

当前预处理脚本 [`step4_preprocess_order_files_v2.py`](../../scripts/step4_preprocess_order_files_v2.py) 使用：

```text
datetime = ActionDay + UpdateTime
```

不是：

```text
TradingDay + UpdateTime
```

原因：

- `ActionDay` 对应实际交易发生日期
- `TradingDay` 在夜盘场景下更接近结算日/交易归属日
- 样例中夜盘数据存在 `TradingDay != ActionDay`

因此当前实现的时间相关字段映射为：

| 目标字段 | 来源原始字段 | 当前实现 | 说明 |
|---------|-------------|---------|-----|
| `datetime` | `ActionDay` + `UpdateTime` | 直接拼接后解析 | 原始快照时间 |
| `minute` | `datetime` | `dt.truncate(interval)` | 聚合窗口起点 |
| `timestamp` | `datetime` | 在 `data_loader.py` 中从 `datetime` 解析得到 | 后续统一时间列 |

### 3.2 OHLC 字段

当前实现中，`open_price/high_price/low_price/close_price` 不是直接使用原始 CSV 的 `OpenPrice/HighPrice/LowPrice/ClosePrice`，也不是来自另一份“期货成交量统计”文件，而是由预处理脚本按窗口聚合得到：

| 目标字段 | 当前实现 | 说明 |
|---------|---------|-----|
| `open_price` | 当前窗口内第一条 `LastPrice` | 窗口开盘价 |
| `close_price` | 当前窗口内最后一条 `LastPrice` | 窗口收盘价 |
| `high_price` | 当前窗口内所有五档 bid/ask 价格的最大值 | 窗口最高价 |
| `low_price` | 当前窗口内所有五档 bid/ask 价格的最小值 | 窗口最低价 |

对应实现位置：

- 时间拼接：[step4_preprocess_order_files_v2.py](../../scripts/step4_preprocess_order_files_v2.py)
- 聚合逻辑：[step4_preprocess_order_files_v2.py](../../scripts/step4_preprocess_order_files_v2.py)

### 3.3 五档盘口字段

原始字段到 orderbook 基础字段的映射如下：

| orderbook 字段 | 原始字段 | 说明 |
|---------------|---------|-----|
| `bid1_price` | `BidPrice1` | 买一价 |
| `bid2_price` | `BidPrice2` | 买二价 |
| `bid3_price` | `BidPrice3` | 买三价 |
| `bid4_price` | `BidPrice4` | 买四价 |
| `bid5_price` | `BidPrice5` | 买五价 |
| `bid1_size` | `BidVolume1` | 买一量 |
| `bid2_size` | `BidVolume2` | 买二量 |
| `bid3_size` | `BidVolume3` | 买三量 |
| `bid4_size` | `BidVolume4` | 买四量 |
| `bid5_size` | `BidVolume5` | 买五量 |
| `ask1_price` | `AskPrice1` | 卖一价 |
| `ask2_price` | `AskPrice2` | 卖二价 |
| `ask3_price` | `AskPrice3` | 卖三价 |
| `ask4_price` | `AskPrice4` | 卖四价 |
| `ask5_price` | `AskPrice5` | 卖五价 |
| `ask1_size` | `AskVolume1` | 卖一量 |
| `ask2_size` | `AskVolume2` | 卖二量 |
| `ask3_size` | `AskVolume3` | 卖三量 |
| `ask4_size` | `AskVolume4` | 卖四量 |
| `ask5_size` | `AskVolume5` | 卖五量 |

### 3.4 聚合后基础字段汇总

当前 orderbook 文件中，因子计算依赖的基础字段通常包括：

```text
timestamp,
open_price, high_price, low_price, close_price,
bid1_price, bid1_size, bid2_price, bid2_size, bid3_price, bid3_size, bid4_price, bid4_size, bid5_price, bid5_size,
ask1_price, ask1_size, ask2_price, ask2_size, ask3_price, ask3_size, ask4_price, ask4_size, ask5_price, ask5_size
```

补充字段：

- `datetime`
- `minute`
- `is_consecutive_minute`
- `contract`
- `date`

---

## 四、基础字段到 target factor 的映射

### 4.1 直接使用的基础字段

| target factor 基础字段 | 来源 | 说明 |
|-----------------------|------|-----|
| `timestamp` | `datetime` 解析 | 统一时间列 |
| `open_price` | 聚合窗口第一条 `LastPrice` | 基础 K 线价 |
| `high_price` | 聚合窗口盘口最大价 | 基础 K 线价 |
| `low_price` | 聚合窗口盘口最小价 | 基础 K 线价 |
| `close_price` | 聚合窗口最后一条 `LastPrice` | 基础 K 线价 |
| `bid1_price ~ bid5_price` | `BidPrice1 ~ BidPrice5` | 买方五档价格 |
| `bid1_size ~ bid5_size` | `BidVolume1 ~ BidVolume5` | 买方五档数量 |
| `ask1_price ~ ask5_price` | `AskPrice1 ~ AskPrice5` | 卖方五档价格 |
| `ask1_size ~ ask5_size` | `AskVolume1 ~ AskVolume5` | 卖方五档数量 |

### 4.2 K 线特征

| 因子名称 | 计算公式 | 说明 |
|---------|---------|-----|
| `kmid` | `close_price - open_price` | K 线实体方向 |
| `kmid2` | `(close_price - open_price) / (high_price - low_price)` | K 线实体归一化比率 |
| `klen` | `high_price - low_price` | K 线总振幅 |
| `kup` | `high_price - max(open_price, close_price)` | 上影线长度 |
| `kup2` | `kup / klen` | 上影线归一化比率 |
| `klow` | `min(open_price, close_price) - low_price` | 下影线长度 |
| `klow2` | `klow / klen` | 下影线归一化比率 |
| `ksft` | `2 * close_price - high_price - low_price` | 收盘位置偏移 |
| `ksft2` | `ksft / klen` | 收盘位置归一化偏移 |

说明：

- `max_oc` / `min_oc` 只在实现中作为中间变量，不属于最终输出字段
- 当 `klen == 0` 时，`kmid2`、`kup2`、`klow2`、`ksft2` 返回 `0`

### 4.3 订单簿归一化特征

| 因子名称 | 计算公式 | 说明 |
|---------|---------|-----|
| `volume` | `Σ(bid_i_size) + Σ(ask_i_size)` | 五档总挂单量 |
| `bid1_size_n ~ bid5_size_n` | `bid_i_size / volume` | 买方归一化挂单量 |
| `ask1_size_n ~ ask5_size_n` | `ask_i_size / volume` | 卖方归一化挂单量 |

### 4.4 WAP 特征

| 因子名称 | 计算公式 | 说明 |
|---------|---------|-----|
| `wap_1` | `(ask1_size * bid1_price + bid1_size * ask1_price) / (ask1_size + bid1_size)` | 第一档加权均价 |
| `wap_2` | `(ask2_size * bid2_price + bid2_size * ask2_price) / (ask2_size + bid2_size)` | 第二档加权均价 |
| `wap_balance` | `abs(wap_1 - wap_2)` | 一二档均价差 |

### 4.5 价差与量能特征

| 因子名称 | 计算公式 | 说明 |
|---------|---------|-----|
| `buy_spread` | `abs(bid1_price - bid5_price)` | 买盘价差 |
| `sell_spread` | `abs(ask1_price - ask5_price)` | 卖盘价差 |
| `price_spread` | `2 * (ask1_price - bid1_price) / (ask1_price + bid1_price)` | 归一化买卖价差 |
| `buy_volume` | `Σ(bid_i_size)` | 买方五档总量 |
| `sell_volume` | `Σ(ask_i_size)` | 卖方五档总量 |
| `volume_imbalance` | `(buy_volume - sell_volume) / (buy_volume + sell_volume)` | 买卖量不平衡度 |

### 4.6 VWAP 特征

| 因子名称 | 计算公式 | 说明 |
|---------|---------|-----|
| `sell_vwap` | `Σ(ask_i_size_n * ask_i_price)` | 卖方加权均价 |
| `buy_vwap` | `Σ(bid_i_size_n * bid_i_price)` | 买方加权均价 |

### 4.7 对数收益率特征

| 因子名称 | 计算公式 | 说明 |
|---------|---------|-----|
| `log_return_bid1_price` | `log(bid1_price[t] / bid1_price[t-1])` | 买一价对数收益率 |
| `log_return_bid2_price` | `log(bid2_price[t] / bid2_price[t-1])` | 买二价对数收益率 |
| `log_return_ask1_price` | `log(ask1_price[t] / ask1_price[t-1])` | 卖一价对数收益率 |
| `log_return_ask2_price` | `log(ask2_price[t] / ask2_price[t-1])` | 卖二价对数收益率 |
| `log_return_wap_1` | `log(wap_1[t] / wap_1[t-1])` | 第一档 WAP 对数收益率 |
| `log_return_wap_2` | `log(wap_2[t] / wap_2[t-1])` | 第二档 WAP 对数收益率 |

说明：

- `log_return_*` 基于价格序列，不基于 `*_size_n`
- 第一行通常为空，因为不存在 `t-1`

### 4.8 趋势因子

统一公式：

```text
y_trend = (y - RollingMean(y, 60)) / RollingStd(y, 60)
```

当前实现中的基础变量集合：

- `ask1_price`
- `bid1_price`
- `buy_spread`
- `sell_spread`
- `wap_1`
- `wap_2`
- `buy_vwap`
- `sell_vwap`
- `volume`

对应输出字段：

- `ask1_price_trend_60`
- `bid1_price_trend_60`
- `buy_spread_trend_60`
- `sell_spread_trend_60`
- `wap_1_trend_60`
- `wap_2_trend_60`
- `buy_vwap_trend_60`
- `sell_vwap_trend_60`
- `volume_trend_60`

说明：

- 当前实现分母实际为 `RollingStd(y, 60) + 1e-8`
- 前 60 行可能为空，因为滚动窗口不足

---

## 五、字段数量汇总

### 5.1 因子输出字段数量

| 分类 | 数量 |
|------|-----|
| 基础时间字段 | 1 |
| 基础价格字段 | 4 |
| 基础盘口价格字段 | 10 |
| 基础盘口数量字段 | 10 |
| K 线衍生 | 9 |
| 归一化数量衍生 | 11 |
| WAP 衍生 | 3 |
| 价差衍生 | 3 |
| 量能衍生 | 3 |
| VWAP 衍生 | 2 |
| 对数收益率衍生 | 6 |
| 趋势衍生 | 9 |

如果只看最终“特征输出”部分，衍生因子共 46 个。

如果把基础字段一并统计，则常用分析字段为：

```text
timestamp
+ open_price, high_price, low_price, close_price
+ bid1_price ~ bid5_price, bid1_size ~ bid5_size
+ ask1_price ~ ask5_price, ask1_size ~ ask5_size
+ 46 个衍生因子
```

合计 71 个字段。

---

## 六、与当前代码实现的对应关系

### 6.1 预处理脚本

文件：[step4_preprocess_order_files_v2.py](../../scripts/step4_preprocess_order_files_v2.py)

负责：

- 使用 `ActionDay + UpdateTime` 生成 `datetime`
- 将原始快照按 `10s / 20s / 30s / 1m` 聚合
- 生成 `open_price/high_price/low_price/close_price`
- 生成 `bid*/ask*` 五档价格与数量

### 6.2 数据加载模块

文件：[data_loader.py](../../src/gen/data_loader.py)

当前使用的关键函数：

- `load_daily_orderbook_data()`
- `load_and_merge_date_range()`

说明：

- 当前主流程读取的是预处理后的 `orderbook/{timeframe}` 文件
- 若存在 `datetime` 列，会进一步解析为 `timestamp`

### 6.3 特征计算模块

文件：[feature_calculator.py](../../src/gen/feature_calculator.py)

关键函数：

- `calculate_kline_features()`
- `calculate_volume_and_normalized_size()`
- `calculate_wap_features()`
- `calculate_spread_features()`
- `calculate_volume_features()`
- `calculate_vwap_features()`
- `calculate_log_return_features()`
- `calculate_trend_features()`
- `calculate_all_features()`

### 6.4 配置模块

文件：[config.py](../../src/gen/config.py)

当前相关配置：

- `LEVEL_NAMES`
- `DCE_RENAME_MAP`
- `ALL_FEATURES`

说明：

- 当前代码中没有 `KLINE_RENAME_MAP`

---

## 七、数据质量检查口径

当前实现和文档默认关注以下检查项：

- `bid1_price < ask1_price`
- 价格字段非负
- `volume_imbalance` 在 `[-1, 1]` 范围内
- 对数收益率首行空值可接受
- 趋势因子窗口前段空值可接受

---

## 八、结论

对 SH/AL 当前实现而言，最重要的口径是：

1. 时间戳使用 `ActionDay + UpdateTime`
2. OHLC 来自窗口聚合，不直接取原始 `OpenPrice/HighPrice/LowPrice/ClosePrice`
3. 因子计算基于预处理后的 orderbook 文件
4. `log_return_*` 基于价格，`trend_*` 基于 60 窗口滚动标准化

以上口径已经与当前实现保持一致。

---

**文档版本**: 2.0
**最后更新**: 2026-04-06
**维护者**: MacroHFT Features SH Team
