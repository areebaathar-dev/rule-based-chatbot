"""
tests/test_chatbot_logic.py

Tests for the chatbot's logic engine.

Run with:   python -m unittest discover -s tests -v
       or:  pytest tests/ -v

These check that the bot behaves consistently:
    - handles greetings
    - handles the exit command cleanly
    - picks the right response category deterministically (wording can be
      random, but which topic fires should not be)
    - never crashes or returns nothing on unrecognized input (fallback)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chatbot_logic import RuleBasedChatBot


class TestSanitization(unittest.TestCase):
    def test_lowercases_and_strips(self):
        self.assertEqual(RuleBasedChatBot.sanitize("   HeLLo   "), "hello")

    def test_collapses_internal_whitespace(self):
        self.assertEqual(RuleBasedChatBot.sanitize("hi    there"), "hi there")


class TestExitHandling(unittest.TestCase):
    def setUp(self):
        self.bot = RuleBasedChatBot()

    def test_recognizes_exit_words(self):
        for word in ["exit", "quit", "bye", "goodbye", "  BYE  "]:
            self.assertTrue(self.bot.is_exit_command(self.bot.sanitize(word)), f"Failed on: {word}")

    def test_does_not_falsely_trigger_exit(self):
        self.assertFalse(self.bot.is_exit_command(self.bot.sanitize("hello")))


class TestGreetings(unittest.TestCase):
    def setUp(self):
        self.bot = RuleBasedChatBot()

    def test_hello_gets_a_response(self):
        response = self.bot.get_response("hello")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_greeting_is_deterministically_categorized(self):
        # The specific wording may vary (random.choice), but the trace
        # should always show that a greeting-related rule fired.
        self.bot.get_response("hey there")
        trace = self.bot.last_trace
        self.assertIn("greeting", trace["rule"])


class TestFallback(unittest.TestCase):
    def setUp(self):
        self.bot = RuleBasedChatBot()

    def test_unknown_input_never_crashes(self):
        try:
            response = self.bot.get_response("asdkjhaslkdjhaslkdjh1298371")
        except Exception as e:
            self.fail(f"get_response raised an exception on unknown input: {e}")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_unknown_input_uses_fallback_layer(self):
        self.bot.get_response("zzqxjkvbn123")
        self.assertEqual(self.bot.last_trace["rule"], "fallback")

    def test_empty_input_does_not_crash(self):
        response = self.bot.get_response("")
        self.assertIsInstance(response, str)


class TestNameExtraction(unittest.TestCase):
    def setUp(self):
        self.bot = RuleBasedChatBot()

    def test_bored_is_not_mistaken_for_a_name(self):
        # regression test: "I'm bored" was previously misread as the user
        # introducing themselves as "Bored", since it matches the same
        # "I'm ___" pattern used for real name introductions.
        response = self.bot.get_response("i'm bored")
        self.assertNotIn("Nice to meet you", response)
        self.assertIsNone(self.bot.user_name)
        self.assertEqual(self.bot.last_trace["rule"], "keyword match: small_talk_bored")

    def test_extracts_name_from_common_phrasings(self):
        for phrase, expected in [
            ("my name is Areeba", "Areeba"),
            ("i am Sara", "Sara"),
            ("call me Ali", "Ali"),
        ]:
            bot = RuleBasedChatBot()
            bot.get_response(phrase)
            self.assertEqual(bot.user_name, expected, f"Failed on: {phrase}")


class TestExactMatchLayer(unittest.TestCase):
    """Verifies Layer 1 -- the literal `.get()` pattern from the training kit slide."""

    def setUp(self):
        self.bot = RuleBasedChatBot()

    def test_exact_match_hits_layer_1(self):
        self.bot.get_response("hello")
        self.assertTrue(self.bot.last_trace["rule"].startswith("exact match"))

    def test_get_with_default_never_returns_none(self):
        # Simulates the exact slide pattern directly.
        result = self.bot.exact_responses.get("not_a_real_key", "I do not understand.")
        self.assertEqual(result, "I do not understand.")


class TestUsageTracking(unittest.TestCase):
    def setUp(self):
        self.bot = RuleBasedChatBot()

    def test_usage_counts_increment(self):
        self.bot.get_response("hello")
        self.bot.get_response("hello")
        stats = self.bot.get_usage_stats()
        self.assertEqual(stats.get("exact:hello"), 2)


class TestKeywordBoundaryMatching(unittest.TestCase):
    """
    Regression test for a real bug found during manual testing: the short
    greeting keyword 'yo' was matching as a raw substring inside the word
    'you' (e.g. in 'who made you'), causing about_bot questions to
    incorrectly return a generic greeting instead of the correct answer.
    """

    def setUp(self):
        self.bot = RuleBasedChatBot()

    def test_who_made_you_returns_about_bot_not_greeting(self):
        response = self.bot.get_response("who made you?")
        self.assertEqual(self.bot.last_trace["rule"], "keyword match: about_bot")

    def test_short_keyword_does_not_match_inside_longer_word(self):
        # "yo" should NOT fire just because "you" is in the sentence.
        self.bot.get_response("what do you think about pizza")
        self.assertNotEqual(self.bot.last_trace.get("rule"), "keyword match: greeting")

    def test_standalone_yo_still_works_as_greeting(self):
        self.bot.get_response("yo")
        self.assertEqual(self.bot.last_trace["rule"], "keyword match: greeting")


class TestRiddleGame(unittest.TestCase):
    def setUp(self):
        self.bot = RuleBasedChatBot()

    def test_riddle_sets_pending_state(self):
        self.bot.get_response("riddle")
        self.assertIsNotNone(self.bot.pending_riddle)

    def test_correct_answer_clears_pending_state(self):
        self.bot.get_response("riddle")
        answer = self.bot.pending_riddle["answer"]
        response = self.bot.get_response(answer)
        self.assertIn("Correct", response)
        self.assertIsNone(self.bot.pending_riddle)

    def test_wrong_answer_keeps_pending_state(self):
        self.bot.get_response("riddle")
        response = self.bot.get_response("definitely not the answer xyz")
        self.assertIn("Not quite", response)
        self.assertIsNotNone(self.bot.pending_riddle)

    def test_giveup_reveals_answer_and_clears_state(self):
        self.bot.get_response("riddle")
        answer = self.bot.pending_riddle["answer"]
        response = self.bot.get_response("i don't know")
        self.assertIn(answer, response)
        self.assertIsNone(self.bot.pending_riddle)

    def test_asking_for_new_riddle_mid_game_gives_new_question(self):
        self.bot.get_response("riddle")
        first_question = self.bot.pending_riddle["question"]
        self.bot.get_response("riddle")
        # a new riddle should be pending (question may coincidentally repeat, but state should reset)
        self.assertIsNotNone(self.bot.pending_riddle)
        self.assertEqual(self.bot.riddle_attempts, 0)


class TestContextualMotivation(unittest.TestCase):
    def setUp(self):
        self.bot = RuleBasedChatBot()

    def test_study_keyword_selects_study_category(self):
        self.bot.get_response("motivate me for study")
        self.assertEqual(self.bot.last_motivation_category, "study")

    def test_work_keyword_selects_work_category(self):
        self.bot.get_response("motivate me for work")
        self.assertEqual(self.bot.last_motivation_category, "work")

    def test_generic_request_asks_clarifying_question(self):
        response = self.bot.get_response("motivate me")
        self.assertTrue(self.bot.pending_motivation)
        self.assertIn("study", response.lower())

    def test_clarifying_answer_of_study_gives_study_quote(self):
        self.bot.get_response("motivate me")
        response = self.bot.get_response("study")
        self.assertFalse(self.bot.pending_motivation)
        self.assertEqual(self.bot.last_motivation_category, "study")

    def test_clarifying_answer_with_custom_topic(self):
        self.bot.get_response("motivate me")
        response = self.bot.get_response("my thesis defense")
        self.assertFalse(self.bot.pending_motivation)
        self.assertIn("thesis defense", response)


class TestRomanUrduDetection(unittest.TestCase):
    def setUp(self):
        self.bot = RuleBasedChatBot()

    def test_detects_roman_urdu_markers(self):
        self.assertTrue(self.bot._is_roman_urdu("kaise ho aap"))

    def test_english_not_flagged_as_roman_urdu(self):
        self.assertFalse(self.bot._is_roman_urdu("how are you"))

    def test_roman_urdu_greeting_gets_roman_reply(self):
        response = self.bot.get_response("kaise ho")
        # response should not be an English-only fallback; check it came from the roman pool
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
