"""Read drivers and layered Action/NLA curves without altering animation."""


def curves(data):
    animation = data.animation_data
    if animation is None:
        return
    yield from animation.drivers
    actions = {animation.action} if animation.action else set()
    pending = [strip for track in animation.nla_tracks for strip in track.strips]
    while pending:
        strip = pending.pop()
        if strip.action:
            actions.add(strip.action)
        pending.extend(getattr(strip, "strips", ()))
    for action in actions:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", ()):
                    yield from bag.fcurves
