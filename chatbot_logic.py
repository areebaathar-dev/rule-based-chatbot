"""
chatbot_logic.py

Core logic for the chatbot. Kept separate from the GUI/CLI files so both
can use the same code without duplicating it.

Basic flow for every message:
1. clean up the text (lowercase, strip spaces)
2. check for an exact match in a small dictionary
3. check if a riddle is waiting for an answer
4. check if the user is asking to repeat something ("another one")
5. check if they're introducing their name
6. check for simple math
7. scan for keywords tied to known topics (greeting, joke, riddle, etc.)
8. if nothing matched, fall back to a default reply

If the message looks like Roman Urdu / Hinglish (based on common words like
"hai", "kya", "kaise"), the bot tries to reply in the same style for
everyday conversation topics like greetings and thanks.
"""

import json
import random
import re
import difflib
from datetime import datetime
from pathlib import Path


# words that can follow "I'm ___" or "I am ___" but are NOT names -- without
# this list, something like "I'm bored" gets misread as someone introducing
# themselves as "Bored"
NOT_A_NAME = {
    "bored", "tired", "sad", "happy", "hungry", "sick", "fine", "okay", "ok",
    "ready", "busy", "free", "done", "back", "home", "sorry", "sure", "good",
    "great", "awesome", "excited", "nervous", "confused", "lost", "here",
    "leaving", "kidding", "joking", "serious", "curious", "worried", "stressed",
}


