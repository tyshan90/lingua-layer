#!/usr/bin/env python3
"""Persistent, dependency-free learner state for the LinguaLayer skill."""

from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any


STATE_VERSION = 1
ACTIVE_WORD_LIMIT = 5
LEARNED_EXPOSURE = 11
MAX_STATE_BYTES = 1_000_000
MAX_LANGUAGE_LENGTH = 80
MAX_WORD_LENGTH = 200
MAX_CONSUME_COUNT = 100
MAX_EXPOSURES = 1_000_000


class StateError(ValueError):
    """Raised when learner state or an input value is invalid."""


def default_state_path() -> Path:
    configured = os.environ.get("LINGUA_LAYER_STATE")
    if configured:
        return Path(configured).expanduser()
    codex_home = os.environ.get("CODEX_HOME")
    root = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return root / "lingua-layer" / "state.json"


def clean_text(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise StateError(f"{field} must be text")
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized:
        raise StateError(f"{field} cannot be empty")
    if len(normalized) > maximum:
        raise StateError(f"{field} cannot exceed {maximum} characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise StateError(f"{field} cannot contain control characters")
    if any(unicodedata.category(character) == "Cs" for character in normalized):
        raise StateError(f"{field} contains invalid Unicode characters")
    return normalized


def show_translation(exposure: int) -> bool:
    if exposure <= 5:
        return True
    if exposure <= 10:
        return exposure % 2 == 0
    return False


def empty_state() -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "initialized": False,
        "enabled": False,
        "active_language": None,
        "languages": {},
    }


class Store:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path is not None else default_state_path()

    def setup(
        self,
        language: str,
        *,
        translation_language: str = "English",
        level: str = "beginner",
        transliteration: str = "auto",
    ) -> dict[str, Any]:
        state = self._load()
        language = clean_text(language, "language", MAX_LANGUAGE_LENGTH)
        key = self._language_key(state, language) or language
        if key not in state["languages"]:
            state["languages"][key] = self._new_profile(
                translation_language, level, transliteration
            )
        state["initialized"] = True
        state["enabled"] = True
        state["active_language"] = key
        self._save(state)
        return self.view()

    def switch_language(
        self,
        language: str,
        *,
        translation_language: str | None = None,
        level: str | None = None,
        transliteration: str | None = None,
    ) -> dict[str, Any]:
        state = self._load()
        was_initialized = state["initialized"]
        language = clean_text(language, "language", MAX_LANGUAGE_LENGTH)
        key = self._language_key(state, language) or language
        if key not in state["languages"]:
            state["languages"][key] = self._new_profile(
                translation_language or "English",
                level or "beginner",
                transliteration or "auto",
            )
        state["initialized"] = True
        if not was_initialized:
            state["enabled"] = True
        state["active_language"] = key
        self._save(state)
        return self.view()

    def configure(
        self,
        *,
        translation_language: str | None = None,
        level: str | None = None,
        transliteration: str | None = None,
    ) -> dict[str, Any]:
        state = self._load_initialized()
        profile = self._active_profile(state)
        if translation_language is not None:
            profile["translation_language"] = clean_text(
                translation_language, "translation language", MAX_LANGUAGE_LENGTH
            )
        if level is not None:
            profile["level"] = clean_text(level, "level", MAX_LANGUAGE_LENGTH)
        if transliteration is not None:
            profile["transliteration"] = clean_text(
                transliteration, "transliteration", MAX_LANGUAGE_LENGTH
            )
        if translation_language is None and level is None and transliteration is None:
            raise StateError("provide at least one setting to configure")
        self._save(state)
        return self.view()

    def add_word(
        self,
        term: str,
        translation: str,
        *,
        transliteration: str | None = None,
    ) -> dict[str, Any]:
        state = self._load_initialized()
        profile = self._active_profile(state)
        term = clean_text(term, "term", MAX_WORD_LENGTH)
        translation = clean_text(translation, "translation", MAX_WORD_LENGTH)
        if transliteration is not None:
            transliteration = clean_text(
                transliteration, "transliteration", MAX_WORD_LENGTH
            )
        existing = profile["active_words"] + profile["learned_words"]
        if any(word["term"].casefold() == term.casefold() for word in existing):
            raise StateError(f"word already exists: {term}")
        if len(profile["active_words"]) >= ACTIVE_WORD_LIMIT:
            raise StateError("the profile already has five active words")
        profile["active_words"].append(
            {
                "term": term,
                "translation": translation,
                "transliteration": transliteration,
                "exposures": 0,
            }
        )
        self._save(state)
        return self.view()

    def consume(self, term: str, *, count: int = 1) -> list[dict[str, Any]]:
        state = self._load_initialized()
        profile = self._active_profile(state)
        term = clean_text(term, "term", MAX_WORD_LENGTH)
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= MAX_CONSUME_COUNT:
            raise StateError(f"count must be between 1 and {MAX_CONSUME_COUNT}")
        word, collection = self._find_word(profile, term)
        if word["exposures"] > MAX_EXPOSURES - count:
            raise StateError(f"exposure limit is {MAX_EXPOSURES}")
        presentations: list[dict[str, Any]] = []
        for _ in range(count):
            word["exposures"] += 1
            exposure = word["exposures"]
            presentations.append(
                {
                    "term": word["term"],
                    "translation": word["translation"],
                    "transliteration": word["transliteration"],
                    "exposure": exposure,
                    "show_translation": show_translation(exposure),
                }
            )
            if collection == "active_words" and exposure == LEARNED_EXPOSURE:
                profile["active_words"].remove(word)
                profile["learned_words"].append(word)
                collection = "learned_words"
        self._save(state)
        return presentations

    def pause(self) -> dict[str, Any]:
        state = self._load_initialized()
        state["enabled"] = False
        self._save(state)
        return self.view()

    def resume(self) -> dict[str, Any]:
        state = self._load_initialized()
        state["enabled"] = True
        self._save(state)
        return self.view()

    def view(self) -> dict[str, Any]:
        state = deepcopy(self._load())
        for profile in state["languages"].values():
            profile["needs_words"] = ACTIVE_WORD_LIMIT - len(profile["active_words"])
            for word in profile["active_words"]:
                next_exposure = word["exposures"] + 1
                word["next_exposure"] = next_exposure
                word["show_translation_next"] = show_translation(next_exposure)
        return state

    def _new_profile(
        self, translation_language: str, level: str, transliteration: str
    ) -> dict[str, Any]:
        return {
            "translation_language": clean_text(
                translation_language, "translation language", MAX_LANGUAGE_LENGTH
            ),
            "level": clean_text(level, "level", MAX_LANGUAGE_LENGTH),
            "transliteration": clean_text(
                transliteration, "transliteration", MAX_LANGUAGE_LENGTH
            ),
            "active_words": [],
            "learned_words": [],
        }

    def _load_initialized(self) -> dict[str, Any]:
        state = self._load()
        if not state["initialized"] or not state["active_language"]:
            raise StateError("LinguaLayer has not been set up")
        return state

    def _active_profile(self, state: dict[str, Any]) -> dict[str, Any]:
        language = state["active_language"]
        try:
            return state["languages"][language]
        except (KeyError, TypeError) as error:
            raise StateError("active language profile is missing") from error

    @staticmethod
    def _language_key(state: dict[str, Any], language: str) -> str | None:
        return next(
            (
                key
                for key in state["languages"]
                if key.casefold() == language.casefold()
            ),
            None,
        )

    @staticmethod
    def _find_word(
        profile: dict[str, Any], term: str
    ) -> tuple[dict[str, Any], str]:
        for collection in ("active_words", "learned_words"):
            for word in profile[collection]:
                if word["term"].casefold() == term.casefold():
                    return word, collection
        raise StateError(f"word not found: {term}")

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return empty_state()
        try:
            size = self.path.stat().st_size
        except OSError as error:
            raise StateError(f"cannot inspect state file: {error}") from error
        if size > MAX_STATE_BYTES:
            raise StateError("state file exceeds the 1 MB limit")
        try:
            raw = self.path.read_text(encoding="utf-8")
            state = json.loads(raw)
        except UnicodeDecodeError as error:
            raise StateError("state file is not valid UTF-8") from error
        except json.JSONDecodeError as error:
            raise StateError("state file is not valid JSON") from error
        except OSError as error:
            raise StateError(f"cannot read state file: {error}") from error
        self._validate_shape(state)
        return state

    @staticmethod
    def _validate_shape(state: Any) -> None:
        if not isinstance(state, dict):
            raise StateError("state root must be an object")
        if state.get("version") != STATE_VERSION:
            raise StateError("unsupported state version")
        required = {
            "initialized": bool,
            "enabled": bool,
            "languages": dict,
        }
        for field, expected_type in required.items():
            if not isinstance(state.get(field), expected_type):
                raise StateError(f"invalid state field: {field}")
        active_language = state.get("active_language")
        if active_language is not None and not isinstance(active_language, str):
            raise StateError("invalid state field: active_language")
        languages = state["languages"]
        if len(languages) > 1_000:
            raise StateError("state contains too many language profiles")
        for language, profile in languages.items():
            try:
                clean_text(language, "language", MAX_LANGUAGE_LENGTH)
                Store._validate_profile(profile)
            except (KeyError, TypeError, StateError) as error:
                raise StateError(f"invalid language profile: {language}") from error
        if state["initialized"]:
            if active_language not in languages:
                raise StateError("active language profile is missing")
        elif active_language is not None or languages:
            raise StateError("uninitialized state cannot contain language profiles")

    @staticmethod
    def _validate_profile(profile: Any) -> None:
        if not isinstance(profile, dict):
            raise StateError("profile must be an object")
        for field in ("translation_language", "level", "transliteration"):
            clean_text(profile[field], field.replace("_", " "), MAX_LANGUAGE_LENGTH)
        active_words = profile["active_words"]
        learned_words = profile["learned_words"]
        if not isinstance(active_words, list) or not isinstance(learned_words, list):
            raise StateError("word collections must be lists")
        if len(active_words) > ACTIVE_WORD_LIMIT:
            raise StateError("too many active words")
        seen: set[str] = set()
        for collection_name, words in (
            ("active_words", active_words),
            ("learned_words", learned_words),
        ):
            for word in words:
                if not isinstance(word, dict):
                    raise StateError("word must be an object")
                term = clean_text(word["term"], "term", MAX_WORD_LENGTH)
                clean_text(word["translation"], "translation", MAX_WORD_LENGTH)
                transliteration = word["transliteration"]
                if transliteration is not None:
                    clean_text(transliteration, "transliteration", MAX_WORD_LENGTH)
                exposures = word["exposures"]
                if (
                    not isinstance(exposures, int)
                    or isinstance(exposures, bool)
                    or exposures < 0
                    or exposures > MAX_EXPOSURES
                ):
                    raise StateError("invalid exposure count")
                if collection_name == "active_words" and exposures >= LEARNED_EXPOSURE:
                    raise StateError("active word has learned exposure count")
                if collection_name == "learned_words" and exposures < LEARNED_EXPOSURE:
                    raise StateError("learned word has insufficient exposures")
                folded = term.casefold()
                if folded in seen:
                    raise StateError("duplicate word")
                seen.add(folded)

    def _save(self, state: dict[str, Any]) -> None:
        self._validate_shape(state)
        try:
            payload = json.dumps(
                state, ensure_ascii=False, indent=2, sort_keys=True
            ).encode("utf-8") + b"\n"
        except UnicodeError as error:
            raise StateError("state contains invalid Unicode characters") from error
        if len(payload) > MAX_STATE_BYTES:
            raise StateError("state file would exceed the 1 MB limit")
        temporary: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(
                f".{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
            )
            with temporary.open("xb") as handle:
                handle.write(payload)
                handle.flush()
            try:
                os.chmod(temporary, 0o600)
            except OSError:
                pass
            os.replace(temporary, self.path)
        except OSError as error:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
            raise StateError(f"cannot write state file: {error}") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, help="override the learner state path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="show learner state")

    setup = subparsers.add_parser("setup", help="create or resume a language profile")
    setup.add_argument("--language", required=True)
    setup.add_argument("--translation-language", default="English")
    setup.add_argument("--level", default="beginner")
    setup.add_argument("--transliteration", default="auto")

    switch = subparsers.add_parser("switch", help="switch or create a language profile")
    switch.add_argument("--language", required=True)
    switch.add_argument("--translation-language")
    switch.add_argument("--level")
    switch.add_argument("--transliteration")

    configure = subparsers.add_parser("configure", help="change the active profile")
    configure.add_argument("--translation-language")
    configure.add_argument("--level")
    configure.add_argument("--transliteration")

    add_word = subparsers.add_parser("add-word", help="add an active vocabulary word")
    add_word.add_argument("--term", required=True)
    add_word.add_argument("--translation", required=True)
    add_word.add_argument("--transliteration")

    consume = subparsers.add_parser("consume", help="record and format word exposures")
    consume.add_argument("--term", required=True)
    consume.add_argument("--count", type=int, default=1)

    subparsers.add_parser("pause", help="pause the overlay")
    subparsers.add_parser("resume", help="resume the overlay")
    return parser


def run_cli(arguments: list[str] | None = None) -> int:
    args = build_parser().parse_args(arguments)
    store = Store(args.state)
    try:
        if args.command == "status":
            result = store.view()
        elif args.command == "setup":
            result = store.setup(
                args.language,
                translation_language=args.translation_language,
                level=args.level,
                transliteration=args.transliteration,
            )
        elif args.command == "switch":
            result = store.switch_language(
                args.language,
                translation_language=args.translation_language,
                level=args.level,
                transliteration=args.transliteration,
            )
        elif args.command == "configure":
            result = store.configure(
                translation_language=args.translation_language,
                level=args.level,
                transliteration=args.transliteration,
            )
        elif args.command == "add-word":
            result = store.add_word(
                args.term,
                args.translation,
                transliteration=args.transliteration,
            )
        elif args.command == "consume":
            result = store.consume(args.term, count=args.count)
        elif args.command == "pause":
            result = store.pause()
        else:
            result = store.resume()
    except StateError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
