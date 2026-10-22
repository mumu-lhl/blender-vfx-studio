"""Parent existing effects and link their timing through native drivers."""

import math
import uuid

import bpy

from . import core
from .animation import curves
from .parameters import GROUP_PARAMETERS

TIME_KEYS = ("start", "duration", "speed", "loop")
# variable: (controller to read, property); G = group, L = layer controller.
TIMING = {
    "start": (
        "s+((floor(max((frame-s)*max(v,0.001)/max(d,1),0)) if l else 0)+max(o,0))*max(d,1)/max(v,0.001)",
        {
            "s": ("G", "start"),
            "l": ("G", "loop"),
            "o": ("L", "vfx_offset_ratio"),
            "d": ("G", "duration"),
            "v": ("G", "speed"),
        },
    ),
    "duration": ("max(d*r,1)", {"d": ("G", "duration"), "r": ("L", "vfx_duration_ratio")}),
    "speed": ("max(v*p,0.001)", {"v": ("G", "speed"), "p": ("L", "vfx_local_speed")}),
    "loop": ("False", {}),
}


def members(group):
    result = [o for o in bpy.data.objects if o.get("vfx_composition") == group]
    for obj in result:
        core.resolve(obj)
        if obj.parent != group or obj.get("vfx_role") != "controller":
            raise ValueError(
                "A composition member was manually reparented; detach it before deleting or copying the group"
            )
    return result


def _link(root, group, offset, ratio, speed):
    world = root.matrix_world.copy()
    root.parent = group
    root.matrix_world = world
    root["vfx_composition"] = group
    for name, value, minimum in (
        ("vfx_offset_ratio", offset, 0.0),
        ("vfx_duration_ratio", ratio, 0.00001),
        ("vfx_local_speed", speed, 0.001),
    ):
        root[name] = float(value)
        root.id_properties_ui(name).update(
            min=minimum, max=1000.0, soft_min=max(0, minimum), soft_max=2.0
        )
    for key, (expression, properties) in TIMING.items():
        driver = root.driver_add(f'["{key}"]').driver
        driver.type = "SCRIPTED"
        for name, (owner, prop) in properties.items():
            var = driver.variables.new()
            var.name, var.type = name, "SINGLE_PROP"
            var.targets[0].id = group if owner == "G" else root
            var.targets[0].data_path = f'["{prop}"]'
        driver.expression = expression


def create(context, objects):
    roots = list(dict.fromkeys(core.resolve(obj) for obj in objects))
    if None in roots or not 2 <= len(roots) <= 32:
        raise ValueError("Select 2–32 spatial VFX controllers or layers")
    for root in roots:
        if root["vfx_module"] in {"screen.glare", "core.composition"}:
            raise ValueError("Screen layers and nested compositions are not supported")
        if root.parent or root.constraints or root.get("vfx_composition"):
            raise ValueError("Detach existing parenting and constraints before composing")
        if root.library or root.override_library or root.name not in context.scene.objects:
            raise ValueError("Composition members must be local effects in this scene")
        if any(c.data_path in {f'["{key}"]' for key in TIME_KEYS} for c in curves(root)):
            raise ValueError("Existing timing animation must be removed or baked before composing")
    for root in roots:
        if (
            any(
                type(root[key]) not in (int, float) or not math.isfinite(root[key])
                for key in ("start", "duration", "speed")
            )
            or root["duration"] < 1
            or root["speed"] < 0.001
        ):
            raise ValueError("Repair invalid member timing before composing")
    context.view_layer.update()
    start = min(float(r["start"]) for r in roots)
    duration = (
        max(float(r["start"]) + float(r["duration"]) / max(float(r["speed"]), 0.001) for r in roots)
        - start
    )
    duration = max(duration, 1.0)
    group, _ = core._controller(
        context,
        "VFX Composition",
        "core.composition",
        "LOW",
        GROUP_PARAMETERS,
        {"duration": duration},
    )
    group.location = (0, 0, 0)
    group["start"] = start
    for root in roots:
        _link(
            root,
            group,
            (float(root["start"]) - start) / duration,
            float(root["duration"]) / duration,
            float(root["speed"]),
        )
    core.select(context, group)
    return group


def check_detach(root):
    root = core.resolve(root)
    group = root.get("vfx_composition") if root else None
    if group is None or core.resolve(group) is None or group["vfx_module"] != "core.composition":
        raise ValueError("Select a composition member")
    if root.constraints:
        raise ValueError("Remove member constraints before detaching with world preservation")
    from .binding import _has_transform_animation

    if _has_transform_animation(root):
        raise ValueError("Bake member transform animation before detaching or copying it alone")
    # Only remove the four drivers we installed. User replacements must be preserved.
    drivers = root.animation_data.drivers if root.animation_data else ()
    for key, (expression, properties) in TIMING.items():
        curve = next((c for c in drivers if c.data_path == f'["{key}"]'), None)
        if (
            curve is None
            or curve.driver.expression != expression
            or len(curve.driver.variables) != len(properties)
        ):
            raise ValueError(
                "Composition timing drivers were edited; restore them before detaching"
            )
        for var in curve.driver.variables:
            if var.name not in properties or var.type != "SINGLE_PROP":
                raise ValueError("Composition timing drivers were edited")
            owner, prop = properties[var.name]
            if (
                var.targets[0].id != (group if owner == "G" else root)
                or var.targets[0].data_path != f'["{prop}"]'
            ):
                raise ValueError("Composition timing drivers were edited")
    return root


def detach(context, root):
    root = check_detach(root)
    context.view_layer.update()
    world = root.evaluated_get(context.evaluated_depsgraph_get()).matrix_world.copy()
    values = {key: root[key] for key in TIME_KEYS}
    for key in TIME_KEYS:
        root.driver_remove(f'["{key}"]')
        root[key] = values[key]
    root.parent = None
    root.matrix_world = world
    del root["vfx_composition"]
    core.select(context, root)
    return root


def duplicate(context, group):
    sources = members(group)
    uid = str(uuid.uuid4())
    collection = bpy.data.collections.new("VFX • Composition Copy")
    core._tag(collection, uid)
    context.scene.collection.children.link(collection)
    clone = group.copy()
    collection.objects.link(clone)
    core._tag(clone, uid)
    core._remap_drivers(clone, {group: clone})
    for source in sources:
        child = core.duplicate(context, source, _standalone=False, _references={group: clone})
        child.parent = clone
        child["vfx_composition"] = clone
    core.select(context, clone)
    return clone


def remove(group):
    children = members(group)
    # Check all effects before deleting any: a shared asset must not cause partial deletion.
    for root in children:
        core._delete_spatial(root, validate_only=True)
    core._delete_spatial(group, validate_only=True)
    for root in children:
        core.delete(root)
    core._delete_spatial(group)
