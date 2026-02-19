# J Bravo Strategy Module - v1.1
# Mission: Trend following using EMA 10/20 and Macro Signals
# Portfolio: BTC, SOL, LINK, AVAX, DOGE, PEPE (ETH BYPASSED)

class BravoStrategy:
    def __init__(self, tickers):
        self.tickers = tickers
        self.ema_fast = 10
        self.ema_slow = 20

    def calculate_ema(self, data, period):
        if not data or len(data) < period: return 0
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

if __name__ == "__main__":
    # ETH is excluded per Big Homie's directive
    tickers = ["BTC", "SOL", "LINK", "AVAX", "DOGE", "PEPE"]
    bravo = BravoStrategy(tickers)
    
    print("📋 CURRENT MARKET AUDIT (ALTCOIN FLEET):")
    # BTC Check (Simulation)
    print(f"BTC: {bravo.check_trend('BTC', [64000, 64500, 65000, 65500, 66000])}")
    # SOL Check (Simulation)
    print(f"SOL: {bravo.check_trend('SOL', [140, 142, 145, 148, 150])}")
    # DOGE Check (Simulation)
    print(f"DOGE: {bravo.check_trend('DOGE', [0.15, 0.14, 0.13, 0.12, 0.11])}")
