# 高频交易因子描述文档

本文档按当前代码实现和 [`target_factor.md`](./target_factor.md) 说明 SH 因子口径。

## 一、基础输入字段

### 1. 五档价格字段

- **ask1_price ~ ask5_price**: 卖方五档价格
  - 含义：卖一到卖五的盘口价格
  - 来源：上游五档行情快照字段
  - 用途：反映卖方报价结构，`ask1_price` 为最优卖价

- **bid1_price ~ bid5_price**: 买方五档价格
  - 含义：买一到买五的盘口价格
  - 来源：上游五档行情快照字段
  - 用途：反映买方报价结构，`bid1_price` 为最优买价

### 2. 五档数量字段

- **ask1_size ~ ask5_size**: 卖方五档挂单量
  - 含义：对应卖方各价格档位上的挂单深度
  - 用途：反映卖方各档位的订单分布

- **bid1_size ~ bid5_size**: 买方五档挂单量
  - 含义：对应买方各价格档位上的挂单深度
  - 用途：反映买方各档位的订单分布

### 3. K线价格字段

- **open_price**: 窗口开盘价
- **high_price**: 窗口最高价
- **low_price**: 窗口最低价
- **close_price**: 窗口收盘价

---

## 二、K线相关因子（Candlestick Features）

### 1. 中间变量

- **max_oc**: `max(open_price, close_price)`
  - 含义：K线实体上沿
  - 说明：仅作为中间变量使用，不属于最终输出因子

- **min_oc**: `min(open_price, close_price)`
  - 含义：K线实体下沿
  - 说明：仅作为中间变量使用，不属于最终输出因子

### 2. K线实体特征

- **kmid**: K线实体方向
  - 计算：`close_price - open_price`
  - 含义：收盘价与开盘价之差
  - 用途：正值通常表示上涨，负值通常表示下跌

- **kmid2**: K线实体归一化比率
  - 计算：`(close_price - open_price) / (high_price - low_price)`
  - 含义：实体长度占整根K线振幅的比例
  - 用途：衡量实体相对强度

### 3. K线振幅特征

- **klen**: K线总长度
  - 计算：`high_price - low_price`
  - 含义：当前窗口价格振幅
  - 用途：反映波动幅度

### 4. 上下影线特征

- **kup**: 上影线长度
  - 计算：`high_price - max_oc`
  - 含义：最高价到实体上沿的距离
  - 用途：反映上方压力

- **kup2**: 上影线归一化比率
  - 计算：`(high_price - max_oc) / (high_price - low_price)`
  - 含义：上影线占总振幅的比例
  - 用途：反映归一化后的上方压力

- **klow**: 下影线长度
  - 计算：`min_oc - low_price`
  - 含义：实体下沿到最低价的距离
  - 用途：反映下方支撑

- **klow2**: 下影线归一化比率
  - 计算：`(min_oc - low_price) / (high_price - low_price)`
  - 含义：下影线占总振幅的比例
  - 用途：反映归一化后的下方支撑

### 5. K线位置特征

- **ksft**: K线偏移量
  - 计算：`2 * close_price - high_price - low_price`
  - 含义：收盘价相对高低点中枢的位置偏移
  - 用途：衡量收盘更接近高点还是低点

- **ksft2**: K线偏移归一化比率
  - 计算：`ksft / (high_price - low_price)`
  - 含义：归一化后的 K 线位置偏移
  - 用途：便于跨时段比较

说明：

- 当前实现中，当 `high_price == low_price` 时，`kmid2`、`kup2`、`klow2`、`ksft2` 返回 `0`。

---

## 三、订单簿归一化因子（Normalized Size Features）

### 1. 总订单量

- **volume**: 五档总挂单量
  - 计算：`Σ(bid_i_size) + Σ(ask_i_size)`，`i = 1..5`
  - 含义：当前时刻订单簿前五档总深度
  - 用途：衡量盘口流动性

### 2. 归一化订单量

- **bid1_size_n ~ bid5_size_n**: 买方归一化挂单量
  - 计算：`bid_i_size / volume`
  - 含义：各买方档位挂单量占总盘口量的比例
  - 用途：反映买盘深度分布

- **ask1_size_n ~ ask5_size_n**: 卖方归一化挂单量
  - 计算：`ask_i_size / volume`
  - 含义：各卖方档位挂单量占总盘口量的比例
  - 用途：反映卖盘深度分布

---

## 四、加权平均价格因子（WAP Features）

### 1. 档位加权均价

- **wap_1**: 第一档加权均价
  - 计算：`(ask1_size * bid1_price + bid1_size * ask1_price) / (ask1_size + bid1_size)`
  - 含义：基于买一卖一数量加权的均衡价格
  - 用途：刻画最优档位的局部均衡价

- **wap_2**: 第二档加权均价
  - 计算：`(ask2_size * bid2_price + bid2_size * ask2_price) / (ask2_size + bid2_size)`
  - 含义：基于买二卖二数量加权的均衡价格
  - 用途：刻画次优档位的局部均衡价

### 2. 档位平衡差异

- **wap_balance**: 档位加权均价差异
  - 计算：`abs(wap_1 - wap_2)`
  - 含义：第一档和第二档均衡价格的绝对差
  - 用途：反映不同档位之间的结构一致性

---

## 五、价差因子（Spread Features）

### 1. 单边价差

- **buy_spread**: 买盘价差
  - 计算：`abs(bid1_price - bid5_price)`
  - 含义：买一到买五的价格跨度
  - 用途：反映买盘价格分布宽度

