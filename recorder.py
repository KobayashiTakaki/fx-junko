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

def add_trade_record(trade, table_name):
    conn.execute(
        'create table if not exists ' + table_name + '('
        + ','.join(trades_header)
        + ');'
    )
    records = conn.execute('select * from ' + table_name + ' '
        + 'where tradeId = ' + trade['tradeId'] + ';').fetchall()
    if len(records) == 0:
        df = pd.DataFrame(trade, index=[1])
        df.to_sql(table_name, conn, if_exists="append", index=False)

def update_trade_data(table_name):
    #tradesテーブルからOPENのtrade_idを取得
    open_ids = list(pd.read_sql_query(
        'select tradeId from ' + table_name + ' '
        + 'where state=\'OPEN\''
        ,conn
    )['tradeId'])

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
