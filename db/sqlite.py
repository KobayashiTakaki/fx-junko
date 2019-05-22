import sqlite3
import datetime

class Sqlite():
    def __init__(self):
        self.dbname = 'db/db.sqlite3'
        self.time_format = '%Y-%m-%d %H:%M:%S%z'
        self.conn = sqlite3.connect(self.dbname)

    def get_conn(self):
        return self.conn
