# LinguaLayer for Claude Code

Import the provider-neutral behavior prompt:

@docs/LINGUA_LAYER_PROMPT.md

When working from this repository, use the bundled state adapter at:

`skills/lingua-layer/scripts/lingua_state.py`

Resolve that path from the repository root rather than assuming the current shell directory. Claude Code can load this file through `CLAUDE.md`; the portable prompt remains the source of truth for behavior.

For Claude.ai, copy the contents of `docs/LINGUA_LAYER_PROMPT.md` into a Project's instructions instead of using this file.
