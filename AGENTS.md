# Development rules

Build editable VFX for Blender 5.2 LTS using Blender's own objects, nodes and animation. Prioritize Eevee and artistic quality. Useful geometry, particles and shaders may cost performance; provide quality choices and measured costs instead of enforcing a low-cost ceiling.

- Read DESIGN.md before changing how modules interact or how data is saved. Read CONTEXT.md before changing timing, instance IDs or resource deletion.
- After necessary character-shot validation, expand the complete editable library toward 8–10 effects with distinct shapes and animation uses. Prioritize lightning, dust/smoke, stylized fire, character dash echoes and magic circles; avoid repeated local polish of the same three assets. Judge each asset in actual character shots and HD light/dark Eevee renders, recording viewed animation samples and viewing limits. Tests complement artistic review. Distinguish third-party references, tutorial claims and this project's actual renders; adapt principles rather than copy assets.
- Improve silhouette, color hierarchy and timing with editable native controls. Choose complexity for visible artistic value; do not force every effect to be cheap or sacrifice quality to fixed vertex budgets. Measure scene evaluation and matched renders with/without VFX on available hardware, recording device and settings. Geometry and particle counts guide complexity; they do not prove performance or viewport FPS.
- The project has not entered formal distribution. Maintain only current implementations; remove obsolete builders, preset migrations and compatibility-only tests when simplifying affected code. Preserve user-authored scene data and native editability.
- Continue high-value unblocked work after each Issue. Ask only for missing permissions, irreversible risks or a key requirement that cannot be resolved reasonably.
- Finish a usable effect before adding more abstractions. Keep object and node creation in core/builders, and interface code in UI modules. Use native nodes and drivers for playback; avoid Python frame handlers.
- Preserve user models, animation and edited nodes. Delete only resources owned by the selected effect and unused outside it. Refuse operations when copied instance IDs make ownership unclear.
- Verify changed behavior in Blender background mode. For timing or saved-data changes, save a .blend file and reopen it in a new process without the extension. State which visual and interface checks were actually performed.
- Use feature branches and pull requests. Commit and push completed work, and update ROADMAP.md and relevant Issues to match tested behavior.
- Use RTK for commands it supports. Matt Pocock skills are optional; `caveman` is the only permitted Caveman skill.
- Put temporary scripts, test scenes and renders in ignored work/. Build installation ZIPs in ignored dist/ and publish them as release assets. Commit the scripts that generate Blender assets so a fresh clone can rebuild them.

## Human-readable communication and documentation

- Write for humans. Use natural, concrete language; explain what the feature does, why it matters and how the reader uses it. Preserve accuracy, limitations and important design decisions.
- README and user guides address Blender users, including artists with no programming or repository knowledge. Developer documents may assume basic programming, but must explain this project's architecture and unfamiliar terms on first use.
- Lead user documentation with purpose, available features/project status and a working first-use path. Organize longer guides by the user's task: installation, creation, editing, saving and troubleshooting.
- Use Markdown as the normal reading structure: descriptive headings for sections, **numbered lists for ordered actions**, bullets for parallel choices, and concise tables for parameters, feature comparisons or version differences. A short document need not use every form.
- Bold important actions, UI labels and decisions; use code formatting for commands, paths and identifiers, and italics for brief secondary notes when useful. Give formatting a clear reading purpose.
- Keep paragraphs short and focused on one idea. Split long passages that mix instructions, parameters, limitations and history into appropriate sections, steps or tables. Concision must preserve an easy-to-scan page, not compress it into dense prose.
- Describe current behavior in user documentation; omit historical before/after explanations and effect revision numbers. Keep implementation internals, commit hashes, CI details and lengthy validation history in linked developer or review records. User pages retain the practical consequence and relevant limitation, with a link for detail.
- Include concrete examples and actual screenshots or renders when they clarify the workflow or result. State relevant viewing limits; an image or passing test alone does not prove artistic quality.
- Follow the existing document language unless asked otherwise. Write Chinese naturally rather than translating English technical prose literally; retain established technical terms where needed.
- Apply these rules to README files, guides, design documents, Issues, PRs and human-facing reports, scaling structure to their length and purpose.
- Before finishing, review from a newcomer's perspective: can the intended reader quickly find the next action and its limitations? For README and user guides, check installation, first use, editing and saving are easy to locate, UI labels and links are correct, and technical history does not bury the workflow. Rewrite unclear sections before submitting.
