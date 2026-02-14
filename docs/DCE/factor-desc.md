# 高频交易因子描述文档

## 一、订单簿基础数据（Order Book Data）

### 1. 价格档位数据
- **ask1_price ~ ask5_price**: 卖方五档价格
  - 含义：市场上卖方挂单的前五个最优价格档位
  - 计算：notional / depth（名义价值 / 深度）
  - 用途：反映市场卖方的报价结构，ask1_price为最低卖价

- **bid1_price ~ bid5_price**: 买方五档价格
  - 含义：市场上买方挂单的前五个最优价格档位
  - 计算：notional / depth（名义价值 / 深度）
  - 用途：反映市场买方的报价结构，bid1_price为最高买价

### 2. 订单量档位数据
- **ask1_size ~ ask5_size**: 卖方五档订单量
  - 含义：对应卖方各价格档位上的挂单数量
  - 用途：反映市场卖方在各价格档位上的订单深度

- **bid1_size ~ bid5_size**: 买方五档订单量
  - 含义：对应买方各价格档位上的挂单数量
  - 用途：反映市场买方在各价格档位上的订单深度

---

## 二、K线相关因子（Candlestick Features）

### 1. 基础K线特征
- **max_oc**: K线最大价
  - 计算：max(open_price, close_price)
  - 含义：开盘价和收盘价中的较大值
  - 用途：判断K线的方向和强度

- **min_oc**: K线最小价
  - 计算：min(open_price, close_price)
  - 含义：开盘价和收盘价中的较小值
  - 用途：判断K线的方向和支撑位

### 2. K线实体特征
- **kmid**: K线实体中点
  - 计算：close_price - open_price
  - 含义：收盘价与开盘价的差值，表示K线实体大小
  - 用途：正值表示上涨（阳线），负值表示下跌（阴线）

- **kmid2**: K线实体比率
  - 计算：(close_price - open_price) / (high_price - low_price)
  - 含义：K线实体占整个价格波动范围的比例
  - 用途：衡量趋势的强度，比率越大表示趋势越明确

### 3. K线整体长度
- **klen**: K线长度
  - 计算：high_price - low_price
  - 含义：K线的最高价与最低价之差
  - 用途：反映该时间段内的价格波动幅度

### 4. K线上影线特征
- **kup**: 上影线绝对长度
  - 计算：high_price - max_oc
  - 含义：最高价与实体上沿的距离
  - 用途：反映上方压力，上影线越长表示上方抛压越大

- **kup2**: 上影线比率
  - 计算：(high_price - max_oc) / (high_price - low_price)
  - 含义：上影线占整个K线长度的比例
  - 用途：归一化的上方压力指标

### 5. K线下影线特征
- **klow**: 下影线绝对长度
  - 计算：min_oc - low_price
  - 含义：实体下沿与最低价的距离
  - 用途：反映下方支撑，下影线越长表示下方支撑越强

- **klow2**: 下影线比率
  - 计算：(min_oc - low_price) / (high_price - low_price)
  - 含义：下影线占整个K线长度的比例
  - 用途：归一化的下方支撑指标

### 6. K线偏移特征
- **ksft**: K线偏移量
  - 计算：2 * close_price - high_price - low_price
  - 含义：收盘价相对于最高最低价中点的偏移
  - 用途：正值表示收盘偏向高点，负值表示收盘偏向低点

- **ksft2**: K线偏移比率
  - 计算：ksft / (high_price - low_price)
  - 含义：归一化的K线偏移量
  - 用途：衡量收盘价在当前K线中的相对位置

---

## 三、订单量归一化因子（Normalized Volume Features）

### 1. 总订单量
- **volume**: 订单簿总量
  - 计算：所有买卖五档订单量之和
  - 含义：当前时刻市场上挂单的总深度
  - 用途：衡量市场流动性

### 2. 归一化订单量
- **bid1_size_n ~ bid5_size_n**: 买方归一化订单量
  - 计算：bid_size / volume
  - 含义：各买方档位订单量占总订单量的比例
  - 用途：反映买方订单在各档位的分布情况

- **ask1_size_n ~ ask5_size_n**: 卖方归一化订单量
  - 计算：ask_size / volume
  - 含义：各卖方档位订单量占总订单量的比例
  - 用途：反映卖方订单在各档位的分布情况

---

## 四、加权平均价格因子（Weighted Average Price Features）

### 1. 档位加权平均价格
- **wap_1**: 第一档加权平均价格
  - 计算：(ask1_size * bid1_price + bid1_size * ask1_price) / (ask1_size + bid1_size)
  - 含义：基于买一卖一的成交量加权中间价
  - 用途：反映最优档位的市场均衡价格

- **wap_2**: 第二档加权平均价格
  - 计算：(ask2_size * bid2_price + bid2_size * ask2_price) / (ask2_size + bid2_size)
  - 含义：基于买二卖二的成交量加权中间价
  - 用途：反映次优档位的市场均衡价格

