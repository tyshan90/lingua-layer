import json
import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone
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

    def test_progress_check_waits_a_week_and_only_prompts_once(self):
        started = datetime(2026, 8, 31, 9, tzinfo=timezone.utc)
        self.store.setup("Malay", translation_language="English", now=started)

        before_due = self.store.progress_check(now=started + timedelta(days=6, hours=23))
        self.assertFalse(before_due["due"])
        self.assertFalse(before_due["progress_prompt_pending"])

        due = self.store.progress_check(now=started + timedelta(days=7))
        self.assertTrue(due["due"])
        self.assertTrue(due["progress_prompt_pending"])

        repeated = self.store.progress_check(now=started + timedelta(days=7, minutes=1))
        self.assertFalse(repeated["due"])
        self.assertTrue(repeated["progress_prompt_pending"])

    def test_progress_response_accepts_two_words_only_after_opt_in(self):
        started = datetime(2026, 8, 31, 9, tzinfo=timezone.utc)
        self.store.setup("Malay", translation_language="English", now=started)

        with self.assertRaisesRegex(StateError, "no progress prompt"):
            self.store.progress_response(True, now=started + timedelta(days=7))

        self.store.progress_check(now=started + timedelta(days=7))
        accepted = self.store.progress_response(
            True, now=started + timedelta(days=7, minutes=1)
        )

        self.assertEqual(2, accepted["words_per_sentence"])
        self.assertFalse(accepted["progress_prompt_pending"])
        self.assertIsNone(accepted["next_progress_check_at"])

    def test_declining_progression_reschedules_the_prompt(self):
        started = datetime(2026, 8, 31, 9, tzinfo=timezone.utc)
        self.store.setup("Malay", translation_language="English", now=started)
        self.store.progress_check(now=started + timedelta(days=7))

        declined = self.store.progress_response(
            False, now=started + timedelta(days=7, minutes=1)
        )
        self.assertEqual(1, declined["words_per_sentence"])
        self.assertFalse(declined["progress_prompt_pending"])
        self.assertEqual(
            "2026-09-14T09:01:00Z", declined["next_progress_check_at"]
        )

    def test_legacy_profile_gets_progress_defaults_when_checked(self):
        self.store.setup("Malay", translation_language="English")
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        profile = state["languages"]["Malay"]
        for field in (
            "started_at",
            "next_progress_check_at",
            "last_progress_prompt_at",
            "progress_prompt_pending",
            "words_per_sentence",
        ):
            profile.pop(field, None)
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        checked = self.store.progress_check(
            now=datetime(2026, 8, 31, 9, tzinfo=timezone.utc)
        )
        self.assertFalse(checked["due"])
        self.assertEqual(1, checked["words_per_sentence"])
        self.assertEqual(
            "2026-09-07T09:00:00Z", checked["next_progress_check_at"]
        )


if __name__ == "__main__":
    unittest.main()
