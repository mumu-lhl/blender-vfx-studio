"""Bounded native birth schedules; no stored particle simulation history."""

import math

from .nodes import PROGRESS, TIME_PROPS, node


def limits(rate, lifetime):
    """Return the effective rate and allocated slot count displayed by the UI."""
    life = min(max(lifetime, 0.001), 100.0)
    rate = min(max(rate, 0.0), 10000.0, 2048.0 / life)
    return rate, min(max(math.ceil(rate * life), 1), 2048)


def fields(tree, root, value, math_node):
    link = tree.links.new

    # Keep the schedule above the shared motion graph so it remains readable when edited.
    def calc(name, operation, a, b, x, y):
        return math_node(name, operation, a, b, x, y)

    rate = value("Requested Rate", "rate", -3400, 1200, "min(max(p,0),10000)")
    life = value("Particle Lifetime", "lifetime", -3400, 1000, "min(max(p,0.001),100)")
    emission = value("Emission Seconds", "emission_seconds", -3400, 800, "min(max(p,0),100)")
    maximum = calc("Rate Budget", "DIVIDE", 2048, life, -3200, 1200)
    effective = calc("Effective Rate", "MINIMUM", rate, maximum, -3000, 1200)
    working = calc("Nonzero Schedule Rate", "MAXIMUM", effective, 0.001, -2800, 1200)
    count = calc("Lifetime Population", "MULTIPLY", effective, life, -3200, 600)
    count = calc("Required Slots", "CEIL", count, 0, -3000, 600)
    count = calc("At Least One Slot", "MAXIMUM", count, 1, -2800, 600)
    count = calc("Bounded Slots", "MINIMUM", count, 2048, -2600, 600)
    line = node(tree, "GeometryNodeMeshLine", "Emitter Pool", -800, 800)
    line.inputs["Offset"].default_value = (0, 0, 0)
    link(count, line.inputs["Count"])
    progress = value("Effect Progress", None, -3400, 400, PROGRESS, TIME_PROPS)
    span = calc("Motion Span with Tail", "ADD", emission, life, -3200, 200)
    clock = calc("Emitter Motion Time", "MULTIPLY", progress, span, -3000, 400)
    # Compute the scalar birth counter in the driver's double precision, then floor it.
    # Native float32 math can otherwise put an exact high-rate boundary below its birth ID.
    expression = (
        f"floor(({PROGRESS})*(min(max(e,0),100)+max(min(u,100),.001))"
        "*min(max(r,0),10000,2048/max(min(u,100),.001))+0.000001)"
    )
    serial = value(
        "Latest Birth ID",
        None,
        -2400,
        400,
        expression,
        dict(TIME_PROPS, e="emission_seconds", u="lifetime", r="rate"),
    )
    index = node(tree, "GeometryNodeInputIndex", "Pool Slot", -2600, 1000)
    cycle = calc("Births Since Slot", "SUBTRACT", serial, index.outputs[0], -2200, 600)
    cycle = calc("Slot Cycle", "DIVIDE", cycle, count, -2000, 600)
    cycle = calc("Completed Slot Cycles", "FLOOR", cycle, 0, -1800, 600)
    identity = calc("Cycle Birth Offset", "MULTIPLY", cycle, count, -2200, 1000)
    identity = calc("Particle Birth ID", "ADD", identity, index.outputs[0], -2000, 1000)
    birth = calc("Birth Time", "DIVIDE", identity, working, -1800, 1000)
    age = calc("Particle Age", "SUBTRACT", clock, birth, -2200, 200)
    # Clamp tiny negative ages when a boundary was rounded up by the birth tolerance.
    age = calc("Nonnegative Age", "MAXIMUM", age, 0, -2000, 200)
    own_progress = calc("Individual Progress", "DIVIDE", age, life, -1800, 200)
    own_progress = calc("Bounded Individual Progress", "MINIMUM", own_progress, 1, -1600, 200)
    born = calc("Has Been Born", "GREATER_THAN", identity, -0.5, -2600, -100)
    emitting = calc("Born Before Stop", "LESS_THAN", birth, emission, -2400, -100)
    living = calc("Within Individual Lifetime", "LESS_THAN", age, life, -2200, -100)
    enabled = calc("Rate Enabled", "GREATER_THAN", effective, 0, -2000, -100)
    alive = calc("Born in Emission Window", "MULTIPLY", born, emitting, -2400, -400)
    alive = calc("Still Living", "MULTIPLY", alive, living, -2200, -400)
    alive = calc("Emitter Enabled", "MULTIPLY", alive, enabled, -2000, -400)
    return line, identity, age, own_progress, alive
