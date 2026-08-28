# LinguaLayer

**Learn a language while you work.**

LinguaLayer is a Codex skill that adds one non-essential target-language word to ordinary prose sentences while keeping code, commands, configuration, infrastructure guidance, warnings, and exact technical content unchanged.

It maintains five active words per language, repeats them in natural context, and gradually removes translations as they become familiar. Progress is stored locally and separately for every language.

## Example

Without LinguaLayer:

> The fix is simple: add the missing environment variable and redeploy.

With Malay active:

> The fix is mudah (simple): add the missing environment variable and redeploy.

The inserted word is non-essential. Removing it leaves the technical instruction intact.

## Learning progression

| Exposure | Presentation |
| ---: | --- |
| 1–5 | Target word with translation |
| 6 | Target word with translation |
| 7 | Target word only |
| 8 | Target word with translation |
| 9 | Target word only |
| 10 | Target word with translation |
| 11+ | Target word only |

Once a word reaches exposure 11, it moves to learned vocabulary and a new word enters the five-word active set.

## Install

### Ask Codex to install it

Give Codex this repository's GitHub URL and ask:

> Install the skill at `skills/lingua-layer` from this GitHub repository.

### Install manually

1. Download or clone this repository.
2. Copy `skills/lingua-layer` to `$CODEX_HOME/skills/lingua-layer`. If `CODEX_HOME` is unset, use `~/.codex/skills/lingua-layer`.
3. Start a new Codex task or restart Codex so the skill is discovered.

To verify the installation before starting a task, run `python <skill-directory>/scripts/lingua_state.py status` (replace `<skill-directory>` with the copied path). Then explicitly invoke it with `Use $lingua-layer.`

LinguaLayer requires Python 3.10 or newer and has no third-party dependencies.

## Use with Claude and Gemini

The core behavior is provider-neutral. Copy [`docs/LINGUA_LAYER_PROMPT.md`](docs/LINGUA_LAYER_PROMPT.md) into a host's instructions, then follow the host-specific steps in [`integrations/README.md`](integrations/README.md):

- Claude.ai: add the prompt to a Project's instructions and knowledge.
- Claude Code: copy [`integrations/claude/CLAUDE.md`](integrations/claude/CLAUDE.md) to the clone root as `CLAUDE.md`.
- Gemini Apps: add the prompt to a custom Gem's instructions and Knowledge.
- Gemini API or AI Studio: pass the prompt as `system_instruction` and connect the state operations through function calling.

The web products cannot run the bundled local Python helper. Use best-effort in-chat learning there, or provide an authenticated per-user state service for reliable cross-chat and multi-device exposure counts. See [`integrations/README.md`](integrations/README.md) for the documented provider setup and privacy boundary.

## First use

Invoke the skill once:

```text
Use $lingua-layer.
```

LinguaLayer asks one onboarding question:

> Which language would you like to start learning?

It defaults to beginner vocabulary and uses the user's conversational language for translations. Level, translation language, and transliteration can be changed later.

## Controls

Use natural requests such as:

```text
Switch LinguaLayer to Japanese.
Pause LinguaLayer.
Resume LinguaLayer.
Use intermediate vocabulary.
Translate the words into Malay.
Turn off transliteration.
Show my LinguaLayer progress.
```

Each language keeps an independent profile, so switching languages does not reset earlier progress.

## State and privacy

Learner state is stored in:

1. `$LINGUA_LAYER_STATE`, when explicitly set;
2. `$CODEX_HOME/lingua-layer/state.json`; or
3. `~/.codex/lingua-layer/state.json` when `CODEX_HOME` is unset.

The state contains language settings, vocabulary, translations, and exposure counts. LinguaLayer does not store prompts, source code, credentials, or conversation transcripts, and it makes no network requests.

Writes are size-limited and atomically replace the previous state. Invalid or corrupt state is reported rather than silently overwritten.

## Automatic invocation limitation

The skill requests implicit invocation after setup, but current official OpenAI documentation does not guarantee that a skill will run in every future task. For strict behavior, explicitly mention `$lingua-layer` in a task or add it to the applicable project instructions.

## Test

From the repository root:

```text
python -m unittest discover -s skills/lingua-layer/tests -v
```

## License

MIT
