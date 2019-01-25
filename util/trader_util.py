import datetime
from time import sleep
import pandas as pd
import numpy as np
import db.db  as db
import api.oanda_api as oanda_api
import util.price_util as price_util

conn = db.conn
db_time_format = db.time_format

def is_macd_crossed(guranularity='M5', within=1):
    table_name = 'prices_{}'.format(guranularity)

    # 最新のpriceをwithin+1件取得(datetimeの降順)
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc limit ' + within+1 + ';'
        , conn)

    # 最新のレコードのdatetimeが古くないか確認
    time_now = datetime.datetime.now(datetime.timezone.utc)
    time_last_price = datetime.datetime.strptime(df.iloc[0]['datetime'], db_time_format)
    max_time = datetime.timedelta(minutes=minutes*5)

    if time_now - time_last_price > max_time:
        raise Exception('is_macd_crossed: price data too old for is_macd_crossed.')

    # withinの件数、クロスを判定
    for i in range(0, within):
        price_newer = df.iloc[i]
        price_older = df.iloc[i+1]
        #シグナルを上向きにクロス
        if price_older['macd_direction'] < price_newer['macd_direction']:
            return True, 1

        #シグナルを下向きにクロス
        elif price_older['macd_direction'] > price_newer['macd_direction']:
            return True, -1

    return False, 0
