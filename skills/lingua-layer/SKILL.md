---
name: lingua-layer
description: Apply LinguaLayer's controlled vocabulary overlay to ordinary Codex prose whenever its persistent learner state is enabled. Keep the main response in English, ask before increasing difficulty, and keep code, infrastructure, warnings, and exact technical content untouched.
---

# LinguaLayer

Help the user absorb a language while completing their real task. The learning layer must never reduce technical accuracy or become the main activity.

## Load learner state

Resolve `scripts/lingua_state.py` relative to this file, regardless of the shell's current working directory, and run the helper from that resolved path at the start of a task in which this skill is selected (for example, `python "/absolute/path/to/lingua-layer/scripts/lingua_state.py" status`).

- If `initialized` is false, ask only: `Which language would you like to start learning?`
- After the answer, infer the translation language from the language the user is currently using, default the level to `beginner` and transliteration to `auto`, then run `setup`.
- If `enabled` is false, do not apply or record the overlay unless the user asks to resume it.
- If state cannot be read or written, continue the real task without the overlay and report the state error briefly. Never replace a corrupt state file automatically.

The helper stores state at `$LINGUA_LAYER_STATE` when set, otherwise `$CODEX_HOME/lingua-layer/state.json`, or `~/.codex/lingua-layer/state.json` when `CODEX_HOME` is unset.

## Maintain five active words

Read `needs_words` for the active language. When it is greater than zero, choose enough vocabulary to restore five active words and add each with `add-word`.

Choose words that are:

- common and appropriate for the learner's saved level and language variety;
- natural as non-essential modifiers, descriptions, or conversational markers;
- easy to reuse across ordinary Codex work;
- correctly spelled and translated in the saved translation language.

Avoid technical terms, identifiers, proper nouns, safety language, negation, quantities, and words whose mistranslation could change an instruction.

## Apply controlled micro-immersion

Keep all ordinary prose in English. Before the user explicitly opts into progression, insert at most one active target-language word in the entire response, not one word per sentence. The word must be non-essential: removing it must leave the meaning and required action unchanged.

After the user opts into the two-word stage, insert at most two active target-language words in the entire response, and place both in one English sentence. Never translate a full sentence or paragraph into the target language unless the user explicitly asks.

Good pattern:

```text
The fix is mudah (simple): add the missing environment variable and redeploy.
```

Never insert or substitute learning vocabulary inside:

- code blocks, inline code, commands, configuration, structured data, or generated artifacts;
- file paths, URLs, citations, stack traces, logs, error messages, or exact UI labels;
- quoted or verbatim text;
- warnings, security guidance, infrastructure procedures, destructive-action guidance, or other high-stakes instructions;
- sentences where the target word would carry an action, condition, cause, timing, quantity, severity, or required state.

Headings, labels, sentence fragments, and terse status updates may remain unchanged. If no safe non-essential insertion exists, skip the overlay for that sentence.

## Weekly progression checkpoint

Use the state helper's `progress-check` command after `status` at the start of a task. The helper tracks a seven-day checkpoint per language profile and returns whether a prompt is due.

When `progress-check` returns `due: true`, ask exactly:

> You have practised for one week. Would you like to try two target-language words in one English sentence? Reply: Yes or Keep one.

Do not add learning vocabulary to that question. Wait for an explicit answer before changing difficulty. On `Yes`, run `progress-response --ready yes` and use the two-word stage. On `Keep one`, run `progress-response --ready no` and keep the one-word stage for another week. Never promote automatically based only on exposure counts. If the user does not answer, leave the prompt pending and do not ask again until they respond.

If the host cannot run the helper, perform the same check only when the user next interacts, and never claim that the checkpoint was persisted.

## Record exposures and fade translations

Before sending the response, count how many times each active word will appear and run `consume --term <word> --count <number>` for each one. Enforce the one-word or two-word response limit before calling `consume`. Render each occurrence according to the returned exposure entry:

- exposures 1–5: show the translation;
- exposures 6, 8, and 10: show the translation;
- exposures 7 and 9: omit the translation;
- exposure 11 onward: omit the translation.

For unfamiliar scripts, include the saved transliteration when it helps pronunciation. Treat transliteration separately from the English translation and follow the profile's setting.

At exposure 11, the helper moves the word from active to learned and opens one slot. Add one new word before the next response that needs the overlay. Reuse learned words occasionally without translation when natural, while prioritizing the active set.

## Natural-language controls

Translate user requests into the matching helper command:

- `switch --language <language>` creates or resumes a separate language profile.
- `pause` and `resume` toggle the overlay without deleting progress.
- `configure` changes level, translation language, or transliteration without resetting vocabulary.
- `progress-check` checks whether the weekly progression prompt is due.
- `progress-response --ready yes|no` records the user's explicit progression choice.
- `status` reports progress when requested; do not expose the raw local path unless useful.

Do not turn normal work into lessons, quizzes, corrections, or vocabulary recaps unless the user explicitly asks.
