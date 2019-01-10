import datetime
from time import sleep
import pandas as pd
import numpy as np
import db.db  as db
import api.oanda_api as oanda_api

conn = db.conn
db_time_fromat = db.time_format

# TODO: 5分足と15分足を切り替えられるようにする

def now_in_unixtime():
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    return int(now.timestamp())

def loop():
    update_price_data()
    update_trade_data()
    db.write_log('analyzer', 'updated data')

def is_macd_crossed(use_current=False):
    df = pd.read_sql_query('select * from prices order by datetime;', conn)

    if use_current:
        candle = oanda_api.get_candles(self.instrument, self.params, False)
        df_current = pd.DataFrame(candle).loc[:,['datetime', 'close']]
        df = df.append(df_current, ignore_index = True)
        df = calc_macd(df)

    price_last = df.iloc[-2]
    price_newer = df.iloc[-1]

    max_macd = 0.045

    if price_last['macd_direction'] < price_newer['macd_direction']:
        if price_last['macd'] > -max_macd:
            #シグナルを上向きにクロス
            #かつ、クロス時のmacdが低すぎない
            return True, 1
        else:
            db.write_log('last macd: ' + '0:.5f'.format(price_last['macd']) + '. too low.')
    elif price_last['macd_direction'] > price_newer['macd_direction']:
        if price_last['macd'] < max_macd:
            #シグナルを下向きにクロス
            #かつ、クロス時のmacdが高すぎない
            return True, -1
        else:
            db.write_log('last macd: ' + '0:.5f'.format(price_last['macd']) + '. too high.')

    return False, 0

def is_cross_interval_enough():
    df = pd.read_sql_query('select datetime,crossed from prices where crossed <> 0 order by datetime;', conn)

    #pricesテーブルにcrossedのレコードが3件以上無いならTrue
    if len(df) < 3:
        return True

    #-1回クロスと-2回クロスの間の時間
    cross_interval_1 = (
        datetime.datetime.strptime(df.iloc[-1]['datetime'], db_time_fromat)
        - datetime.datetime.strptime(df.iloc[-2]['datetime'], db_time_fromat)
    )
    db.write_log('analyzer', 'cross_interval_1: ' + str(cross_interval_1))

    #-2回クロスと-3回クロスの間の時間
    cross_interval_2 = (
        datetime.datetime.strptime(df.iloc[-2]['datetime'], db_time_fromat)
        - datetime.datetime.strptime(df.iloc[-3]['datetime'], db_time_fromat)
    )
    db.write_log('analyzer', 'cross_interval_2: ' + str(cross_interval_2))

    enough_time = datetime.timedelta(minutes=55)

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
        datetime.datetime.strptime(last_stop['closeTime'], db_time_fromat)
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

def is_macd_trending(direction, least_slope=0, count=3, use_current=False):
    df = None

    if use_current:
        df = pd.read_sql_query(
            'select * from prices;'
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
        df = calc_macd(df).tail(count)

    else:
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

def update_trade_data(count=10):
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
        'closeTime',
        'stopLossOrderState',
        'trailingStopLossOrderState',
        'trailingStopLossOrderDistance',
        'is_scal'
    ]
    #oanda_apiからtradeを取得
    #DataFrameのindexとしてtradeIdを設定
    res_trades = oanda_api.get_trades('ALL', count)
    fetched_trades = pd.DataFrame(res_trades).set_index('tradeId')

    #tradesテーブルにあるレコードを取得
    #DataFrameのindexとしてtradeIdを設定
    trades_records = pd.read_sql_query(
        'select * from trades;'
        , conn
    ).set_index('tradeId')

    for i, row in fetched_trades.iterrows():
        #tradesテーブルに存在するtradeの場合
        if i in trades_records.index.values:
            #削除して、fetched_tradesのレコードを追加する
            trades_records = trades_records.drop(i, axis=0)
            trades_records = trades_records.append(row)
        #tradesテーブルに存在しないtradeの場合
        else:
            #fetched_tradesのレコードを追加する
            trades_records = trades_records.append(row)

    #indexに指定していた列をデータに戻す
    trades_records = trades_records.reset_index()

    #列並べ替え、tradeIdでソートしてDBに書き込み
    trades_records.reindex(columns=trades_header)\
    .sort_values('tradeId').reset_index(drop=True)\
    .to_sql('trades', conn, if_exists="replace")

def refresh_open_trade():
    update_trade_data()
    df = pd.read_sql_query(
        "select * from trades where state = 'OPEN' order by openTime;"
        , conn)

    #複数tradeがあったら最新のtradeだけ残して全部クローズする
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
        now = datetime.datetime.now(datetime.timezone.utc)
        if now - open_time > datetime.timedelta(minutes=5):
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

if __name__=='__main__':
    try:
        loop()
    except Exception as e:
        db.write_log('exception', str(e))
    finally:
        sleep(120)