- **sell_spread**: 卖盘价差
  - 计算：`abs(ask1_price - ask5_price)`
  - 含义：卖一到卖五的价格跨度
  - 用途：反映卖盘价格分布宽度

### 2. 买卖价差

- **price_spread**: 归一化买卖价差
  - 计算：`2 * (ask1_price - bid1_price) / (ask1_price + bid1_price)`
  - 含义：买一卖一价差的归一化表达
  - 用途：反映流动性与交易成本

---

## 六、量能因子（Volume Features）

### 1. 单边总量

- **buy_volume**: 买方五档总量
  - 计算：`bid1_size + bid2_size + bid3_size + bid4_size + bid5_size`
  - 含义：买方前五档挂单量之和
  - 用途：衡量买盘整体深度

- **sell_volume**: 卖方五档总量
  - 计算：`ask1_size + ask2_size + ask3_size + ask4_size + ask5_size`
  - 含义：卖方前五档挂单量之和
  - 用途：衡量卖盘整体深度

### 2. 买卖不平衡

- **volume_imbalance**: 买卖量不平衡度
  - 计算：`(buy_volume - sell_volume) / (buy_volume + sell_volume)`
  - 含义：买盘与卖盘总量的相对差异
  - 用途：衡量盘口力量偏向

---

## 七、VWAP 因子（VWAP Features）

- **sell_vwap**: 卖方加权均价
  - 计算：`Σ(ask_i_size_n * ask_i_price)`，`i = 1..5`
  - 含义：卖方五档价格按归一化数量加权后的平均水平
  - 用途：反映卖盘整体价格中枢

- **buy_vwap**: 买方加权均价
  - 计算：`Σ(bid_i_size_n * bid_i_price)`，`i = 1..5`
  - 含义：买方五档价格按归一化数量加权后的平均水平
  - 用途：反映买盘整体价格中枢

---

## 八、对数收益率因子（Log Return Features）

### 1. 盘口价格对数收益率

- **log_return_bid1_price**: 买一价对数收益率
  - 计算：`log(bid1_price[t] / bid1_price[t-1])`
  - 含义：买一价格的对数变化率
  - 用途：衡量最优买价变动速度

- **log_return_bid2_price**: 买二价对数收益率
  - 计算：`log(bid2_price[t] / bid2_price[t-1])`
  - 含义：买二价格的对数变化率
  - 用途：衡量次优买价变动速度

- **log_return_ask1_price**: 卖一价对数收益率
  - 计算：`log(ask1_price[t] / ask1_price[t-1])`
  - 含义：卖一价格的对数变化率
  - 用途：衡量最优卖价变动速度

- **log_return_ask2_price**: 卖二价对数收益率
  - 计算：`log(ask2_price[t] / ask2_price[t-1])`
  - 含义：卖二价格的对数变化率
  - 用途：衡量次优卖价变动速度

### 2. WAP 对数收益率

- **log_return_wap_1**: 第一档 WAP 对数收益率
  - 计算：`log(wap_1[t] / wap_1[t-1])`
  - 含义：第一档均衡价格的对数变化率
  - 用途：衡量最优档位均衡价的变动趋势

- **log_return_wap_2**: 第二档 WAP 对数收益率
  - 计算：`log(wap_2[t] / wap_2[t-1])`
  - 含义：第二档均衡价格的对数变化率
  - 用途：衡量次优档位均衡价的变动趋势

说明：

- `log_return_*` 基于价格序列，不基于 `*_size_n`。
- 第一行通常为空，因为不存在 `t-1`。

---

## 九、趋势因子（Trend Features）

趋势因子基于以下变量集合：

- `ask1_price`
- `bid1_price`
- `buy_spread`
- `sell_spread`
- `wap_1`
- `wap_2`
- `buy_vwap`
- `sell_vwap`
- `volume`

统一公式：

- `y_trend = (y - RollingMean(y, 60)) / RollingStd(y, 60)`

对应输出列：

- **ask1_price_trend_60**: 卖一价趋势因子
- **bid1_price_trend_60**: 买一价趋势因子
- **buy_spread_trend_60**: 买盘价差趋势因子
- **sell_spread_trend_60**: 卖盘价差趋势因子
- **wap_1_trend_60**: 第一档 WAP 趋势因子
- **wap_2_trend_60**: 第二档 WAP 趋势因子
- **buy_vwap_trend_60**: 买方 VWAP 趋势因子
- **sell_vwap_trend_60**: 卖方 VWAP 趋势因子
- **volume_trend_60**: 总挂单量趋势因子

说明：

- 当前实现分母使用 `RollingStd(y, 60) + 1e-8`，用于避免除零。
- 前 60 行可能为空，因为滚动窗口不足。

---

## 十、因子应用说明

### 1. 因子类型分类

- **价格类因子**：订单簿价格、K线价格、WAP、VWAP
- **数量类因子**：订单量、归一化订单量、买卖总量
- **比率类因子**：价差、成交量不平衡度、K线归一化比率
- **动态类因子**：对数收益率、趋势因子

### 2. 常见应用场景

- **流动性分析**：`price_spread`、`volume`、`buy_spread`、`sell_spread`
- **市场微观结构分析**：订单簿价格数量、`wap_1`、`wap_2`、`buy_vwap`、`sell_vwap`
- **价格预测**：`volume_imbalance`、`log_return_*`、`*_trend_60`、K线特征
- **风险管理**：`klen`、`price_spread`、`volume_imbalance`

### 3. 注意事项

- 对数收益率和趋势因子都依赖历史序列。
- 趋势因子是 60 窗口滚动标准化结果。
- `max_oc` 和 `min_oc` 是中间变量，不属于最终输出列。
