"""Spring easing, the motion feel of Apple's interfaces.

Instead of a fixed curve, a spring is described by its damping: the target is
reached quickly, with at most a hint of overshoot, and slows down like a real
object. Kept free of any Qt import so it can be unit-tested anywhere.

``spring_progress(t, damping)`` maps normalised time t in [0, 1] to progress
(0 at the start, exactly 1 at the end).

    damping 1.0   critically damped: fastest, no overshoot (panels, heights)
    damping 0.8   slight settle, about 1.5 % overshoot (indicators, small moves)
"""

import math

# The envelope must have faded to well under 1 % by t = 1.
_SETTLE = 7.0


def _raw(t: float, damping: float) -> float:
    z = damping
    w0 = _SETTLE / z if z < 1.0 else _SETTLE
    if z < 1.0:
        wd = w0 * math.sqrt(1.0 - z * z)
        return 1.0 - math.exp(-z * w0 * t) * (math.cos(wd * t) + (z * w0 / wd) * math.sin(wd * t))
    # critically damped (damping >= 1 is treated as critical)
    return 1.0 - math.exp(-w0 * t) * (1.0 + w0 * t)


def spring_progress(t: float, damping: float = 0.8) -> float:
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    end = _raw(1.0, damping)
    return _raw(t, damping) / end
