import datetime
from time import sleep
import api.api as api
import analizer

instrument = 'USD_JPY'
params = {
    'granularity': 'S5',
    'count': 1
}

api = api.Api()
open_trade = None

def main():
    if open_trade:
        print('i have a open position')

        if open_trade['side'] == 'long':
            if analizer.is_macd_keep_going('down'):
                close_position()

        if open_trade['side'] == 'short':
            if analizer.is_macd_keep_going('up'):
                close_position()

        candle = api.get_candles(instrument, params, False)
        if analizer.is_macd_crossed(candle)[0]:
            close_position()

    else:
        #ポジションがない場合
        print('i dont have a open position')

        candle = api.get_candles(instrument, params, False)
        is_macd_crossed = analizer.is_macd_crossed(candle)

        if is_macd_crossed[0] and analizer.is_entry_interval_enough():
            if is_macd_crossed[1] == 1:
                #上向きクロスだったら買いでエントリー
                print('entry by long')
                entry(10000)
            else:
                #下向きクロスだったら売りでエントリー
                print('entry by short')
                entry(-10000)
        else:
            print('not crossed')

def entry(amount):
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    print(now)

    print('entry')
    print(amount)
    if amount > 0:
        open_trade = {'side': 'long'}
    else:
        open_trade = {'side': 'short'}
    sleep(300)

def close_position():
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    print(now)

    print('close position')
    api.close_position()
    open_trade = None


if __name__=='__main__':
    while(1):
        try:
            main()
        finally:
            sleep(3)
