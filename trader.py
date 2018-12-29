import datetime
from time import sleep
import api.api as api
import analizer

instrument = 'USD_JPY'
params = {
    'granularity': 'S5',
    'count': 1,
    'completed_only': False
}

is_position_open = False

def main():
    candle = api.get_candles(params)
    is_macd_crossed = analizer.is_macd_crossed(candle)

    if is_position_open:
        print('i have a open position')
    else:
        #ポジションがない場合
        print('i dont have a open position')

        #is_macd_crossedの戻り値がTrueのとき
        if is_macd_crossed[0]:
            if is_macd_crossed[1] == 1:
                #上向きクロスだったら買いでエントリー
                print('entry by buy')
                entry(10000)
            else:
                #下向きクロスだったら売りでエントリー
                print('entry by sell')
                entry(-10000)

        else:
            print('not crossed')

def entry(amount):
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    print(now)

    print('entry')
    print(amount)
    is_position_open = True
    sleep(300)

def close_position():
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    print(now)

    print('close position')
    is_position_open = False

def losscut():
    print('losscut')
    is_position_open = False

if __name__=='__main__':
    while(1):
        try:
            main()
        finally:
            sleep(3)
