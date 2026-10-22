"""Opt-in native attachment; target animation remains untouched."""

from . import core


def managed(root):
    name = root.get("vfx_binding_constraint")
    if not name:
        return None
    constraint = root.constraints.get(name)
    if constraint is None or constraint.type != "CHILD_OF":
        raise ValueError("Managed binding was renamed or replaced; restore it before unbinding")
    return constraint


def validate(context, root):
    root = core.resolve(root)
    if root is None or root.name not in context.scene.objects:
        raise ValueError("Select a VFX in this scene")
    if root["vfx_module"] == "screen.glare":
        raise ValueError("Screen effects cannot be spatially bound")
    if root.library or root.override_library:
        raise ValueError("Make the controller local before changing bindings")
    return root


def bind(context, root, target, bone=""):
    root = validate(context, root)
    if managed(root):
        raise ValueError("Unbind the existing managed binding before attaching again")
    if target is None or target.name not in context.scene.objects or core.resolve(target):
        raise ValueError("Choose a target object in this scene outside any VFX hierarchy")
    if bone and (target.type != "ARMATURE" or bone not in target.pose.bones):
        raise ValueError("Choose an existing pose bone on the target armature")
    # Follow ordinary parenting and constraint target dependencies to catch indirect cycles.
    pending, seen = [target], set()
    while pending:
        obj = pending.pop()
        if obj == root:
            raise ValueError("Binding would create a dependency cycle")
        if obj in seen:
            continue
        seen.add(obj)
        if obj.parent:
            pending.append(obj.parent)
        constraints = list(obj.constraints)
        if obj.type == "ARMATURE":
            constraints.extend(c for pose_bone in obj.pose.bones for c in pose_bone.constraints)
        pending.extend(c.target for c in constraints if getattr(c, "target", None))
        if obj.animation_data:
            pending.extend(
                t.id
                for f in obj.animation_data.drivers
                for v in f.driver.variables
                for t in v.targets
                if isinstance(t.id, type(root))
            )
    context.view_layer.update()
    evaluated = target.evaluated_get(context.evaluated_depsgraph_get())
    matrix = evaluated.matrix_world.copy()
    if bone:
        matrix @= evaluated.pose.bones[bone].matrix
    if abs(matrix.determinant()) < 1e-10:
        raise ValueError("Binding target has a singular transform; restore nonzero scale")
    # Native Child Of computes target * inverse * existing owner transform.
    constraint = root.constraints.new("CHILD_OF")
    constraint.name = "VFX • Binding"
    constraint.target = target
    constraint.subtarget = bone
    constraint.inverse_matrix = matrix.inverted()
    root["vfx_binding_constraint"] = constraint.name
    context.view_layer.update()
    return constraint


def _has_transform_animation(root):
    animation = root.animation_data
    if animation is None:
        return False
    curves = list(animation.drivers)
    actions = [animation.action] if animation.action else []
    for track in animation.nla_tracks:
        actions.extend(strip.action for strip in track.strips if strip.action)
    for action in actions:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", ()):
                    curves.extend(bag.fcurves)
    # Custom ID properties (time, color, shape) do not control the object transform.
    # Other paths may include transform or constraint animation; preserve them intact.
    return any(not curve.data_path.startswith('["') for curve in curves)


def unbind(context, root):
    root = validate(context, root)
    constraint = managed(root)
    if constraint is None:
        raise ValueError("This effect has no managed binding")
    # Other constraints may act after this binding. Re-solving their inverse is ambiguous.
    if len(root.constraints) != 1:
        raise ValueError(
            "Keep only the managed constraint before unbinding with world preservation"
        )
    if _has_transform_animation(root):
        raise ValueError(
            "Bake or remove controller transform/constraint animation before unbinding"
        )
    context.view_layer.update()
    world = root.evaluated_get(context.evaluated_depsgraph_get()).matrix_world.copy()
    root.constraints.remove(constraint)
    root.matrix_world = world
    del root["vfx_binding_constraint"]
    context.view_layer.update()
