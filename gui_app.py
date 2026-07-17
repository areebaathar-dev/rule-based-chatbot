"""
gui_app.py

Desktop chat window for the chatbot, built with CustomTkinter.

Run with:  python gui_app.py
"""

import customtkinter as ctk
import tkinter as tk
from datetime import datetime
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from chatbot_logic import RuleBasedChatBot

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BOT_NAME = "ChatBot"

GRAD_TOP = (255, 107, 74)     # coral
GRAD_BOTTOM = (45, 212, 191)   # teal

THEMES = {
    "dark": {
        "bg_main": "#121212",
        "sidebar_bg": "#171717",
        "card_bg": "#1E1E22",
        "card_hover": "#28282E",
        "bot_bubble": "#1E1E24",
        "bot_text": "#ECECEC",
        "user_bubble": "#FF6B4A",
        "user_text": "#FFFFFF",
        "text_primary": "#E4E4E7",
        "text_muted": "#8C8C93",
        "entry_bg": "#1E1E22",
        "border": "#2A2A30",
    },
    "light": {
        "bg_main": "#F7F5F2",
        "sidebar_bg": "#FFFFFF",
        "card_bg": "#F1EFEC",
        "card_hover": "#E7E4DF",
        "bot_bubble": "#EFEDEA",
        "bot_text": "#242424",
        "user_bubble": "#FF6B4A",
        "user_text": "#FFFFFF",
        "text_primary": "#1A1A1A",
        "text_muted": "#75757C",
        "entry_bg": "#F1EFEC",
        "border": "#E2DFDA",
    },
}

ACCENT = "#FF6B4A"
ACCENT_2 = "#2DD4BF"
ONLINE_GREEN = "#4ADE80"


def draw_vertical_gradient(canvas, width, height, top_rgb, bottom_rgb):
    steps = max(height, 2)
    for i in range(0, steps, 3):  # every 3px is smooth enough and noticeably faster to draw
        ratio = i / steps
        r = int(top_rgb[0] + (bottom_rgb[0] - top_rgb[0]) * ratio)
        g = int(top_rgb[1] + (bottom_rgb[1] - top_rgb[1]) * ratio)
        b = int(top_rgb[2] + (bottom_rgb[2] - top_rgb[2]) * ratio)
        color = f"#{r:02x}{g:02x}{b:02x}"
        canvas.create_line(0, i, width, i + 3, fill=color, width=3, tags="gradient")


class GradientPanel(tk.Canvas):
    def __init__(self, master, top_rgb, bottom_rgb, **kwargs):
        super().__init__(master, highlightthickness=0, bd=0, **kwargs)
        self.top_rgb = top_rgb
        self.bottom_rgb = bottom_rgb
        self._last_size = None
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        size = (event.width, event.height)
        if size == self._last_size:
            return
        self._last_size = size
        # only clear the gradient lines themselves -- NOT the badge/name
        # labels placed on this same canvas via create_window, which
        # "delete('all')" was wiping out and leaving stray artifacts behind
        self.delete("gradient")
        draw_vertical_gradient(self, event.width, event.height, self.top_rgb, self.bottom_rgb)
        self.tag_lower("gradient")
        try:
            self.tag_raise("content")  # keep badge/text above the gradient lines
        except tk.TclError:
            pass  # content not drawn yet on the very first resize


class Avatar(ctk.CTkFrame):
    def __init__(self, master, glyph, color, size=34, font=None, **kwargs):
        super().__init__(master, width=size, height=size, corner_radius=size // 2,
                          fg_color=color, **kwargs)
        self.pack_propagate(False)
        ctk.CTkLabel(self, text=glyph, font=font or ctk.CTkFont(size=int(size * 0.45)), text_color="white").place(
            relx=0.5, rely=0.5, anchor="center"
        )


