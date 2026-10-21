"""Blender VFX Studio: native assets, optional authoring UI."""


def register():
    from . import ui

    ui.register()


def unregister():
    from . import ui

    ui.unregister()
