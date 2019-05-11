from oanda import client

class Trades():
    def __init__(self):
        self.client = client.Client()
        self.open_trade = None

    def get_open_trade(self):
        return self.open_trade

    def open(self, units):
        try:
            self.client.market_order(units)
        except Exception as e:
            self.logger.debug(traceback.format_exc())
            raise TradesError(e)
        finally:
            self.update_open_trade()

    def close(self, id):
        try:
            self.client.close_trade(id)
        except Exception as e:
            self.logger.debug(traceback.format_exc())
            raise TradesError(e)
        finally:
            self.update_open_trade()

    def update_open_trade(self):
        try:
            self.open_trade = self.client.get_open_trade()
        except Exception as e:
            self.logger.debug(traceback.format_exc())
            raise TradesError(e)

class TradesError(Exception):
    pass
