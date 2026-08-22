import base64
import mimetypes
import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

import janus_client_v022 as v022

APP_NAME = "JANUS - Global 7-2-1-1 v0.24"
MAX_FILE_BYTES = 8 * 1024 * 1024


class AttachmentAPI(v022.AuthAPI):
    def upload_file(self, path: str):
        size = os.path.getsize(path)
        if size <= 0:
            raise RuntimeError("Empty files are not supported")
        if size > MAX_FILE_BYTES:
            raise RuntimeError("JANUS currently accepts files up to 8 MiB")
        with open(path, "rb") as f:
            data = f.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise RuntimeError("JANUS currently accepts files up to 8 MiB")
        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
        return self.call(
            "POST",
            "/files/upload",
            {
                "filename": os.path.basename(path),
                "mime_type": mime,
                "data_base64": base64.b64encode(data).decode("ascii"),
            },
            timeout=120,
        )


# v0.22/v0.23 constructs its API through the inherited factory.
v022.v021.base.API = AttachmentAPI


class App(v022.App):
    def __init__(self):
        self._pending_attachments = []
        super().__init__()
        self.title(APP_NAME)

    def build_chat(self):
        p = self.page("chat")
        self.head(p, "Chat", "Enter sends • Shift+Enter adds a line • Attach adds account-bound file grounding")
        self.chat = tk.Text(p, state="disabled", wrap="word", font=("Segoe UI", 11), padx=8, pady=8)
        self.chat.pack(fill="both", expand=True)

        self.attachment_var = tk.StringVar(value="No files attached")
        attach_row = ttk.Frame(p)
        attach_row.pack(fill="x", pady=(8, 0))
        ttk.Button(attach_row, text="Attach file", command=self.attach_file).pack(side="left")
        ttk.Button(attach_row, text="Clear", command=self.clear_attachments).pack(side="left", padx=(6, 8))
        ttk.Label(attach_row, textvariable=self.attachment_var).pack(side="left", fill="x", expand=True)

        row = ttk.Frame(p)
        row.pack(fill="x", pady=8)
        self.entry = tk.Text(row, height=4, wrap="word", font=("Segoe UI", 11))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.enter_key)
        self.entry.bind("<Shift-Return>", self.shift_enter)
        ttk.Button(row, text="Send", command=self.send).pack(side="left", fill="y", padx=8)
        self.say("JANUS", "Connected. Ready.")

    def _refresh_attachment_label(self):
        if not self._pending_attachments:
            self.attachment_var.set("No files attached")
            return
        names = [str(x.get("filename") or "file") for x in self._pending_attachments]
        self.attachment_var.set("Attached: " + ", ".join(names))

    def attach_file(self):
        if len(self._pending_attachments) >= 4:
            messagebox.showinfo("JANUS", "Up to 4 files can be attached to one Chat turn.")
            return
        path = filedialog.askopenfilename(
            title="Attach a file to JANUS",
            filetypes=[
                ("JANUS-supported files", "*.txt *.md *.json *.csv *.tsv *.log *.py *.js *.ts *.java *.kt *.swift *.c *.h *.cpp *.cs *.go *.rs *.rb *.php *.sh *.ps1 *.bat *.xml *.yaml *.yml *.toml *.ini *.cfg *.conf *.sql *.html *.css *.pdf *.png *.jpg *.jpeg *.webp *.gif"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self.status.set("Uploading attachment")
        self.bg(lambda: self.api.upload_file(path), self._attachment_uploaded)

    def _attachment_uploaded(self, result):
        item = result.get("file") if isinstance(result, dict) else None
        if not isinstance(item, dict) or not item.get("id"):
            self.status.set("Active")
            self.say("System", "JANUS could not confirm that attachment upload.")
            return
        if all(x.get("id") != item.get("id") for x in self._pending_attachments):
            self._pending_attachments.append(item)
        self._refresh_attachment_label()
        self.status.set("Attachment ready")

    def clear_attachments(self):
        self._pending_attachments = []
        if hasattr(self, "attachment_var"):
            self._refresh_attachment_label()

    def send(self):
        message = self.entry.get("1.0", "end").strip()
        attachments = list(self._pending_attachments)
        if not message and not attachments:
            return
        if not message:
            message = "Please assess the attached file or files."
        self.entry.delete("1.0", "end")
        display = message
        if attachments:
            display += "\n\n" + "\n".join(f"[Attached: {x.get('filename','file')}]" for x in attachments)
        self.say("You", display)
        self.clear_attachments()
        self.status.set("Processing")
        payload = {
            "profile_id": self.user,
            "message": message,
            "attachment_ids": [str(x.get("id")) for x in attachments if x.get("id")],
        }
        self.bg(lambda: self.api.call("POST", "/desktop/chat", payload), self.chat_done)

    def logout_account(self):
        self.clear_attachments()
        super().logout_account()


if __name__ == "__main__":
    App().mainloop()