class ChatBubble(ctk.CTkFrame):
    """A message row with an avatar and a bubble."""

    def __init__(self, master, text, is_user, timestamp, colors, fonts, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", expand=True, padx=6)

        final_color = colors["user_bubble"] if is_user else colors["bot_bubble"]
        text_color = colors["user_text"] if is_user else colors["bot_text"]
        justify = "right" if is_user else "left"

        if is_user:
            ctk.CTkFrame(row, fg_color="transparent", width=30).pack(side="left", fill="x", expand=True)

        col = ctk.CTkFrame(row, fg_color="transparent")
        col.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")

        avatar = Avatar(col, "🙂" if is_user else BOT_NAME[0], ACCENT if is_user else ACCENT_2, size=32, font=fonts["avatar"])
        bubble = ctk.CTkFrame(col, fg_color=final_color, corner_radius=16,
                               border_width=1, border_color=colors["border"] if not is_user else final_color)

        if is_user:
            bubble.pack(side="left", padx=(0, 8))
            avatar.pack(side="left")
        else:
            avatar.pack(side="left", padx=(0, 8))
            bubble.pack(side="left")

        ctk.CTkLabel(
            bubble, text=text, text_color=text_color, wraplength=380,
            justify=justify, font=fonts["msg"],
        ).pack(padx=15, pady=11)

        meta = ctk.CTkLabel(col, text=timestamp, text_color=colors["text_muted"], font=fonts["meta"])
        meta.pack(anchor="e" if is_user else "w", padx=(0, 44) if is_user else (44, 0), pady=(2, 0))

        if not is_user:
            ctk.CTkFrame(row, fg_color="transparent", width=30).pack(side="right", fill="x", expand=True)


class TypingIndicator(ctk.CTkFrame):
    def __init__(self, master, colors, fonts, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=6)
        Avatar(row, BOT_NAME[0], ACCENT_2, size=32, font=fonts["avatar"]).pack(side="left", padx=(0, 8))
        bubble = ctk.CTkFrame(row, fg_color=colors["bot_bubble"], corner_radius=16,
                               border_width=1, border_color=colors["border"])
        bubble.pack(side="left")
        self.label = ctk.CTkLabel(
            bubble, text=f"{BOT_NAME} is typing", text_color=colors["text_muted"],
            font=fonts["typing"],
        )
        self.label.pack(padx=15, pady=11)
        self._dots = 0
        self._running = True
        self._animate()

    def _animate(self):
        if not self._running:
            return
        self._dots = (self._dots + 1) % 4
        self.label.configure(text=f"{BOT_NAME} is typing" + "." * self._dots)
        self.after(350, self._animate)

    def stop(self):
        self._running = False


class SidebarButton(ctk.CTkFrame):
    def __init__(self, master, icon, label, command, colors, **kwargs):
        super().__init__(master, fg_color=colors["card_bg"], corner_radius=12, height=44, **kwargs)
        self.pack_propagate(False)
        self.command = command
        self.colors = colors

        self.content = ctk.CTkLabel(
            self, text=f"{icon}   {label}", anchor="w", font=ctk.CTkFont(size=13),
            text_color=colors["text_primary"],
        )
        self.content.pack(fill="both", expand=True, padx=14)

        for widget in (self, self.content):
            widget.bind("<Button-1>", lambda e: self.command())
            widget.bind("<Enter>", lambda e: self.configure(fg_color=self.colors["card_hover"]))
            widget.bind("<Leave>", lambda e: self.configure(fg_color=self.colors["card_bg"]))

    def restyle(self, colors):
        self.colors = colors
        self.configure(fg_color=colors["card_bg"])
        self.content.configure(text_color=colors["text_primary"])


class ChatbotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.bot = RuleBasedChatBot(bot_name=BOT_NAME)
        self.theme_name = "dark"
        self.colors = THEMES[self.theme_name]
        self.chat_history = []

        self.title(f"{BOT_NAME}")
        self.geometry("1040x700")
        self.minsize(760, 540)
        self.configure(fg_color=self.colors["bg_main"])

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # fonts are created once and reused everywhere, instead of a fresh
        # CTkFont object per message -- noticeably cheaper as the chat grows
        self.fonts = {
            "msg": ctk.CTkFont(size=14),
            "meta": ctk.CTkFont(size=10),
            "avatar": ctk.CTkFont(size=15),
            "typing": ctk.CTkFont(size=13, slant="italic"),
        }

        self._sidebar_buttons = []

        self._build_sidebar()
        self._build_main_panel()

        self.after(200, self._show_welcome_message)

    # ------------------------------------------------------------------
    def _draw_header_content(self, canvas):
        """
        Draws the bot name and subtitle straight onto the gradient canvas
        using native text (not embedded CTk widgets, which don't blend
        properly against a raw canvas background).
        """
        cx = 125
        canvas.create_text(cx, 48, text=BOT_NAME, fill="#FFFFFF", font=("Segoe UI", 22, "bold"), tags="content")
        canvas.create_text(cx, 72, text="your chat assistant", fill="#FFF3EF", font=("Segoe UI", 12), tags="content")

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=self.colors["sidebar_bg"])
        self.sidebar.grid(row=0, column=0, sticky="nswe")
        self.sidebar.grid_propagate(False)

        gradient = GradientPanel(self.sidebar, GRAD_TOP, GRAD_BOTTOM, width=250, height=110)
        gradient.pack(fill="x", side="top")
        self._draw_header_content(gradient)

        self.status_label = ctk.CTkLabel(
            self.sidebar, text="●  Online", font=ctk.CTkFont(size=12, weight="bold"), text_color=ONLINE_GREEN
        )
        self.status_label.pack(pady=(14, 10))

        self.quick_actions_title = ctk.CTkLabel(
            self.sidebar, text="QUICK ACTIONS", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.colors["text_muted"], anchor="w",
        )
        self.quick_actions_title.pack(fill="x", padx=20, pady=(6, 6))

        actions_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        actions_scroll.pack(fill="both", expand=True, padx=8)

        actions = [
            ("👋", "Say hi", "hello"),
            ("🙂", "How are you?", "how are you"),
            ("🤖", "What's your name?", "what is your name"),
            ("ℹ️", "Who made you?", "who made you"),
            ("❓", "Help", "help"),
            ("😂", "Tell a joke", "tell me a joke"),
            ("🧩", "Riddle me", "riddle"),
            ("💡", "Motivate me", "motivate me"),
            ("🕐", "What time is it?", "what time is it"),
            ("📅", "What's the date?", "what is the date"),
            ("🧮", "Do some math", "what is 12 + 7"),
            ("☁️", "Weather", "weather"),
            ("😴", "I'm bored", "i'm bored"),
            ("🙏", "Say thanks", "thanks"),
        ]
        for icon, label, payload in actions:
            btn = SidebarButton(actions_scroll, icon, label, colors=self.colors,
                                 command=lambda p=payload: self._send_text(p))
            btn.pack(fill="x", pady=4)
            self._sidebar_buttons.append(btn)

        self.tools_title = ctk.CTkLabel(
            self.sidebar, text="TOOLS", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.colors["text_muted"], anchor="w",
        )
        self.tools_title.pack(fill="x", padx=20, pady=(12, 6))

        self.tool_buttons = []
        for label, cmd in [("📊 Analytics", self._open_analytics), ("⬇ Export Chat", self._export_chat), ("🗑 Clear Chat", self._clear_chat)]:
            row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            b = ctk.CTkButton(
                row, text=label, height=34, corner_radius=10,
                fg_color=self.colors["card_bg"], hover_color=self.colors["card_hover"],
                text_color=self.colors["text_primary"], command=cmd,
            )
            b.pack(fill="x")
            self.tool_buttons.append(b)

        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(fill="x", side="bottom", padx=16, pady=16)

        self.theme_btn = ctk.CTkButton(
            bottom, text="☀️ Light Mode", height=34, corner_radius=10,
            fg_color="transparent", border_width=1, border_color=self.colors["border"],
            text_color=self.colors["text_primary"],
            command=self._toggle_theme,
        )
        self.theme_btn.pack(fill="x")

    # ------------------------------------------------------------------
    def _build_main_panel(self):
        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=self.colors["bg_main"])
        self.main.grid(row=0, column=1, sticky="nswe")
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self.header = ctk.CTkFrame(self.main, height=58, corner_radius=0, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="we")
        self.header_title = ctk.CTkLabel(
            self.header, text="Conversation", font=ctk.CTkFont(size=15, weight="bold"), text_color=self.colors["text_primary"],
        )
        self.header_title.pack(side="left", padx=24, pady=16)
        self.msg_count_label = ctk.CTkLabel(
            self.header, text="0 messages", font=ctk.CTkFont(size=11), text_color=self.colors["text_muted"],
        )
        self.msg_count_label.pack(side="right", padx=24)

        self.chat_scroll = ctk.CTkScrollableFrame(self.main, fg_color="transparent", corner_radius=0)
        self.chat_scroll.grid(row=1, column=0, sticky="nswe")
        self._typing_indicator = None

        self._build_input_bar(self.main)

    def _build_input_bar(self, main):
        self.bar_wrap = ctk.CTkFrame(main, fg_color="transparent")
        self.bar_wrap.grid(row=2, column=0, sticky="we", padx=24, pady=(0, 20))

        self.bar = ctk.CTkFrame(self.bar_wrap, corner_radius=24, fg_color=self.colors["card_bg"],
                                 border_width=1, border_color=self.colors["border"])
        self.bar.pack(fill="x")

        self.entry = ctk.CTkEntry(
            self.bar, placeholder_text=f"Message {BOT_NAME}...", height=48, corner_radius=22,
            font=ctk.CTkFont(size=14), border_width=0, fg_color="transparent",
            text_color=self.colors["text_primary"],
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(16, 8), pady=6)
        self.entry.bind("<Return>", lambda e: self._on_send())

        self.send_btn = ctk.CTkButton(
            self.bar, text="➤", width=42, height=42, corner_radius=21,
            fg_color=ACCENT, hover_color="#E85A3A",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._on_send,
        )
        self.send_btn.pack(side="right", padx=8, pady=6)

    # ------------------------------------------------------------------
    def _show_welcome_message(self):
        self._add_bubble(self.bot.get_greeting_message(), is_user=False)

    def _send_text(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self._on_send()

    def _on_send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._add_bubble(text, is_user=True)

        self._typing_indicator = TypingIndicator(self.chat_scroll, self.colors, self.fonts)
        self._typing_indicator.pack(fill="x", pady=(6, 0))
        self._scroll_to_bottom()

        # response is instant (no real computation cost), so a short
        # scheduled callback feels snappy without needing a thread
        self.after(180, lambda: self._compute_response(text))

    def _compute_response(self, text):
        response = self.bot.get_response(text)
        self._deliver_response(text, response)

    def _deliver_response(self, original_text, response):
        if self._typing_indicator:
            self._typing_indicator.stop()
            self._typing_indicator.destroy()
            self._typing_indicator = None

        self._add_bubble(response, is_user=False)

        clean = self.bot.sanitize(original_text)
        if self.bot.is_exit_command(clean):
            self.status_label.configure(text="●  Session ended", text_color="#F87171")
            self.entry.configure(state="disabled")

    def _add_bubble(self, text, is_user, record=True):
        timestamp = datetime.now().strftime("%I:%M %p")
        bubble = ChatBubble(self.chat_scroll, text, is_user, timestamp, self.colors, self.fonts)
        bubble.pack(fill="x", pady=(3, 0))
        self._scroll_to_bottom()
        if record:
            sender = "You" if is_user else self.bot.bot_name
            self.chat_history.append((sender, text, timestamp))
            self.msg_count_label.configure(text=f"{len(self.chat_history)} messages")

    def _scroll_to_bottom(self):
        self.after(30, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))

    def _clear_chat(self):
        for widget in self.chat_scroll.winfo_children():
            widget.destroy()
        self.bot = RuleBasedChatBot(bot_name=BOT_NAME)
        self.chat_history = []
        self.entry.configure(state="normal")
        self.status_label.configure(text="●  Online", text_color=ONLINE_GREEN)
        self.msg_count_label.configure(text="0 messages")
        self._show_welcome_message()

    # ------------------------------------------------------------------
    # THEME SWITCHING -- every custom-colored surface is reconfigured here,
    # and the chat is re-rendered from history so old and new messages
    # both end up matching the chosen theme (not just newly sent ones).
    # ------------------------------------------------------------------
    def _toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.colors = THEMES[self.theme_name]
        ctk.set_appearance_mode(self.theme_name)
        self._apply_theme()

    def _apply_theme(self):
        c = self.colors
        self.configure(fg_color=c["bg_main"])
        self.sidebar.configure(fg_color=c["sidebar_bg"])
        self.main.configure(fg_color=c["bg_main"])
        self.quick_actions_title.configure(text_color=c["text_muted"])
        self.tools_title.configure(text_color=c["text_muted"])
        self.header_title.configure(text_color=c["text_primary"])
        self.msg_count_label.configure(text_color=c["text_muted"])
        self.bar.configure(fg_color=c["card_bg"], border_color=c["border"])
        self.entry.configure(text_color=c["text_primary"])
        self.theme_btn.configure(
            text="☀️ Light Mode" if self.theme_name == "dark" else "🌙 Dark Mode",
            border_color=c["border"], text_color=c["text_primary"],
        )

        for btn in self._sidebar_buttons:
            btn.restyle(c)
        for b in self.tool_buttons:
            b.configure(fg_color=c["card_bg"], hover_color=c["card_hover"], text_color=c["text_primary"])

        # re-render the whole conversation so older bubbles also match
        for widget in self.chat_scroll.winfo_children():
            widget.destroy()
        history = self.chat_history
        self.chat_history = []
        for sender, text, timestamp in history:
            is_user = sender == "You"
            bubble = ChatBubble(self.chat_scroll, text, is_user, timestamp, self.colors, self.fonts)
            bubble.pack(fill="x", pady=(3, 0))
        self.chat_history = history
        self._scroll_to_bottom()

    # ------------------------------------------------------------------
    def _open_analytics(self):
        stats = self.bot.get_usage_stats()

        win = ctk.CTkToplevel(self)
        win.title(f"Session Analytics — {BOT_NAME}")
        win.geometry("580x500")
        win.configure(fg_color=self.colors["bg_main"])
        win.grab_set()

        ctk.CTkLabel(
            win, text="📊 Rule-Match Analytics", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(18, 4))
        ctk.CTkLabel(
            win, text=f"{self.bot.message_count} message(s) processed this session",
            font=ctk.CTkFont(size=12), text_color=self.colors["text_muted"],
        ).pack(pady=(0, 14))

        if not stats:
            ctk.CTkLabel(win, text=f"No messages sent yet — chat with {BOT_NAME} first!").pack(pady=40)
            return

        labels = list(stats.keys())
        values = list(stats.values())

        plt.style.use("dark_background" if self.theme_name == "dark" else "default")
        fig, ax = plt.subplots(figsize=(5.3, 3.7), dpi=100)
        bars = ax.barh(labels, values, color=ACCENT)
        ax.set_xlabel("Times matched")
        ax.set_title("Which rules fired this session", fontsize=11)
        ax.bar_label(bars, padding=3, fontsize=8)
        fig.tight_layout()
        fig.patch.set_facecolor(self.colors["card_bg"])
        ax.set_facecolor(self.colors["card_bg"])

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=18, pady=(0, 18))
        plt.close(fig)

    def _export_chat(self):
        if not self.chat_history:
            return
        filename = f"chat_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(os.path.expanduser("~"), filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"{BOT_NAME} Chat Transcript — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write("=" * 50 + "\n\n")
                for sender, text, ts in self.chat_history:
                    f.write(f"[{ts}] {sender}: {text}\n")
            self._add_bubble(f"✅ Chat exported to: {filepath}", is_user=False)
        except OSError as e:
            self._add_bubble(f"⚠️ Could not export chat: {e}", is_user=False)


if __name__ == "__main__":
    app = ChatbotApp()
    app.mainloop()
