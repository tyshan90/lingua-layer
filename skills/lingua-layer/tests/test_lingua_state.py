import json
import sys
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lingua_state import StateError, Store  # noqa: E402


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.state_path = ROOT / "tests" / f".state-{uuid.uuid4().hex}.json"
        self.addCleanup(self.state_path.unlink, missing_ok=True)
        self.store = Store(self.state_path)

    def test_first_setup_creates_a_beginner_profile(self):
        state = self.store.setup("Malay", translation_language="English")

        self.assertTrue(state["enabled"])
        self.assertEqual("Malay", state["active_language"])
        self.assertEqual("beginner", state["languages"]["Malay"]["level"])
        self.assertEqual("English", state["languages"]["Malay"]["translation_language"])
        self.assertEqual([], state["languages"]["Malay"]["active_words"])
        self.assertTrue(self.state_path.exists())

    def test_switching_languages_preserves_independent_progress(self):
        self.store.setup("Malay", translation_language="English")
        self.store.add_word("mudah", "simple")
        self.store.consume("mudah", count=3)

        self.store.switch_language("Japanese", translation_language="English")
        self.store.add_word("簡単", "simple", transliteration="kantan")
        self.store.consume("簡単", count=1)
        state = self.store.switch_language("Malay")

        malay = state["languages"]["Malay"]
        japanese = state["languages"]["Japanese"]
        self.assertEqual(3, malay["active_words"][0]["exposures"])
        self.assertEqual(1, japanese["active_words"][0]["exposures"])
        self.assertEqual("Malay", state["active_language"])

    def test_translation_fades_and_word_is_learned_after_eleven_exposures(self):
        self.store.setup("Malay", translation_language="English")
        self.store.add_word("mudah", "simple")

        presentations = self.store.consume("mudah", count=11)

        self.assertEqual(
            [True, True, True, True, True, True, False, True, False, True, False],
            [item["show_translation"] for item in presentations],
        )
        profile = self.store.view()["languages"]["Malay"]
        self.assertEqual([], profile["active_words"])
        self.assertEqual(11, profile["learned_words"][0]["exposures"])
        self.assertEqual(5, profile["needs_words"])

    def test_active_learning_set_is_capped_at_five_words(self):
        self.store.setup("Malay", translation_language="English")
        for index in range(5):
            self.store.add_word(f"word-{index}", f"meaning-{index}")

        with self.assertRaisesRegex(StateError, "five active words"):
            self.store.add_word("word-5", "meaning-5")

    def test_duplicate_words_are_rejected_case_insensitively(self):
        self.store.setup("Spanish", translation_language="English")
        self.store.add_word("Fácil", "easy")

        with self.assertRaisesRegex(StateError, "already exists"):
            self.store.add_word("fácil", "simple")

    def test_control_characters_are_rejected_without_changing_state(self):
        self.store.setup("Malay", translation_language="English")
        before = self.state_path.read_text(encoding="utf-8")

        with self.assertRaisesRegex(StateError, "control characters"):
            self.store.add_word("bad\nword", "unsafe")

        self.assertEqual(before, self.state_path.read_text(encoding="utf-8"))

    def test_corrupt_state_is_not_silently_overwritten(self):
        corrupt = "{not valid json"
        self.state_path.write_text(corrupt, encoding="utf-8")

        with self.assertRaisesRegex(StateError, "not valid JSON"):
            self.store.setup("Malay", translation_language="English")

        self.assertEqual(corrupt, self.state_path.read_text(encoding="utf-8"))

    def test_malformed_profile_is_rejected_as_state_error(self):
        malformed = {
            "version": 1,
            "initialized": True,
            "enabled": True,
            "active_language": "Malay",
            "languages": {"Malay": {"active_words": "not a list"}},
        }
        self.state_path.write_text(json.dumps(malformed), encoding="utf-8")

        with self.assertRaisesRegex(StateError, "invalid language profile"):
            self.store.view()

    def test_unwritable_parent_reports_a_state_error(self):
        blocker = ROOT / "tests" / f".blocker-{uuid.uuid4().hex}"
        blocker.write_text("not a directory", encoding="utf-8")
        self.addCleanup(blocker.unlink, missing_ok=True)
        store = Store(blocker / "state.json")

        with self.assertRaisesRegex(StateError, "cannot write state file"):
            store.setup("Malay", translation_language="English")

    def test_pause_and_resume_persist(self):
        self.store.setup("Malay", translation_language="English")

        self.assertFalse(self.store.pause()["enabled"])
        self.assertTrue(self.store.resume()["enabled"])

    def test_switching_while_paused_does_not_resume_overlay(self):
        self.store.setup("Malay", translation_language="English")
        self.store.pause()

        state = self.store.switch_language("Japanese", translation_language="English")

        self.assertFalse(state["enabled"])

    def test_consume_rejects_exposure_overflow_without_changing_state(self):
        self.store.setup("Malay", translation_language="English")
        self.store.add_word("mudah", "simple")
        self.store.consume("mudah", count=11)

        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state["languages"]["Malay"]["learned_words"][0]["exposures"] = 1_000_000
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        before = self.state_path.read_text(encoding="utf-8")

        with self.assertRaisesRegex(StateError, "exposure limit"):
            self.store.consume("mudah")

        self.assertEqual(before, self.state_path.read_text(encoding="utf-8"))

    def test_invalid_utf8_state_is_reported_as_state_error(self):
        self.state_path.write_bytes(bytes([0xFF]))

        with self.assertRaisesRegex(StateError, "UTF-8"):
            self.store.view()

    def test_surrogate_input_is_reported_as_state_error_without_changing_state(self):
        self.store.setup("Malay", translation_language="English")
        before = self.state_path.read_text(encoding="utf-8")

        with self.assertRaisesRegex(StateError, "Unicode"):
            self.store.add_word("\ud800", "invalid")

        self.assertEqual(before, self.state_path.read_text(encoding="utf-8"))

    def test_profile_settings_can_be_changed_without_resetting_progress(self):
        self.store.setup("Japanese", translation_language="English")
        self.store.add_word("簡単", "simple", transliteration="kantan")
        self.store.consume("簡単", count=2)

        state = self.store.configure(
            level="intermediate",
            translation_language="Malay",
            transliteration="off",
        )

        profile = state["languages"]["Japanese"]
        self.assertEqual("intermediate", profile["level"])
        self.assertEqual("Malay", profile["translation_language"])
        self.assertEqual("off", profile["transliteration"])
        self.assertEqual(2, profile["active_words"][0]["exposures"])


if __name__ == "__main__":
    unittest.main()
