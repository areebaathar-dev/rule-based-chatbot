# Chatbot

A rule-based chatbot built in Python — a terminal version and a desktop GUI,
both sharing the same logic engine. It understands greetings, jokes, riddles
(with a real answer-checking game), study/work motivation, simple math, and
basic Roman Urdu / Hinglish phrasing.

## Features

- Keyword + typo-tolerant matching (so "helo" still works)
- Riddle mini-game — asks a question, checks your guess, only reveals the
  answer if you say you don't know
- Motivation quotes that adapt to context ("motivate me for study" vs
  "motivate me for work")
- Understands common Roman Urdu / Hinglish phrases and replies in kind
- Remembers your name mid-conversation
- Simple arithmetic ("what is 12 + 7")
- Desktop GUI with dark/light mode, a quick-actions sidebar, session
  analytics, and chat export
- Data-driven — the knowledge base lives in `intents.json`, not hardcoded
  in the Python files, so adding a new topic doesn't require touching code

## Project structure

```
chatbot_logic.py     - the actual logic (used by both interfaces below)
cli_chatbot.py        - terminal version
gui_app.py              - desktop GUI
intents.json             - knowledge base (keywords + responses)
benchmark.py               - quick script comparing dictionary lookups vs if-elif chains
tests/
  test_chatbot_logic.py    - unit tests
requirements.txt
```

## Running it

```bash
pip install -r requirements.txt

python gui_app.py        # GUI
python cli_chatbot.py     # terminal
```

## Running the tests

```bash
python -m unittest discover -s tests -v
```

## How it decides what to say

For each message: clean up the text → check for an exact match → check if
a riddle answer is pending → check for a "tell me another one" follow-up →
check for a name introduction → check for math → scan for keywords tied to
a topic → fall back to a default reply if nothing matched.

## Extending it

Add a new topic by editing `intents.json` — no code changes needed:

```json
"favorite_color": {
  "keywords": ["favorite color", "favourite colour"],
  "responses": { "en": ["I'd say blue, what's yours?"] }
}
```

## 📄 License

This project is licensed under the MIT License.

## Author

Areeba — BS Computer Science, NFC-IEFR Faisalabad
