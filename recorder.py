import datetime
import pandas as pd
import db.db  as db
import api.oanda_api as oanda_api
import util.price_util as price_util

conn = db.conn
db_time_fromat = db.time_format

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
    'trailingStopLossOrderDistance'
]

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

def now_in_unixtime():
    tz = datetime.timezone.utc
    now = datetime.datetime.now(tz)
    return int(now.timestamp())

def add_trade_record(trade, table_name):
    create_trades_table(table_name)

    records = conn.execute('select * from ' + table_name + ' '
        + 'where tradeId = ' + trade['tradeId'] + ';').fetchall()
    if len(records) == 0:
        df = pd.DataFrame(trade, index=[1])
        df.to_sql(table_name, conn, if_exists="append", index=False)

def update_trade_data(table_name):
    create_trades_table(table_name)

    #tradesテーブルからOPENのtrade_idを取得
    open_ids = list(pd.read_sql_query(
        'select tradeId from ' + table_name + ' '
        + 'where state=\'OPEN\''
        ,conn
    )['tradeId'])

    if len(open_ids) > 0:
        #joinするため文字列型に変換
        open_ids = list(map(str, open_ids))

        fetched_trades = pd.DataFrame(columns=trades_header)
        for id in open_ids:
            trade = oanda_api.get_trade(id)
            s = pd.Series(trade)
            fetched_trades = fetched_trades.append(s,ignore_index=True)

        conn.execute(
            'delete from '+ table_name + ' where tradeId in ('
            + ','.join(open_ids) + ');'
        )
        conn.commit()

        fetched_trades.to_sql(table_name, conn, if_exists="append", index=False)

def update_price_data():
    params = {
        'granularity': 'M5',
        'toTime': now_in_unixtime(),
        'count': 60,
        'completed_only': True
    }

    candles = oanda_api.get_candles(params=params)
    df = pd.DataFrame(candles)
    df = price_util.calc_macd(df)
    df.reindex(columns=price_header).to_sql('prices', conn, if_exists="replace", index=False)

def create_trades_table(table_name):
    conn.execute(
        'create table if not exists ' + table_name + '('
        + 'tradeId integer primary key, '
        + 'instrument text, '
        + 'price real, '
        + 'openTime text, '
        + 'state text, '
        + 'initialUnits real, '
        + 'realizedPL real, '
        + 'unrealizedPL real, '
        + 'averageClosePrice real, '
        + 'closeTime text,'
        + 'stopLossOrderState text, '
        + 'trailingStopLossOrderState  text, '
        + 'trailingStopLossOrderDistance real'
        + ');'
    )
