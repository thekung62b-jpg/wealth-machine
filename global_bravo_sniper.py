# Global Bravo Sniper - v1.1
# Mission: 24/7 Trend Following across London, NY, and Tokyo sessions
# Targets: BTC, SOL, LINK, AVAX, DOGE, PEPE (ETH BYPASSED)

class GlobalBravoSniper:
    def __init__(self):
        self.sessions = {
            "London": {"start": 3, "end": 12, "focus": ["GBPUSD", "BTC", "SOL"]},
            "NY": {"start": 8, "end": 17, "focus": ["SPY", "Gold", "SOL", "LINK", "AVAX"]},
            "Tokyo": {"start": 19, "end": 4, "focus": ["USDJPY", "BTC", "DOGE", "PEPE"]}
        }

    def get_active_session(self, current_hour_utc):
        for name, times in self.sessions.items():
            if times["start"] <= current_hour_utc < times["end"]:
                return name, times["focus"]
        return "Gap Session", ["BTC", "SOL"]

    def apply_bravo_logic(self, ticker, ema_10, ema_20):
        if ema_10 > ema_20:
            return f"🟢 BULLISH CROSS on {ticker}"
        return f"🔴 BEARISH / NEUTRAL on {ticker}"

if __name__ == "__main__":
    sniper = GlobalBravoSniper()
    # Assume it's 0:00 UTC (Tokyo session)
    session, targets = sniper.get_active_session(0)
    print(f"🌍 Current Session: {session} | Targeting: {targets}")
