# 🤖 Rule-Based Chatbot

A rule-based chatbot built in Python — a terminal version and a desktop GUI, both sharing the same logic engine. Understands greetings, jokes, riddles (with a real answer-checking game), study/work motivation, simple math, and basic Roman Urdu/Hinglish phrasing.

![Python](https://img.shields.io/badge/Python-3670A0?style=flat&logo=python&logoColor=ffdd54)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- Keyword + typo-tolerant matching (so "helo" still works)
- Riddle mini-game — asks a question, checks your guess, only reveals the answer if you say you don't know
- Motivation quotes that adapt to context ("motivate me for study" vs "motivate me for work")
- Understands common Roman Urdu / Hinglish phrases and replies in kind
- Remembers your name mid-conversation
- Simple arithmetic ("what is 12 + 7")
- Desktop GUI with dark/light mode, quick-actions sidebar, session analytics, and chat export
- Data-driven — knowledge base lives in `intents.json`, not hardcoded, so adding a topic doesn't require touching code

---

## 🧠 How It Decides What to Say

For each message: clean up text → check for an exact match → check if a riddle answer is pending → check for a "tell me another one" follow-up → check for a name introduction → check for math → scan for topic keywords → fall back to a default reply if nothing matched.

---

## 🛠️ Tech Stack

| Layer   | Technology |
|---------|------------|
| Language | Python     |
| GUI      | Tkinter    |
| Testing  | unittest   |

---

## 🚀 Getting Started

```bash
git clone https://github.com/areebaathar-dev/rule-based-chatbot.git
cd rule-based-chatbot
pip install -r requirements.txt

python gui_app.py        # GUI version
python cli_chatbot.py    # Terminal version
```

### Running the tests
```bash
python -m unittest discover -s tests -v
```

---

## 📁 Project Structure
rule-based-chatbot/
├── chatbot_logic.py # Core logic (used by both interfaces)
├── cli_chatbot.py # Terminal version
├── gui_app.py # Desktop GUI
├── intents.json # Knowledge base (keywords + responses)
├── benchmark.py # Dictionary lookup vs if-elif comparison
├── tests/
│ └── test_chatbot_logic.py # Unit tests
└── requirements.txt

---

## 🔭 Extending It

Add a new topic by editing `intents.json` — no code changes needed:
```json
"favorite_color": {
  "keywords": ["favorite color", "favourite colour"],
  "responses": { "en": ["I'd say blue, what's yours?"] }
}
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 👩‍💻 Author

**Areeba Athar**
BS Computer Science, NFC-IEFR Faisalabad
[LinkedIn](https://linkedin.com/in/areeba-athar) · [GitHub](https://github.com/areebaathar-dev)