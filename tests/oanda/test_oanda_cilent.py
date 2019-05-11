import unittest
from unittest.mock import MagicMock
from unittest.mock import patch
from oanda import client
import v20
import datetime

class TestOandaClient(unittest.TestCase):
    @patch('oanda.client.Client.get_context')
    def setUp(self, mock_get_context):
        mock_get_context.return_value = MagicMock()
        self.client = client.Client()
        self.client.account_id = 1

    @patch('oanda.client.formatter')
    def test_get_candles(self, mock_formatter):
        mock_res = MagicMock(status=200)
        self.client.context.instrument.candles.return_value = mock_res
        actual = self.client.get_candles()
        # formatter.format_candles()が実行されること
        mock_formatter.format_candles.assert_called()
        # formatter.format_candles()の戻り値が返却されること
        self.assertEqual(actual, mock_formatter.format_candles())

    @patch('oanda.client.formatter')
    def test_get_current_candle(self, mock_formatter):
        mock_res = MagicMock(status=200)
        self.client.context.instrument.candles.return_value = mock_res
        actual = self.client.get_current_candle()
        # formatter.format_candle()が実行されること
        mock_formatter.format_candle.assert_called()
        # formatter.format_candle()の戻り値が返却されること
        self.assertEqual(actual, mock_formatter.format_candle())

    def test_market_order(self):
        mock_res = MagicMock(status=201)
        self.client.context.order.market.return_value = mock_res
        self.client.market_order(1)
        self.client.context.order.market.assert_called()

    @patch('oanda.client.formatter')
    def test_get_trade(self, mock_formatter):
        mock_res = MagicMock(status=200)
        self.client.context.trade.get.return_value = mock_res
        actual = self.client.get_trade(1)
        # formatter.format_trade()が実行されること
        mock_formatter.format_trade.assert_called()
        # formatter.format_trade()の戻り値が返却されること
        self.assertEqual(actual, mock_formatter.format_trade())

    @patch('oanda.client.formatter')
    def test_get_open_trade(self, mock_formatter):
        mock_res = MagicMock(status=200)

        # responseのデータが空の場合Noneが返ること
        mock_res.get.return_value = []
        self.client.context.trade.list_open.return_value = mock_res
        actual = self.client.get_open_trade()
        self.assertIsNone(actual)

        # responseのデータが1件だけの場合
        mock_res.get.return_value = [v20.trade.Trade(id=1)]
        self.client.context.trade.list_open.return_value = mock_res
        actual = self.client.get_open_trade()
        # formatter.format_trade()が実行されること
        mock_formatter.format_trade.assert_called()
        # formatter.format_trade()の戻り値が返却されること
        self.assertEqual(actual, mock_formatter.format_trade())

        # responseのデータが2件以上の場合
        trade1 = v20.trade.Trade(id=1)
        trade2 = v20.trade.Trade(id=2)
        trades = [trade1, trade2]
        mock_res.get.return_value = trades
        self.client.context.trade.list_open.return_value = mock_res
        # client.last_trade()が実行されること
        self.client.last_trade = MagicMock()
        actual = self.client.get_open_trade()
        self.client.last_trade.assert_called_with(trades)
        # client.last_trade()の戻り値が返却されること
        self.assertEqual(actual, self.client.last_trade(trades))

    @patch('oanda.client.formatter')
    def test_last_trade(self, mock_formatter):
        self.client.close_trade = MagicMock()
        trade1 = v20.trade.Trade(id=1)
        trade2 = v20.trade.Trade(id=2)
        trade3 = v20.trade.Trade(id=3)
        trades = [
            trade2,
            trade3,
            trade1
        ]
        actual = self.client.last_trade(trades)
        # 最新以外のtradeのidでclose_trade()が実行されること
        self.client.close_trade.assert_any_call(trade1.id)
        self.client.close_trade.assert_any_call(trade2.id)

        # 最新のtradeがformatter.format_tradeに渡されて、その戻り値が返却されること
        self.assertEqual(actual, mock_formatter.format_trade(trade3))

    def test_close_trade(self):
        mock_res = MagicMock(status=200)
        self.client.context.trade.close.return_value = mock_res
        self.client.close_trade(1)

        # context.trade.closeが実行されること
        self.client.context.trade.close.assert_any_call(self.client.account_id, '1')

    def test_is_market_open(self):
        time_format = '%Y-%m-%d %H:%M:%S%z'
        self.client.get_candles = MagicMock()
        # candleの時間が30分以上前だったらfalseが返却されること
        time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30))\
                .strftime(time_format)
        candle = {'datetime': time}
        self.client.get_candles.return_value = [candle]
        actual = self.client.is_market_open()
        self.assertFalse(actual)

        # candleの時間が29分以上前だったらtrueが返却されること
        time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=29))\
                .strftime(time_format)
        candle = {'datetime': time}
        self.client.get_candles.return_value = [candle]
        actual = self.client.is_market_open()
        self.assertTrue(actual)

if __name__ == '__main__':
    unittest.main()
