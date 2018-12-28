import api.api as api
import datetime
import pandas as pd

candles = api.get_candles()

def format_candle(candle):
    return {
        'datetime':str(datetime.datetime.strptime(
            candle.time.split('.')[0],
            '%Y-%m-%dT%H:%M:%S')),
        'open': candle.mid.o,
        'high': candle.mid.h,
        'low':candle.mid.l,
        'close': candle.mid.c
    }

mapped_list = map(lambda candle: format_candle(candle), candles)
df = pd.DataFrame(list(mapped_list))

macd = pd.DataFrame()
macd['ema12'] = df['close'].ewm(span=12).mean()
macd['ema26'] = df['close'].ewm(span=26).mean()
macd['macd'] = macd['ema12'] - macd['ema26']
macd['signal'] = macd['macd'].rolling(window=9).mean()
df['macd'] = macd['macd']
df['macd_signal'] = macd['signal']
df['macd2'] = macd['macd'] - macd['signal']
print(df.loc[:,['datetime','open','high','low','close', 'macd', 'macd_signal', 'macd2']])
