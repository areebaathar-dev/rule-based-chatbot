"""
cli_chatbot.py

Terminal version of the chatbot. Keeps a loop going, cleans up whatever the
user types, checks it against the knowledge base, and exits cleanly when
told to.

Run with: python cli_chatbot.py
"""

from chatbot_logic import RuleBasedChatBot

BOT_NAME = "ChatBot"


def main():
    bot = RuleBasedChatBot(bot_name=BOT_NAME)

    print(bot.get_greeting_message())
    print("(Type 'exit', 'quit', or 'bye' to end the chat)\n")

    while True:
        raw_input_text = input("You: ")
        clean_input = bot.sanitize(raw_input_text)

        response = bot.get_response(raw_input_text)
        print(f"{BOT_NAME}: {response}")

        if bot.is_exit_command(clean_input):
            break


if __name__ == "__main__":
    main()
