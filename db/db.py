import sqlite3

class Db():
    dbname = 'db/db.sqlite3'
    time_format = '%Y-%m-%d %H:%M:%S%z'

    def __init__(self):
        self.conn = sqlite3.connect(self.dbname)