class RuleBasedChatBot:
    EXIT_COMMANDS = {"exit", "quit", "bye", "goodbye", "stop", "end chat", "close", "allah hafiz"}

    _DEFAULT_DATA = {
        "exact_responses": {"hello": "Hi there!", "hi": "Hey!"},
        "intents": {"greeting": {"keywords": ["hello", "hi", "hey"], "responses": {"en": ["Hello!"]}}},
        "fallback_responses": {"en": ["I don't understand that yet."]},
        "exit_responses": {"en": ["Goodbye!"]},
        "followup_words": ["another", "again", "more"],
        "riddles": [],
        "motivation": {"general": ["Keep going!"]},
        "giveup_words": ["i don't know", "idk"],
        "roman_urdu_markers": ["hai", "kya", "kaise"],
    }

    def __init__(self, bot_name: str = "ChatBot", data_path: str = None):
        self.bot_name = bot_name
        self.user_name = None
        self.message_count = 0
        self.last_trace = {}
        self.intent_usage = {}
        self.last_intent = None
        self.last_motivation_category = "general"
        self.last_custom_topic = None
        self.pending_motivation = False  # waiting for "study / work / something else"

        self.pending_riddle = None
        self.riddle_attempts = 0
        self._recent_picks = {}  # remembers the last item shown per category, to avoid back-to-back repeats

        data = self._load_data(data_path)
        self.exact_responses = data["exact_responses"]
        self.knowledge_base = data["intents"]
        self.fallback_responses = data["fallback_responses"]
        self.exit_responses = data["exit_responses"]
        self.followup_words = data.get("followup_words", ["another", "again", "more"])
        self.riddles = data.get("riddles", [])
        self.motivation = data.get("motivation", {"general": ["Keep going!"]})
        self.giveup_words = data.get("giveup_words", ["i don't know", "idk"])
        self.roman_urdu_markers = set(data.get("roman_urdu_markers", []))

        self._all_keywords = []
        for intent, payload in self.knowledge_base.items():
            for kw in payload["keywords"]:
                self._all_keywords.append((kw.strip(), intent))

    @staticmethod
    def _load_data(data_path: str = None) -> dict:
        path = Path(data_path) if data_path else Path(__file__).parent / "intents.json"
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {
                "exact_responses": raw.get("exact_responses", {}),
                "intents": raw.get("intents", {}),
                "fallback_responses": raw.get("fallback_responses", {"en": ["I don't understand."]}),
                "exit_responses": raw.get("exit_responses", {"en": ["Goodbye!"]}),
                "followup_words": raw.get("followup_words", ["another", "again", "more"]),
                "riddles": raw.get("riddles", []),
                "motivation": raw.get("motivation", {"general": ["Keep going!"]}),
                "giveup_words": raw.get("giveup_words", ["i don't know", "idk"]),
                "roman_urdu_markers": raw.get("roman_urdu_markers", []),
            }
        except (FileNotFoundError, json.JSONDecodeError):
            return RuleBasedChatBot._DEFAULT_DATA

    @staticmethod
    def sanitize(raw_input: str) -> str:
        cleaned = raw_input.lower().strip()
        return re.sub(r"\s+", " ", cleaned)

    def is_exit_command(self, clean_input: str) -> bool:
        return clean_input in self.EXIT_COMMANDS

    def is_followup(self, clean_input: str) -> bool:
        return any(word == clean_input or word in clean_input for word in self.followup_words)

    def is_giveup(self, clean_input: str) -> bool:
        return any(phrase in clean_input for phrase in self.giveup_words)

    def _is_roman_urdu(self, clean_input: str) -> bool:
        words = set(re.findall(r"[a-z']+", clean_input))
        return len(words & self.roman_urdu_markers) > 0

    def _pick_localized(self, response_map: dict, clean_input: str, bot_name_fmt=True, category_key=None):
        use_roman = self._is_roman_urdu(clean_input)
        pool = response_map.get("roman") if use_roman else response_map.get("en")
        if not pool:
            pool = response_map.get("en") or ["I'm not sure how to respond to that."]
        text = self._pick_varied(pool, category_key) if category_key else random.choice(pool)
        return text.format(bot_name=self.bot_name) if bot_name_fmt else text

    def _match_intent(self, clean_input: str):
        # picks the longest matching keyword so more specific phrases win
        # over shorter, more generic ones
        best_intent, best_len = None, 0
        for intent, data in self.knowledge_base.items():
            for keyword in data["keywords"]:
                pattern = r"\b" + re.escape(keyword.strip()) + r"\b"
                if re.search(pattern, clean_input) and len(keyword) > best_len:
                    best_intent, best_len = intent, len(keyword)
        return best_intent

    def _fuzzy_match_intent(self, clean_input: str, cutoff: float = 0.82):
        # catches typos like "helo" or "tiem" -- only checked when the
        # normal keyword scan above finds nothing
        words = clean_input.split()
        best_intent, best_score = None, 0.0
        for word in words:
            if len(word) < 4:
                continue
            for keyword, intent in self._all_keywords:
                if " " in keyword or len(keyword) < 4:
                    continue
                score = difflib.SequenceMatcher(None, word, keyword).ratio()
                if score >= cutoff and score > best_score:
                    best_intent, best_score = intent, score
        return best_intent

    def _extract_name(self, clean_input: str):
        patterns = [r"my name is (\w+)", r"i am (\w+)", r"i'm (\w+)", r"call me (\w+)", r"mera naam (\w+)"]
        for pattern in patterns:
            match = re.search(pattern, clean_input)
            if match:
                word = match.group(1)
                if word.lower() in NOT_A_NAME:
                    return None
                return word.capitalize()
        return None

    def _try_math(self, clean_input: str):
        normalized = (
            clean_input.replace("plus", "+")
            .replace("minus", "-")
            .replace("times", "*")
            .replace("multiplied by", "*")
            .replace("divided by", "/")
            .replace(" x ", " * ")
        )
        match = re.search(r"(-?\d+(?:\.\d+)?)\s*([\+\-\*/])\s*(-?\d+(?:\.\d+)?)", normalized)
        if not match:
            return None
        a, op, b = float(match.group(1)), match.group(2), float(match.group(3))
        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        elif op == "*":
            result = a * b
        elif op == "/":
            if b == 0:
                return "Can't divide by zero!"
            result = a / b
        else:
            return None
        result = int(result) if result == int(result) else round(result, 4)
        return f"That equals {result}."

    def _pick_varied(self, pool, category_key):
        """Random pick that avoids repeating the same item twice in a row
        for a given category (jokes, riddles, quotes...)."""
        if len(pool) <= 1:
            choice = pool[0] if pool else None
        else:
            last = self._recent_picks.get(category_key)
            options = [item for item in pool if item != last] or pool
            choice = random.choice(options)
        self._recent_picks[category_key] = choice
        return choice

    def _ask_new_riddle(self):
        if not self.riddles:
            return "I'm out of riddles for now!"
        riddle = self._pick_varied(self.riddles, "riddle")
        self.pending_riddle = {"question": riddle["question"], "answer": riddle["answer"].lower()}
        self.riddle_attempts = 0
        return f"🧩 Riddle time: {riddle['question']}"

    def _check_riddle_answer(self, clean_input: str):
        answer = self.pending_riddle["answer"]
        is_correct = (
            answer in clean_input
            or difflib.SequenceMatcher(None, clean_input, answer).ratio() >= 0.72
        )
        if is_correct:
            self.pending_riddle = None
            self.riddle_attempts = 0
            return f"✅ Correct! The answer was '{answer}'. Nicely done!"
        self.riddle_attempts += 1
        return "❌ Not quite — try again, or say 'I don't know' if you'd like the answer."

    def _categorize_motivation_topic(self, clean_input: str):
        """Returns 'study', 'work', or None if the topic is ambiguous/unspecified."""
        study_words = {"study", "studies", "studying", "exam", "exams", "test", "assignment", "parhai", "parhna", "parhne"}
        work_words = {"work", "job", "office", "career", "kaam", "internship", "shift", "deadline"}
        words = set(clean_input.split())
        if words & study_words:
            return "study"
        if words & work_words:
            return "work"
        return None

    GENERIC_TOPIC_PHRASES = {"something else", "kuch aur", "anything else", "other", "sonething else"}

    def _custom_motivation(self, clean_input: str):
        if clean_input in self.GENERIC_TOPIC_PHRASES:
            self.last_custom_topic = "whatever it is"
            return "Whatever it is, I believe you can push through it \u2014 one step at a time. 💪"
        topic = clean_input
        for filler in ("for ", "about ", "to ", "with "):
            if topic.startswith(filler):
                topic = topic[len(filler):]
        topic = " ".join(topic.split()[:6])  # keep it short and natural
        self.last_custom_topic = topic
        pool = self.motivation.get("custom", ["Keep going with {topic}!"])
        template = self._pick_varied(pool, "quote:custom")
        return template.format(topic=topic)

    def get_response(self, raw_input: str) -> str:
        self.message_count += 1
        clean_input = self.sanitize(raw_input)

        trace = {"raw_input": raw_input, "sanitized": clean_input, "rule": None}

        if not clean_input:
            trace["rule"] = "empty input"
            self.last_trace = trace
            return "You didn't say anything — I'm listening whenever you're ready!"

        if self.is_exit_command(clean_input):
            trace["rule"] = "exit command"
            self.last_trace = trace
            self._track_usage("exit")
            return self._pick_localized(self.exit_responses, clean_input, bot_name_fmt=False)

        exact_hit = self.exact_responses.get(clean_input)
        if exact_hit:
            trace["rule"] = f"exact match: '{clean_input}'"
            self.last_trace = trace
            self._track_usage(f"exact:{clean_input}")
            self.last_intent = "greeting"
            return exact_hit

        # riddle waiting for an answer?
        if self.pending_riddle:
            if self.is_giveup(clean_input):
                answer = self.pending_riddle["answer"]
                self.pending_riddle = None
                trace["rule"] = "riddle give-up"
                self.last_trace = trace
                self._track_usage("riddle_giveup")
                return f"No worries! The answer was '{answer}'. Want another riddle?"

            matched_intent = self._match_intent(clean_input)
            if matched_intent == "riddle" or self.is_followup(clean_input):
                trace["rule"] = "new riddle requested"
                self.last_trace = trace
                self._track_usage("riddle")
                self.last_intent = "riddle"
                return self._ask_new_riddle()

            if matched_intent is None:
                result = self._check_riddle_answer(clean_input)
                trace["rule"] = "riddle guess"
                self.last_trace = trace
                self._track_usage("riddle_guess")
                return result

            self.pending_riddle = None

        # motivation: waiting for "study / work / something else"?
        if self.pending_motivation:
            self.pending_motivation = False
            category = self._categorize_motivation_topic(clean_input)
            if category:
                text = self._pick_varied(self.motivation[category], f"quote:{category}")
                self.last_motivation_category = category
                trace["rule"] = f"motivation ({category}, from clarification)"
            else:
                text = self._custom_motivation(clean_input)
                self.last_motivation_category = "custom"
                trace["rule"] = "motivation (custom topic)"
            self.last_trace = trace
            self._track_usage(f"quote:{self.last_motivation_category}")
            self.last_intent = "quote"
            return text

        if self.is_followup(clean_input) and self.last_intent:
            if self.last_intent == "riddle":
                trace["rule"] = "follow-up -> new riddle"
                self.last_trace = trace
                self._track_usage("riddle")
                return self._ask_new_riddle()
            if self.last_intent == "quote":
                category = self.last_motivation_category
                if category == "custom" and self.last_custom_topic:
                    pool = self.motivation.get("custom", ["Keep going with {topic}!"])
                    template = self._pick_varied(pool, "quote:custom")
                    text = template.format(topic=self.last_custom_topic)
                else:
                    pool = self.motivation.get(category, ["Keep going!"])
                    text = self._pick_varied(pool, f"quote:{category}")
                trace["rule"] = f"follow-up -> more motivation ({category})"
                self.last_trace = trace
                self._track_usage(f"quote:{category}")
                return text
            kb_entry = self.knowledge_base.get(self.last_intent, {})
            responses = kb_entry.get("responses", {})
            pool = responses.get("en") if isinstance(responses, dict) else responses
            if pool:
                trace["rule"] = f"follow-up -> repeat '{self.last_intent}'"
                self.last_trace = trace
                self._track_usage(f"followup:{self.last_intent}")
                return random.choice(pool).format(bot_name=self.bot_name)

        name = self._extract_name(clean_input)
        if name:
            self.user_name = name
            trace["rule"] = "name introduction"
            self.last_trace = trace
            self._track_usage("name_intro")
            return f"Nice to meet you, {name}! I'll remember that. 😊"

        math_result = self._try_math(clean_input)
        if math_result:
            trace["rule"] = "math"
            self.last_trace = trace
            self._track_usage("math")
            return math_result

        intent = self._match_intent(clean_input)
        used_fuzzy = False
        if not intent:
            intent = self._fuzzy_match_intent(clean_input)
            used_fuzzy = intent is not None

        if intent == "riddle":
            trace["rule"] = "riddle"
            self.last_trace = trace
            self._track_usage("riddle")
            self.last_intent = "riddle"
            return self._ask_new_riddle()

        if intent == "quote":
            category = self._categorize_motivation_topic(clean_input)
            if category:
                text = self._pick_varied(self.motivation[category], f"quote:{category}")
                self.last_motivation_category = category
                trace["rule"] = f"motivation ({category})"
                self.last_trace = trace
                self._track_usage(f"quote:{category}")
                self.last_intent = "quote"
                return text
            # ambiguous -- ask what it's for instead of guessing
            self.pending_motivation = True
            trace["rule"] = "motivation clarification asked"
            self.last_trace = trace
            self._track_usage("quote:asked")
            return self._pick_localized(
                {"en": ["Sure! What's it for \u2014 study, work, or something else?"],
                 "roman": ["Zaroor! Kis cheez ke liye \u2014 study, work, ya kuch aur?"]},
                clean_input, bot_name_fmt=False,
            )

        if intent == "time_query":
            trace["rule"] = "time"
            self.last_trace = trace
            self._track_usage("time_query")
            self.last_intent = "time_query"
            return f"The current time is {datetime.now().strftime('%I:%M %p')}."

        if intent == "date_query":
            trace["rule"] = "date"
            self.last_trace = trace
            self._track_usage("date_query")
            self.last_intent = "date_query"
            return f"Today's date is {datetime.now().strftime('%A, %B %d, %Y')}."

        if intent:
            responses = self.knowledge_base[intent].get("responses", {})
            response = None
            if isinstance(responses, dict):
                response = self._pick_localized(responses, clean_input, category_key=intent)
            elif isinstance(responses, list) and responses:
                response = random.choice(responses).format(bot_name=self.bot_name)

            if response:
                if self.user_name and intent == "greeting":
                    response = f"{response} Good to chat with you again, {self.user_name}."
                trace["rule"] = f"{'typo match' if used_fuzzy else 'keyword match'}: {intent}"
                self.last_trace = trace
                self._track_usage(intent)
                self.last_intent = intent
                return response

        trace["rule"] = "fallback"
        self.last_trace = trace
        self._track_usage("fallback")
        return self._pick_localized(self.fallback_responses, clean_input, bot_name_fmt=False)

    def _track_usage(self, label: str):
        self.intent_usage[label] = self.intent_usage.get(label, 0) + 1

    def get_usage_stats(self) -> dict:
        return dict(sorted(self.intent_usage.items(), key=lambda kv: kv[1], reverse=True))

    def get_trace_text(self) -> str:
        if not self.last_trace:
            return ""
        return self.last_trace.get("rule", "—")

    def get_greeting_message(self) -> str:
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
        return f"{greeting}! I'm {self.bot_name}. Type 'help' anytime. 🤖"


if __name__ == "__main__":
    bot = RuleBasedChatBot()
    print(bot.get_greeting_message())
    for msg in ["i'm bored", "riddle", "idk", "motivate me for study", "bye"]:
        print(f"You: {msg}")
        print(f"Bot: {bot.get_response(msg)}")
