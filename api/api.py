import configparser
import datetime
import v20

config = configparser.ConfigParser()
config.read('conf.ini')

hostname = config['DEMO']['HOSTNAME']
port = int(config['DEMO']['PORT'])
token = config['DEMO']['TOKEN']

api = v20.Context(
        hostname,
        port,
        token=token
)

instrument = 'USD_JPY'
params = {
    'granularity': 'M5',
    'count': 60,
    'completed_only': True
}

def get_candles(instrument=instrument,params=params):
    candles = api.instrument.candles(instrument, **params).get("candles", 200)
    if params['completed_only']:
        candles = [candle for candle in candles if candle.complete]

    return list(map(lambda candle: format_candle(candle), candles))

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
