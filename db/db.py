import sqlite3


def conn:
    dbname = 'db.sqlite3'
    conn = sqlite3.connect(dbname)
    return conn


def store_candles(conn, df):
    corsor = conn.cursor()
