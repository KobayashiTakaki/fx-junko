import datetime
from time import sleep
import pandas as pd
import db.db  as db
import api.oanda_api as oanda_api

db = db.Db()
conn = db.conn
db_time_fromat = db.time_format
oanda_api = oanda_api.OandaApi()

def now_in_unixtime():
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    return int(now.timestamp())

def is_macd_crossed(candle):
    df = pd.read_sql_query('select datetime,close from prices;', conn)
    df_current = pd.DataFrame(candle).loc[:,['datetime', 'close']]
    df = df.append(df_current, ignore_index = True)
    df = calc_macd(df)

    price_last = df.iloc[-2]
    price_current = df.iloc[-1]

    if price_last['macd_direction'] == price_current['macd_direction']:
        return False, 0
    elif price_last['macd_direction'] < price_current['macd_direction']:
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
    print('last_cross_interval ' + str(last_cross_interval))

    #前回クロスと今の間の時間
    interval_from_last_cross = (
        datetime.datetime.now(tz)
        - datetime.datetime.strptime(df.iloc[-1]['datetime'], db_time_fromat)
    )
    print('interval_from_last_cross ' + str(interval_from_last_cross))

    enough_time = datetime.timedelta(minutes=55)

    #前回クロスと前々回クロスの間が十分離れていない
    #かつ前回クロスと今が十分離れていない場合、False
    if (last_cross_interval < enough_time
        and interval_from_last_cross < enough_time):
        return False
    else:
        return True

def is_macd_keep_going(direction):
    count = 3

    #最新のレコードをcount件取得
    df = pd.read_sql_query(
        'select datetime, close from prices order by datetime desc '
        + 'limit ' + str(count) + ';'
        , conn
    )

    # print(df)
    if direction == 'down':
        #closeの降順ソートと日時の昇順ソートが一致->下がり続けている
        if list(df.sort_values('close', ascending=False).index) \
            == list(df.sort_values('datetime').index):
            return True
    if direction == 'up':
        #closeの昇順ソートと日時の昇順ソートが一致->上がり続けている
        if list(df.sort_values('close').index) \
            == list(df.sort_values('datetime').index):
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



if __name__=='__main__':
    while(1):
        try:
            update_price_data()
            update_trade_data()
            tz = datetime.timezone.utc
            now = datetime.datetime.now(tz)
            print(now)
            print('updated')
        except Exception as e:
            print(e)
            continue
        finally:
            sleep(120)
