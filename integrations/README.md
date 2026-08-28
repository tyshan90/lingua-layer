# Claude and Gemini integrations

The provider-neutral behavior lives in [`docs/LINGUA_LAYER_PROMPT.md`](../docs/LINGUA_LAYER_PROMPT.md). Use that file as the single prompt source; the host wrappers in this directory only explain where to install it and how to connect state.

## Claude.ai

1. Create a Claude Project.
2. Open **Set project instructions**.
3. Paste the contents of `docs/LINGUA_LAYER_PROMPT.md` into the instructions field.
4. Add `docs/LINGUA_LAYER_PROMPT.md` to the project's knowledge if you want it available as a reference file.

Anthropic documents that project instructions apply to chats in that project and that files can be uploaded to project knowledge: <https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects>.

Claude.ai cannot run this repository's local Python state helper. The prompt therefore falls back to best-effort behavior unless you provide a hosted state service.

## Claude Code

1. Copy `integrations/claude/CLAUDE.md` to the root of the clone as `CLAUDE.md`.
2. Keep `docs/LINGUA_LAYER_PROMPT.md` at the path imported by that file.
3. Start Claude Code from the clone root.

Claude Code loads `CLAUDE.md` at the start of each session and supports `@path/to/file` imports: <https://code.claude.com/docs/en/memory>.

The bundled adapter can be called from the clone root with the commands documented in `skills/lingua-layer/scripts/lingua_state.py`. Set `LINGUA_LAYER_STATE` when you want a different state location.

## Gemini Apps

1. Open Gemini and create a custom Gem.
2. Paste the contents of `docs/LINGUA_LAYER_PROMPT.md` into the Gem's instructions.
3. Add `docs/LINGUA_LAYER_PROMPT.md` under **Knowledge**.

Google documents custom Gem instructions and knowledge-file uploads here: <https://support.google.com/gemini/answer/15235603?hl=en-GB>.

Gemini Apps cannot run this repository's local Python helper, so cross-chat exposure counts require a hosted state service.

## Gemini API and AI Studio

Pass the contents of `docs/LINGUA_LAYER_PROMPT.md` as `system_instruction`. Gemini's API supports this configuration: <https://ai.google.dev/gemini-api/docs/text-generation>.

For persistent state, declare functions for `status`, `setup`, `switch`, `configure`, `add-word`, `consume`, `pause`, and `resume`. Execute those functions in your application and return their results to Gemini; function calling is client-executed: <https://ai.google.dev/gemini-api/docs/function-calling>.

## State and privacy

The bundled Python helper stores one local JSON profile. For web or multi-device use, put the same operations behind an authenticated service and namespace state per user. Do not share one user's vocabulary or exposure counts with another user.
