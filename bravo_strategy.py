# J Bravo Strategy Module - v1.0
# Mission: Trend following using EMA 10/20 and Macro Signals

class BravoStrategy:
    def __init__(self, tickers):
        self.tickers = tickers
        self.ema_fast = 10
        self.ema_slow = 20

    def calculate_ema(self, data, period):
        # Logic to calculate EMA from price data
        return sum(data[-period:]) / period # Simplified

    def check_trend(self, ticker, price_data):
        fast = self.calculate_ema(price_data, self.ema_fast)
        slow = self.calculate_ema(price_data, self.ema_slow)
        
        if fast > slow:
            return "🚀 BULLISH CROSS (J Bravo Style)"
        elif fast < slow:
            return "⚠️ BEARISH CROSS (Protect Capital)"
        else:
            return "⚖️ SIDEWAYS (No Trade)"

    def check_macro_vix(self, vix_value):
        if vix_value > 30:
            return "🚨 EXTREME FEAR (Look for Bottom)"
        return "Normal Market Conditions"

if __name__ == "__main__":
    bravo = BravoStrategy(["BTC", "ETH", "SOL"])
    # Simulation
    result = bravo.check_trend("BTC", [64000, 64500, 65000, 65500, 66000])
    print(f"J Bravo Signal for BTC: {result}")
