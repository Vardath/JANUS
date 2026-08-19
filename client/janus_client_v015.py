import janus_client as base

base.APP_NAME = "JANUS - Global 7-3-1 v0.15"


def _build_chat_page(self):
    page = self._new_page("chat")
    self._header(page, "Conversation", "Enter sends • Shift+Enter starts a new line")
    self.chat_log = base.tk.Text(
        page,
        wrap="word",
        state="disabled",
        font=("Segoe UI", 11),
        padx=12,
        pady=10,
        spacing1=2,
        spacing3=8,
    )
    self.chat_log.pack(fill="both", expand=True)

    # Separate conversational lanes while preserving one continuous transcript.
    self.chat_log.tag_configure(
        "janus_msg",
        justify="left",
        lmargin1=12,
        lmargin2=12,
        rmargin=220,
        spacing1=4,
        spacing3=10,
    )
    self.chat_log.tag_configure(
        "user_msg",
        justify="right",
        lmargin1=220,
        lmargin2=220,
        rmargin=12,
        spacing1=4,
        spacing3=10,
    )
    self.chat_log.tag_configure(
        "system_msg",
        justify="center",
        lmargin1=90,
        lmargin2=90,
        rmargin=90,
        spacing1=4,
        spacing3=10,
    )
    self.chat_log.tag_configure("janus_name", font=("Segoe UI", 9, "bold"))
    self.chat_log.tag_configure("user_name", font=("Segoe UI", 9, "bold"))
    self.chat_log.tag_configure("system_name", font=("Segoe UI", 9, "italic"))

    bottom = base.ttk.Frame(page)
    bottom.pack(fill="x", pady=(8, 0))
    self.message_entry = base.tk.Text(bottom, height=4, wrap="word", font=("Segoe UI", 11), padx=6, pady=6)
    self.message_entry.pack(side="left", fill="x", expand=True)
    self.message_entry.bind("<Return>", self._enter_send)
    self.message_entry.bind("<Shift-Return>", self._shift_enter)
    base.ttk.Button(bottom, text="Send", command=self.send_chat).pack(side="left", padx=(8, 0), fill="y")


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
