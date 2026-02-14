# DCE 原始数据列说明及字段映射关系

## 文档概览

本文档说明DCE（大连商品交易所）原始数据的字段定义,以及这些字段如何映射到 target_factor 中的计算因子。

---

## 一、DCE 原始数据源

DCE 数据包含三种主要数据类型:

### 1.1 五档行情数据 (Level-5 Market Data)

**文件位置**: `data/豆油2023-2025/{YYYYMM}/{YYYYMMDD}/五档行情数据/{contract}.csv`

**用途**: 提供订单簿(Order Book)的买卖五档价格和数量数据,以及K线基础数据

#### 原始字段列表

| 字段名 | 类型 | 说明 | 映射到 target_factor |
|--------|------|------|---------------------|
| **时间字段** |
| `ActionDay` | Date | 业务日期 | - |
| `TradingDay` | Date | 交易日 | - |
| `UpdateTime` | Time | 更新时间 | `timestamp` (与日期合并) |
| **合约信息** |
| `InstrumentID` | String | 合约代码 (如 y2309) | - |
| **价格字段** |
| `LastPrice` | Float | 最新价 | - |
| `HighPrice` | Float | 最高价 | `high_price` |
| `LowPrice` | Float | 最低价 | `low_price` |
| `OpenPrice` | Float | 开盘价 | `open_price` |
| `ClosePrice` | Float | 收盘价 | `close_price` |
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

**字段总数**: 约 57 个字段

---

### 1.2 期货成交量统计 (Futures Trading Volume Statistics)

**文件位置**: `data/豆油2023-2025/{YYYYMM}/{YYYYMMDD}/期货成交量统计/{contract}.csv`

**用途**: 提供最优5个价位的开仓/平仓成交量分布

#### 原始字段列表

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

**字段总数**: 24 个字段

**注意**: 此数据源暂未直接映射到 target_factor,但可用于扩展特征工程。

---

### 1.3 十笔最优价位委托 (Top 10 Best Price Orders)

**文件位置**: `data/豆油2023-2025/{YYYYMM}/{YYYYMMDD}/十笔最优价位委托/{contract}.csv`

**用途**: 提供最优价位的前10笔委托订单数量

#### 原始字段列表

| 字段名 | 类型 | 说明 | 映射到 target_factor |
|--------|------|------|---------------------|
| **时间字段** |
| `ActionDay` | Date | 业务日期 | - |
| `TradingDay` | Date | 交易日 | - |
| `UpdateTime` | Time | 更新时间 | - |
| **合约信息** |
| `InstrumentID` | String | 合约代码 | - |
| **买方委托** |
| `BidPrice` | Float | 买价 | - |
| `BidOrderV1` | Int | 买委托1 | - |
| `BidOrderV2` | Int | 买委托2 | - |
| `BidOrderV3` | Int | 买委托3 | - |
| `BidOrderV4` | Int | 买委托4 | - |
| `BidOrderV5` | Int | 买委托5 | - |
| `BidOrderV6` | Int | 买委托6 | - |
| `BidOrderV7` | Int | 买委托7 | - |
| `BidOrderV8` | Int | 买委托8 | - |
| `BidOrderV9` | Int | 买委托9 | - |
| `BidOrderV10` | Int | 买委托10 | - |
| **卖方委托** |
| `AskPrice` | Float | 卖价 | - |
| `AskOrderV1` | Int | 卖委托1 | - |
| `AskOrderV2` | Int | 卖委托2 | - |
| `AskOrderV3` | Int | 卖委托3 | - |
| `AskOrderV4` | Int | 卖委托4 | - |
| `AskOrderV5` | Int | 卖委托5 | - |
| `AskOrderV6` | Int | 卖委托6 | - |
| `AskOrderV7` | Int | 卖委托7 | - |
| `AskOrderV8` | Int | 卖委托8 | - |
| `AskOrderV9` | Int | 卖委托9 | - |
| `AskOrderV10` | Int | 卖委托10 | - |

**字段总数**: 24 个字段

**注意**: 此数据源暂未直接映射到 target_factor,但可用于订单流分析。

---

## 二、Target Factor 字段映射关系

### 2.1 基础字段 (Direct Mapping)

这些字段直接从五档行情数据映射而来:

