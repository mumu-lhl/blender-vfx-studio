"""Native compositor wiring, pixel output and lifecycle safety."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import core, presets, screen

WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


def user_tree(source="CompositorNodeRGB"):
    tree = bpy.data.node_groups.new("User Compositor", "CompositorNodeTree")
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    output = tree.nodes.new("NodeGroupOutput")
    original = tree.nodes.new(source)
    if source == "CompositorNodeRGB":
        original.outputs[0].default_value = (0, 0, 0, 1)
    tree.links.new(original.outputs[0], output.inputs["Image"])
    bpy.context.scene.compositing_node_group = tree
    return tree, original, output


def render_setup():
    scene = bpy.context.scene
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(camera)
    camera.location = (0, 0, 5)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4
    scene.camera = camera
    scene.world = bpy.data.worlds.new("Black")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
    scene.render.compositor_device = "CPU"
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 32
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(WORK / "screen-pixels.exr")


def pixels(frame):
    bpy.context.scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(bpy.context.scene.render.filepath, check_existing=False)
    result = list(image.pixels)
    bpy.data.images.remove(image)
    return result


def center(frame):
    result = pixels(frame)
    offset = (16 * 32 + 16) * 4
    return result[offset : offset + 3]


class ScreenTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.frame_set(1)

    def test_create_copy_remove_restores_empty_compositor(self):
        self.assertEqual(bpy.ops.vfx_studio.create_screen(), {"FINISHED"})
        root = bpy.context.object
        clone = core.duplicate(bpy.context, root)
        self.assertNotEqual(clone["vfx_id"], root["vfx_id"])
        self.assertEqual(len(bpy.context.scene.compositing_node_group.nodes), 4)
        core.delete(root)
        self.assertIsNotNone(bpy.context.scene.compositing_node_group)
        core.delete(clone)
        self.assertIsNone(bpy.context.scene.compositing_node_group)
        self.assertEqual(len(bpy.data.objects), 0)
        self.assertEqual(len(bpy.data.node_groups), 0)

    def test_preserve_existing_chain_flag_and_user_branches(self):
        tree, original, output = user_tree()
        bpy.context.scene.render.use_compositing = False
        root = core.create_screen(bpy.context)
        original.name = "Keep User Node"
        other = tree.nodes.new("CompositorNodeRGB")
        other.outputs[0].default_value = (0.2, 0.3, 0.4, 1)
        layer = screen._layer(root)[2]
        # A user may intentionally change the input after adding the effect.
        tree.links.new(other.outputs[0], layer.inputs["Image"])
        core.delete(root)
        self.assertEqual(bpy.context.scene.compositing_node_group, tree)
        self.assertEqual(output.inputs["Image"].links[0].from_node, other)
        self.assertIn(original.name, tree.nodes)
        self.assertFalse(bpy.context.scene.render.use_compositing)
        self.assertNotIn(screen.ORIGINAL_FLAG, tree)

    def test_shared_and_invalid_graphs_are_rejected_before_changes(self):
        tree, _, output = user_tree()
        second = bpy.data.scenes.new("Other Scene")
        second.compositing_node_group = tree
        with self.assertRaisesRegex(ValueError, "shared"):
            core.create_screen(bpy.context)
        self.assertEqual(len(bpy.data.objects), 0)
        second.compositing_node_group = None
        tree.links.remove(output.inputs["Image"].links[0])
        with self.assertRaisesRegex(ValueError, "Connect"):
            core.create_screen(bpy.context)
        self.assertEqual(len(bpy.data.objects), 0)

    def test_shared_group_and_missing_input_block_deletion(self):
        root = core.create_screen(bpy.context)
        _, tree, layer = screen._layer(root)
        external = tree.nodes.new("CompositorNodeGroup")
        external.node_tree = layer.node_tree
        with self.assertRaisesRegex(ValueError, "shared"):
            core.delete(root)
        tree.nodes.remove(external)
        incoming = layer.inputs["Image"].links[0]
        source = incoming.from_socket
        tree.links.remove(incoming)
        with self.assertRaisesRegex(ValueError, "reconnect"):
            core.delete(root)
        self.assertIn(root.name, bpy.data.objects)
        tree.links.new(source, layer.inputs["Image"])
        core.delete(root)

    def test_extra_user_output_connections_are_not_silently_removed(self):
        root = core.create_screen(bpy.context)
        _, tree, layer = screen._layer(root)
        layer.node_tree.interface.new_socket(
            name="User Mask", in_out="OUTPUT", socket_type="NodeSocketFloat"
        )
        consumer = tree.nodes.new("ShaderNodeMath")
        connection = tree.links.new(layer.outputs["User Mask"], consumer.inputs[0])
        with self.assertRaisesRegex(ValueError, "extra outputs"):
            core.delete(root)
        self.assertTrue(consumer.inputs[0].is_linked)
        tree.links.remove(connection)
        core.delete(root)
        self.assertIn(consumer.name, tree.nodes)

    def test_manual_cross_scene_layer_copies_are_ambiguous(self):
        root = core.create_screen(bpy.context)
        _, tree, _ = screen._layer(root)
        other = bpy.data.scenes.new("Manual Scene Copy")
        other.compositing_node_group = tree.copy()
        copied = next(
            n for n in other.compositing_node_group.nodes if n.get("vfx_id") == root["vfx_id"]
        )
        copied.node_tree = copied.node_tree.copy()
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            core.delete(root)
        self.assertIn(root.name, bpy.data.objects)
        self.assertIsNotNone(other.compositing_node_group)

    def test_generated_base_user_edits_are_retained(self):
        root = core.create_screen(bpy.context)
        _, tree, layer = screen._layer(root)
        render = tree.nodes["Scene Render"]
        # Different pass selection is a user edit, even if no extra nodes exist.
        tree.links.new(render.outputs["Alpha"], layer.inputs["Image"])
        core.delete(root)
        self.assertEqual(bpy.context.scene.compositing_node_group, tree)
        self.assertEqual(
            tree.nodes["Scene Output"].inputs["Image"].links[0].from_socket.name, "Alpha"
        )

    def test_copy_preserves_nodes_actions_and_remaps_native_drivers(self):
        root = core.create_screen(bpy.context)
        root["flash"] = 1.0
        root.keyframe_insert('["flash"]', frame=1)
        root["flash"] = 0.0
        root.keyframe_insert('["flash"]', frame=3)
        group = screen._layer(root)[2].node_tree
        group.nodes.new("ShaderNodeValue").label = "User Edit"
        clone = core.duplicate(bpy.context, root)
        copy = screen._layer(clone)[2].node_tree
        self.assertIsNot(copy, group)
        self.assertIsNot(root.animation_data.action, clone.animation_data.action)
        self.assertTrue(any(n.label == "User Edit" for n in copy.nodes))
        for curve in copy.animation_data.drivers:
            self.assertTrue(all(v.targets[0].id == clone for v in curve.driver.variables))
        core.delete(root)
        self.assertIsNotNone(screen._layer(clone)[2])
        document = core.preset_snapshot(clone)
        self.assertEqual(document["assets"], {})
        self.assertEqual(presets.loads(presets.dumps(document)), document)
        imported = core.create_from_preset(bpy.context, document)
        self.assertEqual(imported["vfx_module"], "screen.glare")

    def test_cpu_render_flash_lifetime_loop_and_parameter_changes(self):
        user_tree()
        render_setup()
        root = core.create_screen(bpy.context)
        update(root, strength=0.0, flash=1.0, duration=4.0, loop=False)
        for frame, value in [(3, 0.5), (1, 1), (5, 0), (0, 0), (2, 0.75)]:
            with self.subTest(frame=frame):
                self.assertTrue(all(abs(c - value) < 0.01 for c in center(frame)))
        update(root, loop=True, speed=2.0, color_0=0.0, color_1=0.5, color_2=1.0)
        color = center(3)
        self.assertTrue(all(abs(a - b) < 0.01 for a, b in zip(color, (0, 0.5, 1))))
        _, tree, layer = screen._layer(root)
        for curve in layer.node_tree.animation_data.drivers:
            self.assertTrue(curve.driver.is_valid)
            self.assertTrue(curve.driver.is_simple_expression)
        core.delete(root)
        self.assertTrue(all(abs(c) < 0.01 for c in center(1)))

    def test_cpu_glare_adds_light_outside_a_bright_source(self):
        user_tree("CompositorNodeRLayers")
        render_setup()
        bpy.ops.mesh.primitive_plane_add(size=0.5)
        material = bpy.data.materials.new("User Emission")
        material.use_nodes = True
        material.node_tree.nodes.clear()
        emission = material.node_tree.nodes.new("ShaderNodeEmission")
        emission.inputs["Strength"].default_value = 8
        out = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
        material.node_tree.links.new(emission.outputs[0], out.inputs["Surface"])
        bpy.context.object.data.materials.append(material)
        baseline = pixels(1)
        root = core.create_screen(bpy.context)
        update(root, strength=1.0, glow_size=0.5)
        glow = pixels(1)
        # Compare far-field energy, excluding the emitting mesh's center pixels.
        offsets = [
            (y * 32 + x) * 4
            for y in range(32)
            for x in range(32)
            if x < 12 or x > 19 or y < 12 or y > 19
        ]
        self.assertGreater(sum(glow[i] for i in offsets), sum(baseline[i] for i in offsets) + 0.01)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(ScreenTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Screen integration tests failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.frame_set(1)
user_tree()
render_setup()
root = core.create_screen(bpy.context)
root.name = "Persisted Screen"
update(root, duration=4.0, flash=1.0, strength=0.0)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "screen.blend"))
print("SCREEN_INTEGRATION_OK")