### 2. 档位价格平衡
- **wap_balance**: 档位价格差异
  - 计算：abs(wap_1 - wap_2)
  - 含义：第一档和第二档加权平格的绝对差值
  - 用途：反映不同档位之间的价格一致性，差值越大表示市场结构越不均衡

---

## 五、价差因子（Spread Features）

### 1. 单边价差
- **buy_spread**: 买方价差
  - 计算：abs(bid1_price - bid5_price)
  - 含义：买方最高价与买方第五档价格的差距
  - 用途：反映买方订单簿的深度和价格分布

- **sell_spread**: 卖方价差
  - 计算：abs(ask1_price - ask5_price)
  - 含义：卖方最低价与卖方第五档价格的差距
  - 用途：反映卖方订单簿的深度和价格分布

### 2. 买卖价差
- **price_spread**: 相对买卖价差
  - 计算：2 * (ask1_price - bid1_price) / (ask1_price + bid1_price)
  - 含义：买一卖一价差的归一化值
  - 用途：反映市场流动性和交易成本，价差越小流动性越好

---

## 六、成交量因子（Volume Features）

### 1. 单边成交量
- **buy_volume**: 买方总量
  - 计算：bid1_size + bid2_size + bid3_size + bid4_size + bid5_size
  - 含义：买方五档订单量的总和
  - 用途：反映买方的整体订单深度

- **sell_volume**: 卖方总量
  - 计算：ask1_size + ask2_size + ask3_size + ask4_size + ask5_size
  - 含义：卖方五档订单量的总和
  - 用途：反映卖方的整体订单深度

### 2. 成交量不平衡
- **volume_imbalance**: 成交量不平衡度
  - 计算：(buy_volume - sell_volume) / (buy_volume + sell_volume)
  - 含义：买卖订单量的相对差异
  - 用途：正值表示买方力量较强，负值表示卖方力量较强，是重要的价格预测指标

---

## 七、成交量加权平均价格（VWAP Features）

- **sell_vwap**: 卖方成交量加权平均价格
  - 计算：Σ(ask_size_n * ask_price) for all 5 levels
  - 含义：基于归一化订单量的卖方加权平均价格
  - 用途：反映卖方的整体价格水平

- **buy_vwap**: 买方成交量加权平均价格
  - 计算：Σ(bid_size_n * bid_price) for all 5 levels
  - 含义：基于归一化订单量的买方加权平均价格
  - 用途：反映买方的整体价格水平

---

## 八、对数收益率因子（Log Return Features）

### 1. 价格对数收益率
- **log_return_bid1_price**: 买一价对数收益率
  - 计算：log(bid1_price[t] / bid1_price[t-1])
  - 含义：买一价格的对数变化率
  - 用途：衡量买方最优价格的变动速度

- **log_return_bid2_price**: 买二价对数收益率
  - 计算：log(bid2_price[t] / bid2_price[t-1])
  - 含义：买二价格的对数变化率
  - 用途：衡量买方次优价格的变动速度

- **log_return_ask1_price**: 卖一价对数收益率
  - 计算：log(ask1_price[t] / ask1_price[t-1])
  - 含义：卖一价格的对数变化率
  - 用途：衡量卖方最优价格的变动速度

- **log_return_ask2_price**: 卖二价对数收益率
  - 计算：log(ask2_price[t] / ask2_price[t-1])
  - 含义：卖二价格的对数变化率
  - 用途：衡量卖方次优价格的变动速度

### 2. WAP对数收益率
- **log_return_wap_1**: 第一档WAP对数收益率
  - 计算：log(wap_1[t] / wap_1[t-1])
  - 含义：第一档加权平均价格的对数变化率
  - 用途：衡量最优档位均衡价格的变动趋势

- **log_return_wap_2**: 第二档WAP对数收益率
  - 计算：log(wap_2[t] / wap_2[t-1])
  - 含义：第二档加权平均价格的对数变化率
  - 用途：衡量次优档位均衡价格的变动趋势

---

## 因子应用说明

### 1. 因子类型分类
- **价格类因子**：订单簿价格、K线价格、WAP、VWAP
- **数量类因子**：订单量、归一化订单量、成交量
- **比率类因子**：价差、成交量不平衡度、K线比率
- **动态类因子**：对数收益率、价格变化

### 2. 常见应用场景
- **流动性分析**：使用price_spread, volume, buy_spread, sell_spread
- **市场微观结构**：使用订单簿数据、WAP、VWAP
- **价格预测**：使用volume_imbalance, log_return系列, K线特征
- **风险管理**：使用klen, price_spread, volume_imbalance

### 3. 注意事项
- 对数收益率因子需要历史数据（t-1时刻）
- 归一化因子避免了绝对数值的影响，更适合跨品种比较
- K线特征适用于分钟级或更高频率的数据
- 订单簿数据反映的是瞬时状态，需要结合时间序列分析