| Target Factor 字段 | 来源数据 | 原始字段 | 备注 |
|-------------------|---------|---------|-----|
| **时间戳** |
| `timestamp` | 五档行情 | `TradingDay` + `UpdateTime` | 合并日期和时间 |
| **K线价格** |
| `open_price` | 五档行情 | `OpenPrice` | 开盘价 |
| `high_price` | 五档行情 | `HighPrice` | 最高价 |
| `low_price` | 五档行情 | `LowPrice` | 最低价 |
| `close_price` | 五档行情 | `ClosePrice` | 收盘价 |
| **买方五档价格** |
| `bid1_price` | 五档行情 | `BidPrice1` | 买一价 |
| `bid2_price` | 五档行情 | `BidPrice2` | 买二价 |
| `bid3_price` | 五档行情 | `BidPrice3` | 买三价 |
| `bid4_price` | 五档行情 | `BidPrice4` | 买四价 |
| `bid5_price` | 五档行情 | `BidPrice5` | 买五价 |
| **买方五档数量** |
| `bid1_size` | 五档行情 | `BidVolume1` | 买一量 |
| `bid2_size` | 五档行情 | `BidVolume2` | 买二量 |
| `bid3_size` | 五档行情 | `BidVolume3` | 买三量 |
| `bid4_size` | 五档行情 | `BidVolume4` | 买四量 |
| `bid5_size` | 五档行情 | `BidVolume5` | 买五量 |
| **卖方五档价格** |
| `ask1_price` | 五档行情 | `AskPrice1` | 卖一价 |
| `ask2_price` | 五档行情 | `AskPrice2` | 卖二价 |
| `ask3_price` | 五档行情 | `AskPrice3` | 卖三价 |
| `ask4_price` | 五档行情 | `AskPrice4` | 卖四价 |
| `ask5_price` | 五档行情 | `AskPrice5` | 卖五价 |
| **卖方五档数量** |
| `ask1_size` | 五档行情 | `AskVolume1` | 卖一量 |
| `ask2_size` | 五档行情 | `AskVolume2` | 卖二量 |
| `ask3_size` | 五档行情 | `AskVolume3` | 卖三量 |
| `ask4_size` | 五档行情 | `AskVolume4` | 卖四量 |
| `ask5_size` | 五档行情 | `AskVolume5` | 卖五量 |

**基础字段总数**: 25 个字段

---

### 2.2 衍生字段 (Calculated Features)

以下字段通过基础字段计算得出:

#### 2.2.1 K线特征因子 (Kline Features)

| 因子名称 | 计算公式 | 依赖字段 | 说明 |
|---------|---------|---------|-----|
| `max_oc` | `max(open_price, close_price)` | open_price, close_price | K线实体上端 |
| `min_oc` | `min(open_price, close_price)` | open_price, close_price | K线实体下端 |
| `kmid` | `close_price - open_price` | close_price, open_price | K线实体中点(方向性) |
| `kmid2` | `(close_price - open_price) / (high_price - low_price)` | close, open, high, low | K线实体比率 |
| `klen` | `high_price - low_price` | high_price, low_price | K线总长度 |
| `kup` | `high_price - max_oc` | high_price, max_oc | 上影线长度 |
| `kup2` | `(high_price - max_oc) / (high_price - low_price)` | high, max_oc, low | 上影线比率 |
| `klow` | `min_oc - low_price` | min_oc, low_price | 下影线长度 |
| `klow2` | `(min_oc - low_price) / (high_price - low_price)` | min_oc, low, high | 下影线比率 |
| `ksft` | `2*close_price - high_price - low_price` | close, high, low | K线偏移 |
| `ksft2` | `ksft / (high_price - low_price)` | ksft, high, low | K线偏移比率 |

**K线特征因子数**: 9 个 (不含中间变量 max_oc, min_oc)

#### 2.2.2 订单簿特征 - 归一化数量 (Normalized Size)

