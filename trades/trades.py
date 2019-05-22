import datetime
import db.sqlite
import db.table_defs
import oanda.client
import pandas as pd

class Trades():
    def __init__(self):
        self.oanda_client = oanda.client.Client()
        self.db_client = DbClient()
        self.open_trade = None

    def get_open_trade(self):
        return self.open_trade

    def open(self, units):
        try:
            self.oanda_client.market_order(units)
        except Exception as e:
            raise TradesError('opening trade failed')
        finally:
            self.update_open_trade()
            self.db_client.add_trade_record(self.open_trade)

    def close(self, id):
        try:
            self.oanda_client.close_trade(id)
        except Exception as e:
            raise TradesError('closing trade failed')
        finally:
            self.update_open_trade()

    def update_open_trade(self):
        try:
            self.open_trade = self.oanda_client.get_open_trade()
        except Exception as e:
            raise TradesError('getting open trade failed')

    def update_trade_records(self):
        open_trade_records = self.db_client.get_open_trade_records()
        # 1件も無ければreturn
        if len(open_trade_records) < 1:
            return

        ids = list(open_trade_records['tradeId'])
        self.db_client.delete_trade_records(ids)

        # APIからopen_idのtradeを取得し、DataFrameに追加していく
        header = db.table_defs.get_columns('trades')
        fetched_trades = pd.DataFrame(columns=header)
        for id in ids:
            try:
                trade = self.oanda_client.get_trade(id)
            except Exception as e:
                self.logger.debug(traceback.format_exc())
                raise TradesError(e)
            s = pd.Series(trade)
            fetched_trades = fetched_trades.append(s, ignore_index=True)

        self.db_client.insert_trade_records(fetched_trades)

class DbClient():
    def __init__(self):
        self.conn = db.sqlite.Sqlite().get_conn()

    def create_trades_table(self, table_name='trades'):
        sql = db.table_defs.get_create_table_sql('trades', table_name)
        self.conn.execute(sql)

    def add_trade_record(self, trade, table_name='trades'):
        self.create_trades_table(table_name)

        # 同じidのレコードがあればreturn
        records = conn.execute('select * from ' + table_name + ' '
            + 'where tradeId = ' + trade['tradeId'] + ';').fetchall()
        if len(records) != 0:
            return

        df = pd.DataFrame(trade, index=[1])
        df.to_sql(table_name, self.conn, if_exists="append", index=False)

    def get_open_trade_records(self, table_name='trades'):
        self.create_trades_table(table_name)
        # tradesテーブルからOPENのtrade_idを取得
        open_trade_records = pd.read_sql_query(
            'select tradeId from ' + table_name + ' '
            + 'where state=\'OPEN\''
            ,self.conn
        )
        return open_trade_records

    def delete_trade_records(self, ids, table_name='trades'):
        ids = list(map(str, ids))
        self.conn.execute(
            'delete from '+ table_name + ' where tradeId in ('
            + ','.join(ids) + ');'
        )
        self.conn.commit()

    def insert_trade_records(self, df, table_name='trades'):
        df.to_sql(table_name, self.conn, if_exists="append", index=False)

class TradesError(Exception):
    pass
