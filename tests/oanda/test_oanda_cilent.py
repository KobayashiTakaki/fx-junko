import unittest
from oanda import client

class TestOandaClient(unittest.TestCase):
    def setUp(self):
        self.client = client.Client()

    def test_get_candles(self):
        candles = self.client.get_candles()
        self.assertIsInstance(candles, list)

    def test_get_current_candle(self):
        candle = self.client.get_current_candle()
        self.assertIsInstance(candle, dict)
        self.assertTrue(bool(candle))

    def test_order_open_and_close(self):
        # trade作成
        self.client.market_order(1)

        # open_trade取得
        open_trade = self.client.get_open_trade()
        self.assertIsInstance(open_trade, dict)
        self.assertTrue(bool(open_trade))

        # get_trade
        trade = self.client.get_trade(open_trade['tradeId'])
        self.assertIsInstance(trade, dict)
        self.assertTrue(bool(trade))

        # tradeをclose
        self.client.close_trade(trade['tradeId'])
        trade = self.client.get_open_trade()
        self.assertFalse(bool(trade))

    def test_is_market_open(self):
        res = self.client.is_market_open()
        self.assertIsInstance(res, bool)

if __name__ == '__main__':
    unittest.main()
