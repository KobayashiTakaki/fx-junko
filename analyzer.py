import datetime
from time import sleep
import pandas as pd
import numpy as np
import db.db  as db
import api.oanda_api as oanda_api
import util.price_util as price_util

conn = db.conn
db_time_format = db.time_format

# TODO: 5分足と15分足を切り替えられるようにする
# TODO: DataFrameを作成する際にsort=Trueを指定する
# TODO: DataFrameをDBに書き込む際にindex=Falseを指定する

def is_macd_crossed(minutes=5):
    table_name = 'prices' if minutes == 5 else 'prices_{}min'.format(minutes)

    df = pd.read_sql_query('select * from ' + table_name + ' order by datetime;', conn)

    price_last = df.iloc[-2]
    price_newer = df.iloc[-1]

    max_macd = 0.045 if minutes == 5 else 0.03

    if price_last['macd_direction'] < price_newer['macd_direction']:
        if float(price_last['macd']) > -max_macd:
            #シグナルを上向きにクロス
            #かつ、クロス時のmacdが低すぎない
            return True, 1
        else:
            db.write_log('analyzer', 'last macd: ' + '{0:.5f}'.format(price_last['macd']) + '. too low.')
    elif price_last['macd_direction'] > price_newer['macd_direction']:
        if float(price_last['macd']) < max_macd:
            #シグナルを下向きにクロス
            #かつ、クロス時のmacdが高すぎない
            return True, -1
        else:
            db.write_log('analyzer', 'last macd: ' + '{0:.5f}'.format(price_last['macd']) + '. too high.')

    return False, 0

def is_cross_interval_enough(minutes=5):
    df = pd.read_sql_query('select datetime,crossed from prices where crossed <> 0 order by datetime;', conn)

    #pricesテーブルにcrossedのレコードが3件以上無いならTrue
    if len(df) < 3:
        return True

    #-1回クロスと-2回クロスの間の時間
    cross_interval_1 = (
        datetime.datetime.strptime(df.iloc[-1]['datetime'], db_time_format)
        - datetime.datetime.strptime(df.iloc[-2]['datetime'], db_time_format)
    )
    db.write_log('analyzer', 'cross_interval_1: ' + str(cross_interval_1))

    #-2回クロスと-3回クロスの間の時間
    cross_interval_2 = (
        datetime.datetime.strptime(df.iloc[-2]['datetime'], db_time_format)
        - datetime.datetime.strptime(df.iloc[-3]['datetime'], db_time_format)
    )
    db.write_log('analyzer', 'cross_interval_2: ' + str(cross_interval_2))

    enough_minutes = minutes * 12
    enough_time = datetime.timedelta(minutes=enough_minutes)

    #-1回クロスと-2回クロスの間が十分離れていない
    #かつ-2回クロスと-3回クロスの間が十分離れていない場合、False
    if (cross_interval_1 < enough_time
        and cross_interval_2 < enough_time):
        return False
    else:
        return True

def is_close_last_stop_loss(side):
    last_stop = pd.read_sql_query(
        'select * from trades '
        + 'where stopLossOrderState = \'FILLED\' '
        + 'order by closeTime desc limit 1;'
        ,conn
    )
    if len(last_stop) > 0:
        last_stop = last_stop.iloc[0]
    else:
        db.write_log('analyzer', 'no stop loss recently')
        #stop lossが執行されたレコードが無ければFalse
        return False

    #前回のstop lossから経過した時間
    interval_from_last_stop = (
        datetime.datetime.now(datetime.timezone.utc) -
        datetime.datetime.strptime(last_stop['closeTime'], db_time_format)
    )
    enough_time = datetime.timedelta(minutes=60)

    #十分時間が経過していたらFalse
    if interval_from_last_stop > enough_time:
        db.write_log('analyzer', 'passed enough time from last stop loss')
        return False

    last_stop_side = 'buy' if last_stop['initialUnits'] > 0 else 'sell'

    #最近のstop lossと同じsideだったらTrue
    if last_stop_side == side:
        db.write_log('analyzer', 'same side as recent stop loss')
        return True

    return False