| 因子名称 | 计算公式 | 依赖字段 | 说明 |
|---------|---------|---------|-----|
| `volume` | `Σ(bid_i_size) + Σ(ask_i_size)` | bid1-5_size, ask1-5_size | 总订单量 (i=1..5) |
| `bid1_size_n` | `bid1_size / volume` | bid1_size, volume | 买一归一化量 |
| `bid2_size_n` | `bid2_size / volume` | bid2_size, volume | 买二归一化量 |
| `bid3_size_n` | `bid3_size / volume` | bid3_size, volume | 买三归一化量 |
| `bid4_size_n` | `bid4_size / volume` | bid4_size, volume | 买四归一化量 |
| `bid5_size_n` | `bid5_size / volume` | bid5_size, volume | 买五归一化量 |
| `ask1_size_n` | `ask1_size / volume` | ask1_size, volume | 卖一归一化量 |
| `ask2_size_n` | `ask2_size / volume` | ask2_size, volume | 卖二归一化量 |
| `ask3_size_n` | `ask3_size / volume` | ask3_size, volume | 卖三归一化量 |
| `ask4_size_n` | `ask4_size / volume` | ask4_size, volume | 卖四归一化量 |
| `ask5_size_n` | `ask5_size / volume` | ask5_size, volume | 卖五归一化量 |

**归一化数量因子数**: 11 个 (包含 volume)

#### 2.2.3 加权平均价格因子 (WAP Features)

| 因子名称 | 计算公式 | 依赖字段 | 说明 |
|---------|---------|---------|-----|
| `wap_1` | `(ask1_size * bid1_price + bid1_size * ask1_price) / (ask1_size + bid1_size)` | ask1_size, bid1_price, bid1_size, ask1_price | 一档加权均价 |
| `wap_2` | `(ask2_size * bid2_price + bid2_size * ask2_price) / (ask2_size + bid2_size)` | ask2_size, bid2_price, bid2_size, ask2_price | 二档加权均价 |
| `wap_balance` | `abs(wap_1 - wap_2)` | wap_1, wap_2 | 一二档价差 |

**WAP因子数**: 3 个

#### 2.2.4 价差因子 (Spread Features)

| 因子名称 | 计算公式 | 依赖字段 | 说明 |
|---------|---------|---------|-----|
| `buy_spread` | `abs(bid1_price - bid5_price)` | bid1_price, bid5_price | 买方价差(一到五档) |
| `sell_spread` | `abs(ask1_price - ask5_price)` | ask1_price, ask5_price | 卖方价差(一到五档) |
| `price_spread` | `2 * (ask1_price - bid1_price) / (ask1_price + bid1_price)` | ask1_price, bid1_price | 买卖价差(归一化) |

**价差因子数**: 3 个

#### 2.2.5 成交量因子 (Volume Features)

| 因子名称 | 计算公式 | 依赖字段 | 说明 |
|---------|---------|---------|-----|
| `buy_volume` | `Σ(bid_i_size)` | bid1-5_size | 买方总量 (i=1..5) |
| `sell_volume` | `Σ(ask_i_size)` | ask1-5_size | 卖方总量 (i=1..5) |
| `volume_imbalance` | `(buy_volume - sell_volume) / (buy_volume + sell_volume)` | buy_volume, sell_volume | 成交量不平衡度 |

**成交量因子数**: 3 个

#### 2.2.6 成交量加权平均价格 (VWAP Features)

| 因子名称 | 计算公式 | 依赖字段 | 说明 |
|---------|---------|---------|-----|
| `sell_vwap` | `Σ(ask_i_size_n * ask_i_price)` | ask1-5_size_n, ask1-5_price | 卖方加权均价 (i=1..5) |
| `buy_vwap` | `Σ(bid_i_size_n * bid_i_price)` | bid1-5_size_n, bid1-5_price | 买方加权均价 (i=1..5) |

**VWAP因子数**: 2 个

#### 2.2.7 对数收益率因子 (Log Return Features)

| 因子名称 | 计算公式 | 依赖字段 | 说明 |
|---------|---------|---------|-----|
| `log_return_bid1_price` | `log(bid1_price[t] / bid1_price[t-1])` | bid1_price | 买一价对数收益率 |
| `log_return_bid2_price` | `log(bid2_price[t] / bid2_price[t-1])` | bid2_price | 买二价对数收益率 |
| `log_return_ask1_price` | `log(ask1_price[t] / ask1_price[t-1])` | ask1_price | 卖一价对数收益率 |
| `log_return_ask2_price` | `log(ask2_price[t] / ask2_price[t-1])` | ask2_price | 卖二价对数收益率 |
| `log_return_wap_1` | `log(wap_1[t] / wap_1[t-1])` | wap_1 | wap_1对数收益率 |
| `log_return_wap_2` | `log(wap_2[t] / wap_2[t-1])` | wap_2 | wap_2对数收益率 |

