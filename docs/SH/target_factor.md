# Target Factor

## 1. 基础输入字段

### 五档价格与数量

- `ask1_price` ~ `ask5_price`
- `ask1_size` ~ `ask5_size`
- `bid1_price` ~ `bid5_price`
- `bid1_size` ~ `bid5_size`

### K线价格

- `open_price`
- `high_price`
- `low_price`
- `close_price`

## 2. K线特征

```text
max_oc = max(open_price, close_price)
min_oc = min(open_price, close_price)

kmid  = close_price - open_price
kmid2 = (close_price - open_price) / (high_price - low_price)

klen  = high_price - low_price

kup   = high_price - max_oc
kup2  = (high_price - max_oc) / (high_price - low_price)

klow  = min_oc - low_price
klow2 = (min_oc - low_price) / (high_price - low_price)

ksft  = 2 * close_price - high_price - low_price
ksft2 = ksft / (high_price - low_price)
```

说明：

- `max_oc` 和 `min_oc` 为中间变量，不作为最终输出因子列。

## 3. 订单簿归一化特征

```text
volume = bid1_size + bid2_size + bid3_size + bid4_size + bid5_size
       + ask1_size + ask2_size + ask3_size + ask4_size + ask5_size

bid1_size_n = bid1_size / volume
bid2_size_n = bid2_size / volume
bid3_size_n = bid3_size / volume
bid4_size_n = bid4_size / volume
bid5_size_n = bid5_size / volume

ask1_size_n = ask1_size / volume
ask2_size_n = ask2_size / volume
ask3_size_n = ask3_size / volume
ask4_size_n = ask4_size / volume
ask5_size_n = ask5_size / volume
```

## 4. WAP 特征

```text
wap_1 = (ask1_size * bid1_price + bid1_size * ask1_price) / (ask1_size + bid1_size)
wap_2 = (ask2_size * bid2_price + bid2_size * ask2_price) / (ask2_size + bid2_size)

wap_balance = abs(wap_1 - wap_2)
```

## 5. 价差与量能特征

```text
buy_spread  = abs(bid1_price - bid5_price)
sell_spread = abs(ask1_price - ask5_price)
price_spread = 2 * (ask1_price - bid1_price) / (ask1_price + bid1_price)

buy_volume  = bid1_size + bid2_size + bid3_size + bid4_size + bid5_size
sell_volume = ask1_size + ask2_size + ask3_size + ask4_size + ask5_size

volume_imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume)
```

## 6. VWAP 特征

```text
sell_vwap = ask1_size_n * ask1_price
          + ask2_size_n * ask2_price
          + ask3_size_n * ask3_price
          + ask4_size_n * ask4_price
          + ask5_size_n * ask5_price

buy_vwap  = bid1_size_n * bid1_price
          + bid2_size_n * bid2_price
          + bid3_size_n * bid3_price
          + bid4_size_n * bid4_price
          + bid5_size_n * bid5_price
```

## 7. 对数收益率特征

```text
log_return_bid1_price = log(bid1_price[t] / bid1_price[t-1])
log_return_bid2_price = log(bid2_price[t] / bid2_price[t-1])
log_return_ask1_price = log(ask1_price[t] / ask1_price[t-1])
log_return_ask2_price = log(ask2_price[t] / ask2_price[t-1])

log_return_wap_1 = log(wap_1[t] / wap_1[t-1])
log_return_wap_2 = log(wap_2[t] / wap_2[t-1])
```

说明：

- 这里的 `log_return_*` 基于价格序列，不基于 `*_size_n`。

## 8. 趋势特征

```text
Y = [
  ask1_price,
  bid1_price,
  buy_spread,
  sell_spread,
  wap_1,
  wap_2,
  buy_vwap,
  sell_vwap,
  volume
]

y_trend = (y - RollingMean(y, 60)) / RollingStd(y, 60)
```

对应输出列：

- `ask1_price_trend_60`
- `bid1_price_trend_60`
- `buy_spread_trend_60`
- `sell_spread_trend_60`
- `wap_1_trend_60`
- `wap_2_trend_60`
- `buy_vwap_trend_60`
- `sell_vwap_trend_60`
- `volume_trend_60`

## 9. 最终输出因子列表

```text
kmid, kmid2, klen, kup, kup2, klow, klow2, ksft, ksft2,
volume,
bid1_size_n, bid2_size_n, bid3_size_n, bid4_size_n, bid5_size_n,
ask1_size_n, ask2_size_n, ask3_size_n, ask4_size_n, ask5_size_n,
wap_1, wap_2, wap_balance,
buy_spread, sell_spread, price_spread,
buy_volume, sell_volume, volume_imbalance,
buy_vwap, sell_vwap,
log_return_bid1_price, log_return_bid2_price,
log_return_ask1_price, log_return_ask2_price,
log_return_wap_1, log_return_wap_2,
ask1_price_trend_60, bid1_price_trend_60,
buy_spread_trend_60, sell_spread_trend_60,
wap_1_trend_60, wap_2_trend_60,
buy_vwap_trend_60, sell_vwap_trend_60,
volume_trend_60
```
