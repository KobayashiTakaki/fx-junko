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

open_trade = None

def main():
    if open_trade is not None:
        print('i have a open position')

        if open_trade.initialUnits > 0:
            if analizer.is_macd_keep_going('down'):
                exit()

        else:
            if analizer.is_macd_keep_going('up'):
                exit()

        candle = oanda_api.get_candles(instrument, params, False)
        if analizer.is_macd_crossed(candle)[0]:
            exit()

    else:
        #ポジションがない場合
        print('i dont have a open position')

        candle = oanda_api.get_candles(instrument, params, False)
        is_macd_crossed = analizer.is_macd_crossed(candle)

        if is_macd_crossed[0] and analizer.is_entry_interval_enough():
            if is_macd_crossed[1] == 1:
                #上向きクロスだったら買いでエントリー
                print('entry by buy')
                entry(100)
            else:
                #下向きクロスだったら売りでエントリー
                print('entry by sell')
                entry(-100)
        else:
            print('not crossed')

def entry(amount):
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    print(now)

    response = oanda_api.market_order(amount)
    if response.status == 201:
        print(amount)
        print('entry')
    else:
        raise Exception('entry failed')

    open_trade = oanda_api.get_trades('OPEN', 1)[0]

    action = 'entry'
    feeling = 'neutral'
    start_side = ''
    start_price = open_trade.price

    if open_trade.initialUnits > 0:
        start_side = 'buy'
    else:
        start_side = 'sell'

    info = [
        "[Entry]",
        start_side + " " + instrument + "@" + start_price
    ]
    twitter_api.tweet(action, feeling, info)

    #エントリーしたら5分我慢
    sleep(300)

def exit():
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    print(now)

    side = ''
    if open_trade.initialUnits > 0:
        side = 'long'
    else:
        side = 'short'
    print('close position')

    oanda_api.close_trade(open_trade.id)
    open_trade = None

    last_trade = oanda_api.get_trades('CLOSED', 1)[0]

    instrument = instrument.replace('_', '/')
    start_side = ''
    start_price = last_trade.price
    end_side = ''
    end_price = last_trade.averageClosePrice
    pips = last_trade.realizedPL
    action = ''
    feeling = ''
    info = [
        "[Trade Close]",
        start_side + " " + instrument + "@" + start_price,
        end_side + " " + instrument + "@" + end_price,
        pips + " pips"
    ]
    if pips > 0:
        action = 'take_profit'
        feeling = 'positive'
    else:
        action = 'losscut'
        feeling = 'negative'
    twitter_api.tweet(action, feeling, info)


if __name__=='__main__':
    while(1):
        try:
            main()
        except Exception as e:
            print(e)
            continue
        finally:
            sleep(3)
