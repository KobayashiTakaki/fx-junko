import sqlite3
import datetime

dbname = 'db/db.sqlite3'
time_format = '%Y-%m-%d %H:%M:%S%z'
conn = sqlite3.connect(dbname)

def write_log(type, content):
    conn.execute(
        'create table if not exists logs ('
        + 'datetime text,'
        + 'type text,'
        + 'content text'
        + ');'
    )
    sql = 'insert into logs (datetime, type, content)'\
        + ' values (?, ?, ?);'
    now = datetime.datetime.now().strftime(time_format)
    values = (now, type, content)
    conn.execute(sql, values)
    conn.commit()

def delete_old_log():
    keep_span = datetime.timedelta(weeks=1)
    keep_from = (datetime.datetime.now() - keep_span).strftime(time_format)
    conn.execute(
        'delete from logs where datetime < '
        + '\'' + keep_from + '\' ;'
    )
    conn.commit()
