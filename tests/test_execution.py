from backend.services.execution import calculate_orders


class TestCalculateOrders:
    def test_buy_when_no_position(self):
        positions = []
        targets = {"AAPL": 10000.0}
        prices = {"AAPL": 200.0}
        orders = calculate_orders(positions, targets, prices)
        assert len(orders) == 1
        assert orders[0]["side"] == "buy"
        assert orders[0]["qty"] == 50  # 10000 / 200

    def test_sell_when_over_target(self):
        positions = [{"symbol": "AAPL", "qty": 100.0}]
        targets = {"AAPL": 0.0}
        prices = {"AAPL": 200.0}
        orders = calculate_orders(positions, targets, prices)
        assert len(orders) == 1
        assert orders[0]["side"] == "sell"
        assert orders[0]["qty"] == 100

    def test_no_order_when_at_target(self):
        positions = [{"symbol": "AAPL", "qty": 50.0}]
        targets = {"AAPL": 10000.0}
        prices = {"AAPL": 200.0}
        orders = calculate_orders(positions, targets, prices)
        assert len(orders) == 0

    def test_whitelist_filtering(self):
        positions = []
        targets = {"AAPL": 10000.0, "GOOG": 5000.0}
        prices = {"AAPL": 200.0, "GOOG": 100.0}
        orders = calculate_orders(positions, targets, prices, only_allow_symbols=["AAPL"])
        symbols = [o["symbol"] for o in orders]
        assert "GOOG" not in symbols
        assert "AAPL" in symbols

    def test_position_limit_enforced(self):
        positions = [
            {"symbol": "AAPL", "qty": 10.0},
            {"symbol": "MSFT", "qty": 10.0},
        ]
        targets = {
            "GOOG": 5000.0,
            "TSLA": 3000.0,
            "AMZN": 8000.0,
        }
        prices = {"GOOG": 100.0, "TSLA": 100.0, "AMZN": 100.0}
        orders = calculate_orders(positions, targets, prices, max_positions=3)
        buy_orders = [o for o in orders if o["side"] == "buy"]
        # 2 existing + max 1 new = 3 total positions
        assert len(buy_orders) <= 1

    def test_sells_always_allowed_despite_limit(self):
        """Sell orders should not be limited by max_positions."""
        positions = [
            {"symbol": "AAPL", "qty": 50.0},
            {"symbol": "MSFT", "qty": 50.0},
            {"symbol": "GOOG", "qty": 50.0},
        ]
        targets = {"AAPL": 0.0, "MSFT": 0.0, "GOOG": 0.0}
        prices = {"AAPL": 200.0, "MSFT": 300.0, "GOOG": 100.0}
        orders = calculate_orders(positions, targets, prices, max_positions=1)
        sell_orders = [o for o in orders if o["side"] == "sell"]
        assert len(sell_orders) == 3

    def test_no_price_skips_symbol(self):
        positions = []
        targets = {"AAPL": 10000.0}
        prices = {}
        orders = calculate_orders(positions, targets, prices)
        assert len(orders) == 0
