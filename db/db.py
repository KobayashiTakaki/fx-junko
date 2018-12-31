import sqlite3
import datetime

class Db():
    dbname = 'db/db.sqlite3'
    time_format = '%Y-%m-%d %H:%M:%S%z'

    def __init__(self):
        self.conn = sqlite3.connect(self.dbname)

    def write_log(self, type, content):
        self.conn.execute(
            'create table if not exists logs ('
            + 'datetime text not null primary key,'
            + 'type text,'
            + 'content text'
            + ');'
        )
        sql = 'insert into logs (datetime, type, content)'\
            + ' values (?, ?, ?);'
        now = datetime.datetime.now().strftime(self.time_format)
        values = (now, type, content)
        self.conn.execute(sql, values)
        self.conn.commit()
