

'ask1_price',  ask side percentage==1 ，  notional/ depth
'ask1_size',   ask side percentage==1 ，  depth
'bid1_price',  ask side percentage==-1 ，  notional/ depth
'bid1_size',   ask side percentage==-1 ，  depth
'ask2_price',
'ask2_size',
'bid2_price',
'bid2_size', 
'ask3_price',
'ask3_size', 
'bid3_price', 
'bid3_size', 
'ask4_price', 
'ask4_size',
'bid4_price', 
'bid4_size', 
'ask5_price',  ask side percentage==5 ，  notional/ depth
'ask5_size',   ask side percentage==5 ，  depth
'bid5_price',  ask side percentage==-5 ，  notional/ depth
'bid5_size',   ask side percentage==-5 ，  depth


max_oc = max(open_price,close_price)
min_oc = min(open_price,close_price)
kmid = (close_price-open_price)
kmid2 = (close_price-open_price)/(high_price-low_price)
klen = (high_price-low_price)
kup = (high_price-max_oc)
kup2 = (high_price-max_oc)/(high_price-low_price)
klow = (min_oc-low_price)
klow2 = (min_oc-low_price)/(high_price-low_price)
ksft =  2*close_price - high_price - low_price
ksft2 =  ksft/(high_price-low_price)
volume  = bid1_size+bid2_size+bid3_size+bid4_size+bid5_size+ask1_size+ask2_size+ask3_size+ask4_size+ask5_size

'bid1_size_n', = bid1_size/volume
'bid2_size_n', 
'bid3_size_n',
'bid4_size_n', 
'bid5_size_n', 
'ask1_size_n', = ask1_size/volume
'ask2_size_n',
'ask3_size_n', 
'ask4_size_n', 
'ask5_size_n', 
'wap_1',   (ask1_size*bid1_price+bid1_size*ask1_price)/(ask1_size+bid1_size)
'wap_2',   (ask2_size*bid2_price+bid2_size*ask2_price)/(ask2_size+bid2_size)
'wap_balance', = abs(wap_1 - wap_2)

'buy_spread', = abs(bid1_price-bid5_price)
'sell_spread', = abs(ask1_price-ask5_price)
'price_spread', =2*(ask1_price-bid1_price)/(ask1_price+bid1_price)

'buy_volume', = (bid1_size+bid2_size+bid3_size+bid4_size+bid5_size)
'sell_volume', = (ask1_size+ask2_size+ask3_size+ask4_size+ask5_size)
'volume_imbalance', = (buy_volume-sell_volume)/(buy_volume+sell_volume)

 
'sell_vwap', = ask1_size_n*ask1_price+ask2_size_n*ask2_price+ask3_size_n*ask3_price+ask4_size_n*ask4_price+ask5_size_n*ask5_price
'buy_vwap', = bid1_size_n*bid1_price+bid2_size_n*bid2_price+bid3_size_n*bid3_price+bid4_size_n*bid4_price+bid5_size_n*bid5_price


'log_return_bid1_price',   = 𝑙𝑜𝑔(bid1_size_n/bid1_size_n【t-1】)
'log_return_bid2_price',   = 𝑙𝑜𝑔(bid2_size_n/bid2_size_n【t-1】)
'log_return_ask1_price',   = 𝑙𝑜𝑔(ask1_size_n/ask1_size_n【t-1】)
'log_return_ask2_price',   = 𝑙𝑜𝑔(ask2_size_n/ask2_size_n【t-1】)
 
'log_return_wap_1', = 𝑙𝑜𝑔(wap_1/wap_1【t-1】)
'log_return_wap_2', = 𝑙𝑜𝑔(wap_2/wap_2【t-1】)


ask1_price_trend_60,  y==ask1_price ,𝑦trend = 𝑦 − RollingMean(𝑦, 60)/RollingStd(𝑦, 60)
bid1_price_trend_60,  y==bid1_price ,𝑦trend = 𝑦 − RollingMean(𝑦, 60)/RollingStd(𝑦, 60)
buy_spread_trend_60,  y==buy_spread ,𝑦trend = 𝑦 − RollingMean(𝑦, 60)/RollingStd(𝑦, 60)
sell_spread_trend_60, y==sell_spread ,𝑦trend = 𝑦 − RollingMean(𝑦, 60)/RollingStd(𝑦, 60)
wap_1_trend_60,       y==wap_1 ,𝑦trend = 𝑦 − RollingMean(𝑦, 60)/RollingStd(𝑦, 60)
wap_2_trend_60,       y==wap_2 ,𝑦trend = 𝑦 − RollingMean(𝑦, 60)/RollingStd(𝑦, 60)
buy_vwap_trend_60,    y==buy_vwap ,𝑦trend = 𝑦 − RollingMean(𝑦, 60)/RollingStd(𝑦, 60)
sell_vwap_trend_60,   y==sell_vwap ,𝑦trend = 𝑦 − RollingMean(𝑦, 60)/RollingStd(𝑦, 60)
volume_trend_60,      y==volume ,𝑦trend = 𝑦 − RollingMean(𝑦, 60)/RollingStd(𝑦, 60)
   