import configparser
import datetime
from datetime import timedelta
import v20
import pandas as pd
from pandas.io.json import json_normalize
#import db.db as db
import json

config = configparser.ConfigParser()
config.read('conf.ini')

hostname = config['DEMO']['HOSTNAME']
port = int(config['DEMO']['PORT'])
token = config['DEMO']['TOKEN']


tz = datetime.timezone.utc
now = datetime.datetime.now(tz)

from_time = int((now - timedelta(hours=1)).timestamp())
to_time = int(now.timestamp())

instrument = 'USD_JPY'
kwargs = {}

kwargs['granularity'] = 'M5'
#kwargs['fromTime'] = from_time
kwargs['toTime'] = to_time
kwargs['count'] = 60

api = v20.Context(
        hostname,
        port,
        token=token
    )

response = api.instrument.candles(
        instrument, **kwargs
    )

print("Instrument: {}".format(response.get("instrument", 200)))
print("Granularity: {}".format(response.get("granularity", 200)))

candles = filter(lambda candle: candle.complete
        ,response.get("candles", 200))

# for candle in response.get("candles", 200):
#     print([
#         datetime.datetime.strptime(
#             candle.time.split('.')[0],
#             '%Y-%m-%dT%H:%M:%S'),
#         candle.mid.o,
#         candle.mid.h,
#         candle.mid.l,
#         candle.mid.c
#     ])

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
#print(list(mapped_list))

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


#df = json_normalize(json.loads(candles))
#print(df)
