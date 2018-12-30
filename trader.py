import datetime
from time import sleep
import api.oanda_api as oanda_api
import api.twitter_api as twitter_api
import analizer

instrument = 'USD_JPY'
params = {
    'granularity': 'S5',
    'count': 1
}

oanda_api = oanda_api.OandaApi()
twitter_api = twitter_api.TwitterApi()

open_position = None

def main():
    if open_position:
        print('i have a open position')

        if open_position['side'] == 'buy':
            if analizer.is_macd_keep_going('down'):
                close_position()

        if open_position['side'] == 'sell':
            if analizer.is_macd_keep_going('up'):
                close_position()

        candle = oanda_api.get_candles(instrument, params, False)
        if analizer.is_macd_crossed(candle)[0]:
            close_position()

    else:
        #ポジションがない場合
        print('i dont have a open position')

        candle = oanda_api.get_candles(instrument, params, False)
        is_macd_crossed = analizer.is_macd_crossed(candle)

        if is_macd_crossed[0] and analizer.is_entry_interval_enough():
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
    oanda_api.market_order(amount)

    open_position = oanda_api.get_open_positions()[0]
    action = 'entry'
    feeling = 'neutral'
    start_side = ''
    start_price = ''

    if amount > 0:
        open_position = {'side': 'buy'}
        start_side = 'buy'
    else:
        open_position = {'side': 'sell'}
        start_side = 'sell'

    info = [
        "[Entry]",
        start_side + " " + instrument + "@" + start_price
    ]
    twitter_api.tweet(action, feeling, info)

    #エントリーしたら5分我慢
    sleep(300)

def close_position():
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    print(now)

    print('close position')
    oanda_api.close_all_positions()
    open_position = None

    last_position = oanda_api.get_last_closed_position()

    #instrument = instrument.replace('_', '/')
    #start_side = 'buy'
    #start_price = '110.123'
    #end_side = 'sell'
    #end_price = '110.345'
    #pips = last_position.pl
    # action = ''
    # feeling = ''
    # info = [
    #     "[Position Close]",
    #     start_side + " " + instrument + "@" + start_price,
    #     end_side + " " + instrument + "@" + end_price,
    #     pips + " pips"
    # ]
    # if pips > 0:
    #     action = 'take_profit'
    #     feeling = 'positive'
    # else:
    #     action = 'losscut'
    #     feeling = 'negative'
    # twitter_api.tweet(action, feeling, info)


if __name__=='__main__':
    while(1):
        try:
            main()
        except Exception as e:
            print(e)
            continue
        finally:
            sleep(3)
