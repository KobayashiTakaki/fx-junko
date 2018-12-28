import datetime
from time import sleep
import pandas as pd
import db.db as db
import api.api as api

conn = db.conn()

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
    df = pd.read_sql_query('select datetime,crossed from prices where crossed <> 0;', conn)

    #print(df)
    last_cross_interval = df.iloc[-1]['datetime']

    return false


def is_macd_against():

    return false


# def last_macd():
#

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
    candles = api.get_candles()
    df = pd.DataFrame(candles)
    df = calc_macd(df)
    df.reindex(columns=price_header).to_sql('prices', conn, if_exists="replace")

def calc_macd(df):
    macd = pd.DataFrame()
    macd['ema12'] = df['close'].ewm(span=12).mean()
    macd['ema26'] = df['close'].ewm(span=26).mean()
    macd['macd'] = macd['ema12'] - macd['ema26']
    macd['signal'] = macd['macd'].ewm(span=9).mean()
    df['macd'] = macd['macd']
    df['macd_signal'] = macd['signal']
    df['macd2'] = macd['macd'] - macd['signal']
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

if __name__=='__main__':
    while(1):
        update_price_data()
        tz = datetime.timezone.utc
        now = datetime.datetime.now(tz)
        print(now)
        print('updated')
        sleep(120)
