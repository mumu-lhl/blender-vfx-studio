"""Blender VFX Studio: native assets, optional authoring UI."""


def register():
    from . import asset_browser, library_ui, ui

    ui.register()
    library_ui.register()
    asset_browser.register()


def unregister():
    from . import asset_browser, library_ui, ui

    asset_browser.unregister()
    library_ui.unregister()
    ui.unregister()
