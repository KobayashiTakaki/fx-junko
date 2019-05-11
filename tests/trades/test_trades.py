import unittest
from unittest.mock import MagicMock
from unittest.mock import patch
from trades import trades

class TestTraderTrades(unittest.TestCase):
    @patch('oanda.client.Client')
    def setUp(self, mock_client):
        self.trades = trades.Trades()

    def test_get_open_trades(self):
        open_trade = self.trades.get_open_trade()
        self.assertEqual(open_trade, self.trades.get_open_trade())

    def test_open(self):
        self.trades.update_open_trade = MagicMock()
        self.trades.open(1)
        self.trades.client.market_order.assert_called_with(1)
        self.trades.update_open_trade.assert_called()

    def test_close(self):
        self.trades.update_open_trade = MagicMock()
        self.trades.close(1)
        self.trades.client.close_trade.assert_called_with(1)
        self.trades.update_open_trade.assert_called()

    def test_update_open_trade(self):
        self.trades.update_open_trade()
        self.trades.client.get_open_trade.assert_called()
        self.assertEqual(self.trades.open_trade, self.trades.client.get_open_trade())
