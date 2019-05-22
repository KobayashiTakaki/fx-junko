import unittest
from unittest.mock import MagicMock
from unittest.mock import patch
import trades.trades
import pandas as pd
import db.table_defs

class TestTraderTrades(unittest.TestCase):
    @patch('oanda.client.Client')
    @patch('trades.trades.DbClient')
    def setUp(self, mock_oanda_client, mock_db_client):
        self.trades = trades.trades.Trades()

    def test_get_open_trades(self):
        open_trade = self.trades.get_open_trade()
        self.assertEqual(open_trade, self.trades.get_open_trade())

    def test_open(self):
        self.trades.update_open_trade = MagicMock()
        self.trades.open(1)
        self.trades.oanda_client.market_order.assert_called_with(1)
        self.trades.update_open_trade.assert_called()

    def test_close(self):
        self.trades.update_open_trade = MagicMock()
        self.trades.close(1)
        self.trades.oanda_client.close_trade.assert_called_with(1)
        self.trades.update_open_trade.assert_called()

    def test_update_open_trade(self):
        self.trades.update_open_trade()
        self.trades.oanda_client.get_open_trade.assert_called()
        self.assertEqual(self.trades.open_trade, self.trades.oanda_client.get_open_trade())

    def test_update_trade_records(self):
        # recordsが空の場合
        records = pd.DataFrame()
        self.trades.db_client.get_open_trade_records.return_value = records
        self.trades.update_trade_records()
        self.trades.db_client.delete_trade_records.assert_not_called()
        self.trades.oanda_client.get_trade.assert_not_called()
        self.trades.db_client.insert_trade_records.assert_not_called()

        # recordsが複数ある場合
        trades = [{'tradeId': 1},{'tradeId': 2}]
        records = pd.DataFrame(trades)
        self.trades.db_client.get_open_trade_records.return_value = records
        self.trades.oanda_client.get_trade.side_effect = trades
        self.trades.update_trade_records()
        self.trades.db_client.delete_trade_records.assert_called_with([1, 2])
        self.trades.oanda_client.get_trade.assert_any_call(1)
        self.trades.oanda_client.get_trade.assert_any_call(2)
        self.trades.db_client.insert_trade_records.assert_called()
