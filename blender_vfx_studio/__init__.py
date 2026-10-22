"""Blender VFX Studio: native assets, optional authoring UI."""


def register():
    from . import library_ui, ui

    ui.register()
    library_ui.register()


def unregister():
    from . import library_ui, ui

    library_ui.unregister()
    ui.unregister()
