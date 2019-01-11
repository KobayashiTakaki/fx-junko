import pandas as pd
import db.db  as db

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
