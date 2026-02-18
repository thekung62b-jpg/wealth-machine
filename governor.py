# King Mode Governor - v1.0
class TokenGovernor:
    def __init__(self, limit_percent=0.8):
        self.limit_threshold = limit_percent
    def check_safety(self, current_tokens):
        return (current_tokens / 1000000) < self.limit_threshold
