# Development rules

Build editable VFX for Blender 5.2 LTS using Blender's own objects, nodes and animation. Prioritize Eevee and defaults that work on machines without a dedicated GPU.

- Read DESIGN.md before changing how modules interact or how data is saved. Read CONTEXT.md before changing timing, instance IDs or resource deletion.
- Judge charge → release → hit → dissipation in complete rigged-character shots, including occlusion, distant views and light/dark Eevee renders. Inspect actual images and animation samples before refining local nodes; fix the real builder when the complete picture reveals a defect. Record viewed frames and viewing limits; tests complement artistic review.
- Improve silhouette, color hierarchy and timing with editable native controls. Measure scene evaluation and matched renders with/without VFX on available hardware, recording device and settings. Geometry and particle counts guide complexity; they do not prove performance or viewport FPS.
- Continue high-value unblocked work after each Issue. Ask only for missing permissions, irreversible risks or a key requirement that cannot be resolved reasonably.
- Finish a usable effect before adding more abstractions. Keep object and node creation in core/builders, and interface code in UI modules. Use native nodes and drivers for playback; avoid Python frame handlers.
- Preserve user models, animation and edited nodes. Delete only resources owned by the selected effect and unused outside it. Refuse operations when copied instance IDs make ownership unclear.
- Verify changed behavior in Blender background mode. For timing or saved-data changes, save a .blend file and reopen it in a new process without the extension. State which visual and interface checks were actually performed.
- Use feature branches and pull requests. Commit and push completed work, and update ROADMAP.md and relevant Issues to match tested behavior.
- Use RTK for commands it supports. Matt Pocock skills are optional; `caveman` is the only permitted Caveman skill.
- Put temporary scripts, test scenes and renders in ignored work/. Build installation ZIPs in ignored dist/ and publish them as release assets. Commit the scripts that generate Blender assets so a fresh clone can rebuild them.

## Human-readable communication and documentation

- Write for humans, not for other AI agents. Prioritize clarity, accuracy, and readability over sounding technical or sophisticated.
- Use natural, straightforward language. Prefer concrete explanations over abstract descriptions, buzzwords, and unnecessary jargon.
- Explain what something does, why it exists, and how it works. Name the actual components, operations, and data involved.
- Assume readers understand basic programming but are unfamiliar with this project's architecture.
- Explain unfamiliar technical terms briefly on first use. Preserve established technical terms when they are necessary for accuracy.
- Use short, coherent paragraphs. Avoid excessive headings, nested lists, tables, repetition, and generic filler.
- Include concrete examples when they make complex behavior easier to understand.
- Keep technical details, limitations, and important design decisions intact. Never sacrifice correctness for simplicity.
- Follow the existing documentation language unless explicitly requested otherwise. For Chinese documentation, use natural Chinese rather than literal translations of English technical prose.
- Apply these rules to README files, guides, design documents, issue descriptions, PR descriptions, and human-facing progress reports.
- Before finishing documentation, review it from a newcomer's perspective and rewrite unclear or unnecessarily abstract passages.
