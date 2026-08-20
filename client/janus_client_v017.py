import janus_client_v015  # applies the v0.16 messenger chat patches
import janus_client as base

base.APP_NAME = "JANUS - Global 7-3-1 v0.17"


def flatten_rows(data):
    """Accept both the old table-shaped API and the newer items/notes API."""
    rows = []
    if not isinstance(data, dict):
        return rows

    sources = []
    if isinstance(data.get("items"), list):
        sources.append(("items", data["items"]))
    if isinstance(data.get("notes"), list):
        sources.append(("notes", data["notes"]))
    for table, items in (data.get("tables") or {}).items():
        sources.append((table, items or []))

    for table, items in sources:
        for item in items or []:
            if not isinstance(item, dict):
                continue
            text = item.get("detail") or item.get("content") or item.get("message") or item.get("text") or ""
            kind = item.get("event_type") or item.get("role") or item.get("type") or table
            when = item.get("created_at") or item.get("updated_at") or item.get("timestamp") or ""
            rows.append({"table": table, "kind": str(kind), "when": str(when), "text": str(text), "raw": item})
    rows.sort(key=lambda r: r["when"], reverse=True)
    return rows


base.flatten_rows = flatten_rows


def _build_cores_page(self):
    page = self._new_page("cores")
    self._header(page, "Cores", "JANUS 7 → 3 → 1 processing architecture", lambda: self.refresh_page("cores"))
    self.cores_status = base.tk.StringVar(value="Loading core status...")
    base.ttk.Label(page, textvariable=self.cores_status, font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 8))

    self.cores_tabs = base.ttk.Notebook(page)
    self.cores_tabs.pack(fill="both", expand=True)
    self.server_core_tab = base.ttk.Frame(self.cores_tabs, padding=8)
    self.client_core_tab = base.ttk.Frame(self.cores_tabs, padding=8)
    self.cores_tabs.add(self.server_core_tab, text="Server")
    self.cores_tabs.add(self.client_core_tab, text="Client")

    self.server_core_cards = base.ttk.Frame(self.server_core_tab)
    self.server_core_cards.pack(fill="both", expand=True)

    client = base.ttk.LabelFrame(self.client_core_tab, text="Local JANUS client", style="Card.TLabelframe")
    client.pack(fill="x", pady=6)
    self.client_core_summary = base.tk.StringVar(value="Loading client information...")
    base.ttk.Label(client, textvariable=self.client_core_summary, justify="left", wraplength=800).pack(anchor="w")

    display = base.ttk.LabelFrame(self.client_core_tab, text="Client behaviour", style="Card.TLabelframe")
    display.pack(fill="x", pady=6)
    self.client_display_summary = base.tk.StringVar(value="")
    base.ttk.Label(display, textvariable=self.client_display_summary, justify="left", wraplength=800).pack(anchor="w")


def _render_cores(self, data):
    for child in self.server_core_cards.winfo_children():
        child.destroy()

    runtime = data.get("runtime", {}) if isinstance(data, dict) else {}
    self.cores_status.set(
        f"Status: {str(data.get('status','unknown')).title()}   •   "
        f"Topology: {data.get('topology','7 -> 3 -> 1')}   •   "
        f"Model: {runtime.get('model','unknown')}"
    )

    origin = base.ttk.LabelFrame(self.server_core_cards, text="Server identity", style="Card.TLabelframe")
    origin.pack(fill="x", pady=5)
    base.ttk.Label(origin, text=data.get("origin", "JANUS global core"), wraplength=850, justify="left").pack(anchor="w")

    seven = base.ttk.LabelFrame(self.server_core_cards, text="7 specialist lenses", style="Card.TLabelframe")
    seven.pack(fill="x", pady=5)
    roles = data.get("seven_roles", {})
    if isinstance(roles, list):
        roles = {str(x): "" for x in roles}
    for name, desc in roles.items():
        row = base.ttk.Frame(seven)
        row.pack(fill="x", pady=2)
        base.ttk.Label(row, text=str(name), width=16, font=("Segoe UI", 10, "bold")).pack(side="left", anchor="n")
        base.ttk.Label(row, text=str(desc), wraplength=700, justify="left").pack(side="left", fill="x", expand=True)

    three = base.ttk.LabelFrame(self.server_core_cards, text="3 synthesis bridges", style="Card.TLabelframe")
    three.pack(fill="x", pady=5)
    bridges = data.get("three_bridges", {})
    if isinstance(bridges, list):
        bridges = {str(x): "" for x in bridges}
    for name, desc in bridges.items():
        row = base.ttk.Frame(three)
        row.pack(fill="x", pady=2)
        base.ttk.Label(row, text=str(name), width=22, font=("Segoe UI", 10, "bold")).pack(side="left", anchor="n")
        base.ttk.Label(row, text=str(desc), wraplength=650, justify="left").pack(side="left", fill="x", expand=True)

    one = base.ttk.LabelFrame(self.server_core_cards, text="1 integrator", style="Card.TLabelframe")
    one.pack(fill="x", pady=5)
    integ = data.get("one_integrator", {})
    if isinstance(integ, dict):
        text = f"{integ.get('name','JANUS integrated response')}\n{integ.get('description','')}"
    else:
        text = str(integ)
    base.ttk.Label(one, text=text, wraplength=820, justify="left", font=("Segoe UI", 10, "bold")).pack(anchor="w")

    rt = base.ttk.LabelFrame(self.server_core_cards, text="Server runtime", style="Card.TLabelframe")
    rt.pack(fill="x", pady=5)
    base.ttk.Label(rt, text=(
        f"Background worker: {'On' if runtime.get('background_worker') else 'Off'}   •   "
        f"External access: {'On' if runtime.get('external_access') else 'Off'}   •   "
        f"Supervisor consultation: {'On' if runtime.get('supervisor_consultation') else 'Off'}   •   "
        f"Compute: {runtime.get('compute_budget','balanced')}"
    ), wraplength=850, justify="left").pack(anchor="w")

    self.client_core_summary.set(
        f"Version: v0.17\nLocal profile: {self.profile_id}\nServer: {self.api.base_url}\nConnection: {self.status_var.get()}"
    )
    self.client_display_summary.set(
        f"Auto-refresh: {'On' if self.auto_refresh.get() else 'Off'}\n"
        f"Refresh interval: {self.refresh_seconds.get()} seconds\n"
        f"Chat activity shown: {'Yes' if self.show_chat_activity.get() else 'No'}\n"
        f"Technical details shown: {'Yes' if self.show_technical.get() else 'No'}"
    )


def _render_observe(self, data):
    cycle = data.get("background_cycle", {}) if isinstance(data, dict) else {}
    notes = flatten_rows(data)
    self.observe_status.set(
        f"JANUS online • background worker {'on' if cycle.get('worker_enabled') else 'off'} • "
        f"cycle {cycle.get('interval_minutes','?')} min • {len(notes)} recent notes"
    )
    self._render_observe_notes(data)


base.JanusClient._build_cores_page = _build_cores_page
base.JanusClient._render_cores = _render_cores
base.JanusClient._render_observe = _render_observe


if __name__ == "__main__":
    base.JanusClient().mainloop()
