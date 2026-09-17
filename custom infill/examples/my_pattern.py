import math


def my_wave(x: float) -> float:
    """Custom infill pattern: steeper sine with a slow drift."""
    return 0.8 * math.sin(x / 2.0) + 0.1 * math.sin(x / 11.0)
