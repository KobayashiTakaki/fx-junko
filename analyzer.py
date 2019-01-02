import datetime
from time import sleep
import pandas as pd
import numpy as np
import db.db  as db
import api.oanda_api as oanda_api

conn = db.conn
db_time_fromat = db.time_format

def now_in_unixtime():
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    return int(now.timestamp())

def loop():
    update_price_data()
    update_trade_data()
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    db.write_log('analyzer', 'updated data')

def is_macd_crossed(use_current=False):
    df = pd.read_sql_query('select datetime, close from prices order by datetime;', conn)

    if use_current:
        candle = oanda_api.get_candles(self.instrument, self.params, False)
        df_current = pd.DataFrame(candle).loc[:,['datetime', 'close']]
        df = df.append(df_current, ignore_index = True)

    df = calc_macd(df)

    price_last = df.iloc[-2]
    price_newer = df.iloc[-1]

    if price_last['macd_direction'] == price_newer['macd_direction']:
        return False, 0
    elif price_last['macd_direction'] < price_newer['macd_direction']:
        #シグナルを上向きにクロス
        return True, 1
    else:
        #シグナルを下向きにクロス
        return True, -1

def is_entry_interval_enough():
    df = pd.read_sql_query('select datetime,crossed from prices where crossed <> 0 order by datetime;', conn)
    tz = datetime.timezone.utc

    #前回クロスと前々回クロスの間の時間
    last_cross_interval = (
        datetime.datetime.strptime(df.iloc[-1]['datetime'], db_time_fromat)
        - datetime.datetime.strptime(df.iloc[-2]['datetime'], db_time_fromat)
    )
    db.write_log('analyzer', 'last_cross_interval ' + str(last_cross_interval))

    #前回クロスと今の間の時間
    interval_from_last_cross = (
        datetime.datetime.now(tz)
        - datetime.datetime.strptime(df.iloc[-1]['datetime'], db_time_fromat)
    )
    db.write_log('analyzer', 'interval_from_last_cross ' + str(interval_from_last_cross))

    enough_time = datetime.timedelta(minutes=55)

    #前回クロスと前々回クロスの間が十分離れていない
    #かつ前回クロスと今が十分離れていない場合、False
    if (last_cross_interval < enough_time
        and interval_from_last_cross < enough_time):
        return False
    else:
        return True

def is_macd_trending(direction, least_slope=0):
    count = 3

    #最新のレコードをcount件取得
    df = pd.read_sql_query(
        'select datetime, macd from prices order by datetime desc '
        + 'limit ' + str(count) + ';'
        , conn
    )
    #降順で取得したのを昇順に変更
    df = df.sort_values('datetime')

    #macdの値の近似直線の傾きを算出
    y = list(df['macd'])
    x = np.linspace(1, len(y), len(y))
    slope = np.polyfit(x, y, 1)[0]

    db.write_log('analyzer', 'macd slope: ' + str(slope))
    if direction == 'down':
        if slope <= least_slope:
            return True

    if direction == 'up':
        if slope >= least_slope:
            return True

    return False

def update_price_data():
    price_header = [
        'datetime',
        'open',
        'high',
        'low',
        'close',
        'macd',
        'macd_signal',
        'macd2',
        'macd_direction',
        'crossed'
    ]

    params = {
        'granularity': 'M5',
        'toTime': now_in_unixtime(),
        'count': 60,
        'completed_only': True
    }

    candles = oanda_api.get_candles(params=params)
    df = pd.DataFrame(candles)
    df = calc_macd(df)
    df.reindex(columns=price_header).to_sql('prices', conn, if_exists="replace")

def calc_macd(df):
    macd = pd.DataFrame()
    macd['ema12'] = df['close'].ewm(span=12).mean()
    macd['ema26'] = df['close'].ewm(span=26).mean()
    macd['macd'] = macd['ema12'] - macd['ema26']
    macd['signal'] = macd['macd'].rolling(window=9).mean()
    df['macd'] = macd['macd']
    df['macd_signal'] = macd['signal']
    df['macd2'] = macd['macd'] - macd['signal']
    #macd_direction: macdがシグナルより上なら1, シグナル以下なら-1
    df['macd_direction'] = df['macd2'].apply(lambda v: 1 if v > 0 else -1)

    #macdのcrossを判定
    for i in range(1, len(df)):
        last_price = df.iloc[i-1]
        price = df.iloc[i]
        if last_price['macd_direction'] > price['macd_direction']:
            #1つ前のmacd_drectionが大きい->下向きにクロスした
            df.at[i, 'crossed'] = str(-1)
        elif last_price['macd_direction'] < price['macd_direction']:
            #1つ前のmacd_drectionが小さい->上向きにクロスした
            df.at[i, 'crossed'] = str(1)
        else:
            df.at[i, 'crossed'] = str(0)

    return df

def update_trade_data():
    trades_header = [
        'tradeId',
        'instrument',
        'price',
        'openTime',
        'state',
        'initialUnits',
        'realizedPL',
        'unrealizedPL',
        'averageClosePrice',
        'closeTime'
    ]
    trades = oanda_api.get_trades('ALL', 10)
    df = pd.DataFrame(trades)
    df.reindex(columns=trades_header).to_sql('trades', conn, if_exists="replace")

def refresh_open_trade():
    update_trade_data()
    df = pd.read_sql_query(
        "select * from trades where state = 'OPEN' order by openTime;"
        , conn)

    if len(df) > 1:
        for i in range(0, len(df)-1):
            oanda_api.close_trade(df.at[i, 'tradeId'])

    if len(df) == 0:
        return None

    return df.iloc[-1]

def is_exit_interval_enough():
    open_trade = pd.read_sql_query(
        "select * from trades where state = 'OPEN' order by openTime;"
        , conn)
    if len(open_trade > 0):
        open_time = datetime.datetime.strptime(
            open_trade.iloc[0]['openTime'],
            db_time_fromat
        )
        print(open_time)
        now = datetime.datetime.now(datetime.timezone.utc)
        if now - open_time > datetime.timedelta(minutes=5):
            return True

    return False

def market_trend():
    df = pd.read_sql_query("select macd from prices;", conn)
    macd_positive = df.query('macd > 0')
    if len(macd_positive)/len(df) > 0.7:
        return 1
    if len(macd_positive)/len(df) < 0.3:
        return -1

    return 0

if __name__=='__main__':
    try:
        loop()
    except Exception as e:
        db.write_log('exception', str(e))
    finally:
        sleep(120)