def is_macd_trending(direction, least_slope=0, count=3, use_current=False, minutes=5):
    table_name = 'prices' if minutes == 5 else 'prices_{}min'.format(minutes)
    df = None

    if use_current:
        df = pd.read_sql_query(
            'select * from ' + table_name + ';'
            , conn
        )
        instrument = "USD_JPY"
        params = {
            'granularity': 'S5',
            'count': 1
        }
        candle = oanda_api.get_candles(instrument, params, False)
        df_current = pd.DataFrame(candle)
        df = df.append(df_current, ignore_index = True)
        df = df.sort_values('datetime')
        df = price_util.calc_macd(df).tail(count)

    else:
        #最新のレコードをcount件取得
        df = pd.read_sql_query(
            'select datetime, macd from ' + table_name + ' order by datetime desc '
            + 'limit ' + str(count) + ';'
            , conn
        )
        #降順で取得したのを昇順に変更
        df = df.sort_values('datetime')

    #macdの値の近似直線の傾きを算出
    y = list(df['macd'])
    x = np.linspace(1, len(y), len(y))
    slope = np.polyfit(x, y, 1)[0]

    if direction == 'down':
        if slope <= least_slope:
            db.write_log('analyzer', 'macd slope: ' + '{0:.5f}'.format(slope))
            return True

    if direction == 'up':
        if slope >= least_slope:
            db.write_log('analyzer', 'macd slope: ' + '{0:.5f}'.format(slope))
            return True

    return False

def is_exit_interval_enough(open_trade, minutes=5):
    open_time = datetime.datetime.strptime(
        open_trade['openTime'],
        db_time_format
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    if now - open_time > datetime.timedelta(minutes=minutes):
        return True

    return False

def update_long_price_data():
    price_header = [
        'datetime',
        'open',
        'high',
        'low',
        'close'
    ]
    params = {
        'granularity': 'H1',
        'count': 24,
        'completed_only': True
    }

    candles = oanda_api.get_candles(params=params)
    df = pd.DataFrame(candles)
    df.reindex(columns=price_header).to_sql('long_prices', conn, if_exists="replace")

def market_trend():
    df = pd.read_sql_query("select close from long_prices order by datetime;", conn)
    #closeの値の近似直線の傾きを算出
    y = list(df['close'])
    x = np.linspace(1, len(y), len(y))
    slope = np.polyfit(x, y, 1)[0]
    db.write_log('analyzer', 'long_price_slope: ' + str(slope))
    #どのくらいの傾きにするのが適当か調べるため今のところは0を返す
    return 0

def is_scalping_suitable():
    table_name = 'prices_1min'
    time_from = (datetime.datetime.now(datetime.timezone.utc)\
        - datetime.timedelta(minutes=60)).strftime(db_time_format)
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'where datetime > \'' + time_from + '\';'
        ,conn
    )
    max_price = df['high'].max()
    min_price = df['low'].min()
    if max_price - min_price < 0.1:
        db.write_log('analyzer', 'scalping not suitable')
        return False
    else:
        return True

def is_last_price_move_big():
    table_name = 'prices'
    #最新の2行を取得
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc limit 5;'
        ,conn
    )
    #highとlowの差が大きかったらTrue
    max_price = df['high'].max()
    min_price = df['low'].min()
    if max_price - min_price > 0.1:
        return True

    return False

def get_scal_side():
    table_name = 'prices'
    time_from = (datetime.datetime.now(datetime.timezone.utc)\
    - datetime.timedelta(minutes=60) 
    ).strftime(db_time_format)
    
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'where datetime > \'' + time_from + '\' '
        + 'order by datetime;'
        , conn
    )

    #closeの傾きを計算
    y = list(df['close'])
    x = np.linspace(1, len(y), len(y))
    price_slope = np.polyfit(x, y, 1)[0]

    db. write_log ('analyzer','price_slope: {0:.5f}'.format(price_slope))

    border_slope = 0.03
    if price_slope > border_slope:
        return 'buy'
    elif price_slope < -border_slope:
        return 'sell'
    else:
        return 'both'

if __name__=='__main__':
    try:
        loop()
    except Exception as e:
        db.write_log('exception', str(e))
    finally:
        sleep(120)