**对数收益率因子数**: 6 个

**注意**: 第一行数据的对数收益率因子为 null (无前值数据)

#### 2.2.8 趋势因子 (Trend Features)

趋势因子计算公式统一为: `y_trend = (y - RollingMean(y, 60)) / RollingStd(y, 60)`

| 因子名称 | 基础变量 y | 窗口大小 | 说明 |
|---------|-----------|---------|-----|
| `ask1_price_trend_60` | `ask1_price` | 60 | 卖一价趋势 |
| `bid1_price_trend_60` | `bid1_price` | 60 | 买一价趋势 |
| `buy_spread_trend_60` | `buy_spread` | 60 | 买方价差趋势 |
| `sell_spread_trend_60` | `sell_spread` | 60 | 卖方价差趋势 |
| `wap_1_trend_60` | `wap_1` | 60 | wap_1趋势 |
| `wap_2_trend_60` | `wap_2` | 60 | wap_2趋势 |
| `buy_vwap_trend_60` | `buy_vwap` | 60 | 买方VWAP趋势 |
| `sell_vwap_trend_60` | `sell_vwap` | 60 | 卖方VWAP趋势 |
| `volume_trend_60` | `volume` | 60 | 总量趋势 |

**趋势因子数**: 9 个

**注意**: 前 60 行的趋势因子可能为 null (滚动窗口不足)

---

## 三、数据处理流程

### 3.1 数据加载流程

```
五档行情数据 (CSV)
    ↓
时间戳合并: TradingDay + UpdateTime → timestamp
    ↓
价格字段映射: OpenPrice → open_price, HighPrice → high_price, etc.
    ↓
订单簿字段映射: BidPrice1 → bid1_price, BidVolume1 → bid1_size, etc.
    ↓
基础数据框 (25个基础字段)
```

### 3.2 特征计算流程

```
基础数据框
    ↓
1. K线特征计算 (+9 个因子)
    ↓
2. 归一化订单量计算 (+11 个因子)
    ↓
3. WAP因子计算 (+3 个因子)
    ↓
4. 价差因子计算 (+3 个因子)
    ↓
5. 成交量因子计算 (+3 个因子)
    ↓
6. VWAP因子计算 (+2 个因子)
    ↓
7. 对数收益率因子计算 (+6 个因子)
    ↓
8. 趋势因子计算 (+9 个因子)
    ↓
完整特征数据框 (25 基础 + 46 衍生 = 71 个字段)
```

### 3.3 数据处理注意事项

1. **时间对齐**:
   - 将 `TradingDay` 和 `UpdateTime` 合并为统一的 `timestamp`
   - 时间精度截断到分钟级别

2. **空值处理**:
   - 对数收益率因子: 第一行为 null
   - 趋势因子: 前 60 行可能为 null
   - 除零处理: klen=0 时,相关比率设为 0

3. **数据验证**:
   - 检查 `bid1_price < ask1_price` (买价应低于卖价)
   - 检查价格和数量无负值
   - 检查 `volume_imbalance` 在 [-1, 1] 范围内

---

## 四、Target Factor 字段分类汇总

### 4.1 按来源分类

| 分类 | 数量 | 字段列表 |
|------|-----|---------|
| **基础字段** (直接映射) | 25 | timestamp, open_price, high_price, low_price, close_price, bid1-5_price, bid1-5_size, ask1-5_price, ask1-5_size |
| **K线衍生** | 9 | kmid, kmid2, klen, kup, kup2, klow, klow2, ksft, ksft2 |
| **订单簿衍生** | 11 | volume, bid1-5_size_n, ask1-5_size_n |
| **WAP衍生** | 3 | wap_1, wap_2, wap_balance |
| **价差衍生** | 3 | buy_spread, sell_spread, price_spread |
| **成交量衍生** | 3 | buy_volume, sell_volume, volume_imbalance |
| **VWAP衍生** | 2 | buy_vwap, sell_vwap |
| **对数收益率衍生** | 6 | log_return_bid1_price, log_return_bid2_price, log_return_ask1_price, log_return_ask2_price, log_return_wap_1, log_return_wap_2 |
| **趋势衍生** | 9 | ask1_price_trend_60, bid1_price_trend_60, buy_spread_trend_60, sell_spread_trend_60, wap_1_trend_60, wap_2_trend_60, buy_vwap_trend_60, sell_vwap_trend_60, volume_trend_60 |
| **总计** | **71** | - |

