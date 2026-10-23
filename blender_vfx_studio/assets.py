"""Complete, self-contained spatial effects stored as native collection assets."""

import os
import tempfile
import uuid
from pathlib import Path

import bpy

from . import core
from .registry import MODULES

PREFIX = "__VFX_STUDIO_ASSET__"
BUNDLE_VERSION = 1


def _dependencies(seeds):
    dependencies = {}
    for used, users in bpy.data.user_map().items():
        for user in users:
            dependencies.setdefault(user, set()).add(used)
    result = set(seeds)
    pending = list(result)
    while pending:
        for used in dependencies.get(pending.pop(), ()):
            if used not in result:
                result.add(used)
                pending.append(used)
    return result


def _roots(root):
    if root.get("vfx_module") == "core.composition":
        from . import composition

        members = composition.members(root)
        if not 2 <= len(members) <= 32:
            raise ValueError("A native composition asset requires 2–32 members")
        return [root, *members]
    return [root]


def _validate(root, objects, dependencies):
    roots = _roots(root)
    ids = [r.get("vfx_id") for r in roots]
    if any(not isinstance(uid, str) or not uid for uid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Native asset has missing or duplicate instance IDs")
    if root.parent or root.get("vfx_composition"):
        raise ValueError("Export the complete composition, or detach this effect first")
    for controller in roots:
        module = controller.get("vfx_module")
        if (
            controller.get("vfx_schema") != core.SCHEMA_VERSION
            or module not in MODULES
            or controller.get("vfx_asset_version") != MODULES[module].asset_version
        ):
            raise ValueError("Unsupported native effect schema or asset version")
        if module == "screen.glare":
            raise ValueError("Screen effects belong to a scene; use parameter presets")
    expected = set(roots)
    for controller in roots:
        expected.update(
            o
            for o in controller.children_recursive
            if o.get("vfx_id") == controller["vfx_id"] and o.get("vfx_role") == "layer"
        )
    if set(objects) != expected:
        raise ValueError("Native asset contains objects outside its VFX hierarchy")
    allowed = (
        bpy.types.Object,
        bpy.types.Collection,
        bpy.types.Mesh,
        bpy.types.Material,
        bpy.types.NodeTree,
        bpy.types.Key,
        bpy.types.Action,
        bpy.types.Image,
    )
    for data in dependencies:
        if data.get("vfx_id") is not None and data.get("vfx_id") not in ids:
            raise ValueError("Native asset references data owned by another effect")
        if data.library or data.override_library or not isinstance(data, allowed):
            raise ValueError("Native asset requires local mesh, node, animation and image data")
        if isinstance(data, bpy.types.Object) and data not in expected:
            raise ValueError(
                "Native asset references an external object; unbind or remove that reference"
            )
        if isinstance(data, bpy.types.Collection):
            if set(data.all_objects) - expected:
                raise ValueError("A referenced collection contains objects outside this effect")
        if isinstance(data, bpy.types.Image) and data.source == "SEQUENCE":
            raise ValueError(
                "Image sequences stay external; save a JSON preset and copy the sequence files"
            )
        if isinstance(data, bpy.types.Image) and not (
            data.source == "GENERATED" or (data.source == "FILE" and data.packed_file)
        ):
            raise ValueError("Pack still images into the .blend before exporting a native asset")
    return roots


def write(filepath, root):
    root = core.resolve(root)
    if root is None:
        raise ValueError("Select a spatial VFX controller or layer")
    destination = Path(filepath).expanduser().resolve()
    if destination.suffix.lower() != ".blend":
        raise ValueError("Native effect files must end in .blend")
    if bpy.data.filepath and destination == Path(bpy.data.filepath).resolve():
        raise ValueError("Choose an asset file different from the current project")
    roots = _roots(root)
    objects = set(roots)
    for controller in roots:
        objects.update(
            o
            for o in controller.children_recursive
            if o.get("vfx_id") == controller["vfx_id"] and o.get("vfx_role") == "layer"
        )
    # Sampling sources are authoring references, not required to play stored trails.
    sources = [(r, r.get("vfx_source")) for r in roots if r.get("vfx_module") == "trail.ribbon"]
    bundle, temporary = None, None
    try:
        for controller, _ in sources:
            controller["vfx_source"] = None
        _validate(root, objects, _dependencies(objects))
        bundle = bpy.data.collections.new(root.name.removesuffix(" • Controller"))
        bundle["vfx_id"] = root["vfx_id"]
        bundle["vfx_bundle_version"] = BUNDLE_VERSION
        bundle["vfx_bundle_root"] = root["vfx_id"]
        bundle.asset_mark()
        bundle.asset_data.tags.new("VFX Studio")
        bundle.asset_data.description = "Complete native VFX: " + root.name
        for obj in objects:
            bundle.objects.link(obj)
        with tempfile.NamedTemporaryFile(
            suffix=".blend", dir=destination.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
        bpy.data.libraries.write(str(temporary), {bundle}, path_remap="RELATIVE_ALL", compress=True)
        os.replace(temporary, destination)
    finally:
        if bundle is not None:
            bpy.data.collections.remove(bundle)
        for controller, source in sources:
            controller["vfx_source"] = source
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load(context, filepath, *, collection_name=None):
    active = context.view_layer.objects.active
    if active is not None and active.mode != "OBJECT":
        raise ValueError("Switch to Object Mode before loading a complete effect")
    path = Path(filepath).expanduser().resolve()
    if path.suffix.lower() != ".blend" or not path.is_file():
        raise ValueError("Choose an existing native effect .blend file")
    before = set(bpy.data.all_ids)
    try:
        with bpy.data.libraries.load(str(path), link=False, assets_only=True) as (
            available,
            requested,
        ):
            if collection_name is not None:
                if (
                    not isinstance(collection_name, str)
                    or collection_name not in available.collections
                ):
                    raise ValueError("The selected collection asset is not present in this file")
                names = [collection_name]
            else:
                names = list(available.collections)
                if len(names) != 1:
                    raise ValueError("This file must contain one exported VFX collection asset")
            requested.collections = names
        imported = set(bpy.data.all_ids) - before
        bundle = requested.collections[0]
        if bundle is None or "vfx_bundle_version" not in bundle:
            raise ValueError("This collection was not saved with Save Complete Effect")
        if bundle["vfx_bundle_version"] != BUNDLE_VERSION:
            raise ValueError("Unsupported native effect bundle version; update the extension")
        objects = set(bundle.all_objects)
        roots = [o for o in objects if o.get("vfx_role") == "controller"]
        candidates = [r for r in roots if r.get("vfx_id") == bundle.get("vfx_bundle_root")]
        if len(candidates) != 1:
            raise ValueError("Native asset has no unique main controller")
        root = candidates[0]
        # IDs may match an earlier import. Change only newly appended blocks.
        ids = [r.get("vfx_id") for r in roots]
        if any(not isinstance(uid, str) or not uid for uid in ids) or len(set(ids)) != len(ids):
            raise ValueError("Native asset has missing or duplicate instance IDs")
        replacements = {uid: str(uuid.uuid4()) for uid in ids}
        for data in imported:
            uid = data.get("vfx_id")
            if uid in replacements:
                data["vfx_id"] = replacements[uid]
            elif uid is not None:
                raise ValueError("Native asset contains data owned by another effect")
        bundle["vfx_bundle_root"] = root["vfx_id"]
        dependencies = _dependencies({bundle})
        _validate(root, objects, dependencies)
        if {o for o in imported if isinstance(o, bpy.types.Object)} != objects:
            raise ValueError("Native asset imported objects outside its collection")
        if any(o not in imported for o in objects):
            raise ValueError("Native asset unexpectedly reuses existing objects")
        context.scene.collection.children.link(bundle)
        context.view_layer.update()
        for obj in objects:
            if obj.get("vfx_sim_part") == "source":
                obj.hide_set(True)
        core.select(context, root)
        return root
    except Exception:
        # Remove only data created by this append; never purge pre-existing orphans.
        created = set(bpy.data.all_ids) - before
        if created:
            bpy.data.batch_remove(ids=created)
        raise
