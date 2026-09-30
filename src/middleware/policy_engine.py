"""
PolicyEngine — dari specs/04-middleware.md apa adanya.
Decision engine berdasarkan label + confidence.
"""


class PolicyEngine:
    """Decision engine based on classification result."""

    def __init__(self, block_threshold: float = 0.7):
        self.block_threshold = block_threshold

    def decide(self, label: str, confidence: float) -> str:
        if label == "normal":
            return "allow"

        if confidence > self.block_threshold:
            return "block"
        else:
            return "flag"

    def set_block_threshold(self, threshold: float):
        if 0.0 <= threshold <= 1.0:
            self.block_threshold = threshold
