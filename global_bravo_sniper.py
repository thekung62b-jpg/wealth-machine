# Global Bravo Sniper - v1.0
# Mission: 24/7 Trend Following across London, NY, and Tokyo sessions

class GlobalBravoSniper:
    def __init__(self):
        self.sessions = {
            "London": {"start": 3, "end": 12, "focus": ["GBPUSD", "BTC"]},
            "NY": {"start": 8, "end": 17, "focus": ["SPY", "Gold", "SOL"]},
            "Tokyo": {"start": 19, "end": 4, "focus": ["USDJPY", "BTC"]}
        }

    def get_active_session(self, current_hour_utc):
        for name, times in self.sessions.items():
            if times["start"] <= current_hour_utc < times["end"]:
                return name, times["focus"]
        return "Gap Session", ["BTC"]

    def apply_bravo_logic(self, ticker, ema_10, ema_20):
        # J Bravo 10/20 EMA Cross Logic
        if ema_10 > ema_20:
            return f"🟢 BULLISH CROSS on {ticker}"
        return f"🔴 BEARISH / NEUTRAL on {ticker}"

if __name__ == "__main__":
    sniper = GlobalBravoSniper()
    # Assume it's 4 AM UTC (London/Tokyo overlap)
    session, targets = sniper.get_active_session(4)
    print(f"🌍 Current Session: {session} | Targeting: {targets}")