### 4.2 按功能分类

| 分类 | 数量 | 说明 |
|------|-----|-----|
| **时间特征** | 1 | timestamp |
| **K线价格特征** | 4 | open, high, low, close |
| **K线形态特征** | 9 | kmid系列, klen, kup系列, klow系列, ksft系列 |
| **订单簿价格** | 10 | bid1-5_price, ask1-5_price |
| **订单簿数量** | 10 | bid1-5_size, ask1-5_size |
| **归一化数量** | 11 | volume, bid1-5_size_n, ask1-5_size_n |
| **价格衍生** | 5 | wap_1, wap_2, wap_balance, buy_vwap, sell_vwap |
| **价差特征** | 3 | buy_spread, sell_spread, price_spread |
| **成交量特征** | 3 | buy_volume, sell_volume, volume_imbalance |
| **动量特征** | 6 | log_return_* 系列 |
| **趋势特征** | 9 | *_trend_60 系列 |

---

## 五、代码实现映射

### 5.1 数据加载模块 (data_loader.py)

- **功能**: 从五档行情CSV文件加载原始数据
- **关键函数**:
  - `load_daily_bookdepth()`: 加载五档行情数据
  - `pivot_bookdepth()`: 将长格式转宽格式 (未在DCE数据中使用)
  - `preprocess_kline()`: 预处理K线数据,映射字段名
  - `merge_data()`: 合并订单簿和K线数据

### 5.2 特征计算模块 (feature_calculator.py)

- **功能**: 计算所有衍生因子
- **关键函数**:
  - `calculate_kline_features()`: K线特征 (9个)
  - `calculate_volume_and_normalized_size()`: 归一化数量 (11个)
  - `calculate_wap_features()`: WAP因子 (3个)
  - `calculate_spread_features()`: 价差因子 (3个)
  - `calculate_volume_features()`: 成交量因子 (3个)
  - `calculate_vwap_features()`: VWAP因子 (2个)
  - `calculate_log_return_features()`: 对数收益率 (6个)
  - `calculate_trend_features()`: 趋势因子 (9个)
  - `calculate_all_features()`: 执行所有计算

### 5.3 配置模块 (config.py)

- **功能**: 定义常量和映射关系
- **关键配置**:
  - `LEVEL_NAMES`: 档位映射 {-1: "bid1", 1: "ask1", ...}
  - `KLINE_RENAME_MAP`: K线字段重命名映射
  - `ALL_FEATURES`: 所有因子列表 (46个衍生因子)

---

## 六、扩展数据源 (未映射)

以下DCE数据源尚未映射到 target_factor,但可用于未来特征扩展:

### 6.1 期货成交量统计

- **潜在特征**:
  - 开仓/平仓比例
  - 买卖开仓平衡度
  - 价位分布特征

### 6.2 十笔最优价位委托

- **潜在特征**:
  - 订单流强度
  - 大单分布
  - 委托不平衡度

---

## 七、数据质量与验证

### 7.1 数据完整性检查

- 时间戳连续性
- 空值检查
- 无穷值检查

### 7.2 数据合理性检查

- `bid1_price < ask1_price` (买价低于卖价)
- 价格和数量非负
- `volume_imbalance` ∈ [-1, 1]
- 成交量数据一致性

### 7.3 异常处理策略

- 除零保护: klen=0 时设置比率为 0
- 对数收益率: 第一行设为 null
- 趋势因子: 窗口不足时设为 null

---

## 八、参考文档

- **DCE官方文档**: 大连商品交易所数据接口规范
- **Target Factor 定义**: [target_factor.md](target_factor.md)
- **代码实现**:
  - 数据加载: [src/gen/data_loader.py](../../src/gen/data_loader.py)
  - 特征计算: [src/gen/feature_calculator.py](../../src/gen/feature_calculator.py)
  - 配置管理: [src/gen/config.py](../../src/gen/config.py)

---

**文档版本**: 1.0
**最后更新**: 2026-02-14
**维护者**: MacroHFT Features DCE Team
