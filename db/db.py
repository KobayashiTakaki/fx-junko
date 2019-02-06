import sqlite3
import datetime

dbname = 'db/db.sqlite3'
time_format = '%Y-%m-%d %H:%M:%S%z'
conn = sqlite3.connect(dbname)
