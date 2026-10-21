# Development rules

Build native, editable Blender VFX for Blender 5.2 LTS; prioritize Eevee and CPU-friendly defaults.

- Read DESIGN.md before changing module boundaries or persistence; read CONTEXT.md before changing time, identity or ownership behavior.
- Deliver usable vertical slices. Keep bpy operations in builders/core and UI orchestration in ui.py. Use native nodes/drivers instead of frame handlers.
- Preserve user data and manual node edits. Delete only owned, unshared resources; reject ambiguous instance identities.
- Test changed behavior with real Blender background mode. Save/reopen and extension-disabled playback are required for persistence/time changes. Record visual checks and limitations honestly.
- Use feature branches and PRs after bootstrap. Commit and push each completed stage; keep ROADMAP.md and meaningful GitHub Issues aligned with verified behavior.
- Use RTK for supported commands. Matt Pocock skills are optional aids; the only permitted Caveman skill is `caveman`.
- Keep temporary scripts, test blends and renders in ignored work/; distributable archives go in ignored dist/ and release assets. Generated assets belong in source builders.
