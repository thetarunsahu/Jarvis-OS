class AIProvider:
    
    def __init__(self):
        self.name = "None"
        self.status = "NOT_CONNECTED"

    def generate(self, user_input, context=None):
        raise NotImplementedError(
            "AI provider is not connected yet."
        )