"""Stateless frame-domain timing, mirrored by native driver expressions."""


def phase(frame, start=1.0, duration=24.0, speed=1.0, loop=False):
    elapsed = (frame - start) * max(speed, 0.001) / max(duration, 1.0)
    active = elapsed >= 0 and (loop or elapsed < 1)
    return (elapsed % 1 if loop else min(max(elapsed, 0), 1)), active


# Driver variables: s=start, d=duration, v=speed, l=loop. No Python namespace.
ELAPSED = "((frame-s)*max(v,0.001)/max(d,1.0))"
PROGRESS = f"(({ELAPSED}-floor({ELAPSED})) if l else min(max({ELAPSED},0),1))"
ACTIVE = f"(frame>=s and (l or {ELAPSED}<1))"
