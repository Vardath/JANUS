import janus_client as base

base.APP_NAME = "JANUS - Global 7-3-1 v0.16"


def _build_chat_page(self):
    page = self._new_page("chat")
    self._header(page, "Conversation", "Enter sends • Shift+Enter starts a new line")

    # Composer is packed FIRST and pinned to the bottom so the expanding
    # transcript can never push it out of view.
    composer = base.ttk.Frame(page, padding=(0, 8, 0, 0))
    composer.pack(side="bottom", fill="x")

    self.message_entry = base.tk.Text(
        composer,
        height=3,
        wrap="word",
        font=("Segoe UI", 11),
        padx=10,
        pady=8,
        relief="solid",
        borderwidth=1,
    )
    self.message_entry.pack(side="left", fill="x", expand=True)
    self.message_entry.bind("<Return>", self._enter_send)
    self.message_entry.bind("<Shift-Return>", self._shift_enter)
    base.ttk.Button(composer, text="Send", command=self.send_chat).pack(
        side="right", padx=(8, 0), fill="y"
    )

    transcript = base.ttk.Frame(page)
    transcript.pack(side="top", fill="both", expand=True)

    self.chat_log = base.tk.Text(
        transcript,
        wrap="word",
        state="disabled",
        font=("Segoe UI", 11),
        padx=14,
        pady=10,
        spacing1=2,
        spacing3=8,
        relief="solid",
        borderwidth=1,
    )
    scroll = base.ttk.Scrollbar(transcript, orient="vertical", command=self.chat_log.yview)
    self.chat_log.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    self.chat_log.pack(side="left", fill="both", expand=True)

    # Messenger-style lanes in one continuous transcript.
    self.chat_log.tag_configure(
        "janus_msg",
        justify="left",
        lmargin1=14,
        lmargin2=14,
        rmargin=280,
        spacing1=3,
        spacing3=10,
        background="#f1f1f1",
    )
    self.chat_log.tag_configure(
        "user_msg",
        justify="right",
        lmargin1=280,
        lmargin2=280,
        rmargin=14,
        spacing1=3,
        spacing3=10,
        background="#dfefff",
    )
    self.chat_log.tag_configure(
        "system_msg",
        justify="center",
        lmargin1=120,
        lmargin2=120,
        rmargin=120,
        spacing1=3,
        spacing3=10,
    )
    self.chat_log.tag_configure("janus_name", font=("Segoe UI", 9, "bold"))
    self.chat_log.tag_configure("user_name", font=("Segoe UI", 9, "bold"))
    self.chat_log.tag_configure("system_name", font=("Segoe UI", 9, "italic"))

    self.message_entry.focus_set()


def append_chat(self, speaker, text):
    who = str(speaker or "JANUS")
    body = str(text)
    if who.lower() in {"you", "user"}:
        msg_tag, name_tag, label = "user_msg", "user_name", "You"
    elif who.lower() == "janus":
        msg_tag, name_tag, label = "janus_msg", "janus_name", "JANUS"
    else:
        msg_tag, name_tag, label = "system_msg", "system_name", who

    self.chat_log.config(state="normal")
    self.chat_log.insert("end", f"{label}\n", (msg_tag, name_tag))
    self.chat_log.insert("end", body + "\n\n", (msg_tag,))
    self.chat_log.see("end")
    self.chat_log.config(state="disabled")


base.JanusClient._build_chat_page = _build_chat_page
base.JanusClient.append_chat = append_chat


if __name__ == "__main__":
    base.JanusClient().mainloop()
