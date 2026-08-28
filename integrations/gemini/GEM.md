# LinguaLayer for Gemini

For Gemini Apps, copy the contents of `docs/LINGUA_LAYER_PROMPT.md` into a custom Gem's instructions and add that file as Gem knowledge.

For Gemini API or AI Studio, pass the same contents as `system_instruction`. If the application can execute custom functions, map the state adapter operations (`status`, `setup`, `switch`, `configure`, `add-word`, `consume`, `pause`, and `resume`) to functions backed by a per-user state store.

Prompt-only Gems cannot run the bundled Python helper or guarantee cross-chat exposure counts. Use an external state service when reliable persistence is required.
