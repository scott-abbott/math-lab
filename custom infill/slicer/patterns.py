"""Example infill pattern functions.

Each pattern is a function f(x) -> y_offset used by slicer.infill to bend
an otherwise-straight infill line. Write your own and pass it to the CLI
with --infill-pattern-file / --infill-pattern-func, or use these directly
if importing the slicer as a library.
"""
import math


def lines(x: float) -> float:
    """Plain straight-line infill (the default)."""
    return 0.0


def sine(x: float, amplitude: float = 0.6, wavelength: float = 5.0) -> float:
    """Sinusoidal / wavy infill line."""
    return amplitude * math.sin(2.0 * math.pi * x / wavelength)


def zigzag(x: float, amplitude: float = 0.6, wavelength: float = 5.0) -> float:
    """Triangle-wave (zigzag) infill line."""
    t = (x % wavelength) / wavelength  # 0..1
    triangle = 4 * abs(t - 0.5) - 1     # -1..1..-1 triangle wave
    return amplitude * -triangle


def square(x: float, amplitude: float = 0.6, wavelength: float = 5.0) -> float:
    """Square-wave infill line."""
    t = (x % wavelength) / wavelength
    return amplitude if t < 0.5 else -amplitude


# Convenience: pre-bound versions usable directly as `f(x)` callables.
sine_default = lambda x: sine(x)
zigzag_default = lambda x: zigzag(x)
square_default = lambda x: square(x)

PATTERNS = {
    "lines": lines,
    "sine": sine_default,
    "zigzag": zigzag_default,
    "square": square_default,
}
