import SwiftUI

struct ContentView: View {
    @StateObject private var api = APIClient()
    @AppStorage("janusProfile") private var profile = ""
    @AppStorage("janusLoginIdentifier") private var savedIdentifier = ""
    @State private var authMode = 0
    @State private var identifier = ""
    @State private var password = ""
    @State private var registerUsername = ""
    @State private var registerEmail = ""
    @State private var registerPassword = ""
    @State private var authBusy = false
    @State private var selectedTab = 0
    @State private var chatText = ""
    @State private var chat: [(String, String)] = [("JANUS", "Ready.")]
    @State private var messages: [JanusMessage] = []
    @State private var unread = 0
    @State private var home: HomeResponse?
    @State private var observeItems: [ActivityItem] = []
    @State private var activityItems: [ActivityItem] = []
    @State private var memoryItems: [MemoryItem] = []
    @State private var errorText: String?

    private var signedIn: Bool {
        !profile.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !api.accessToken.isEmpty
    }

    var body: some View {
        NavigationStack {
            Group {
                if signedIn { appView } else { loginView }
            }
            .navigationTitle("JANUS")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Text(api.status).font(.caption).foregroundStyle(.secondary)
                }
            }
            .task { await startup() }
            .alert("JANUS", isPresented: Binding(get: { errorText != nil }, set: { if !$0 { errorText = nil } })) {
                Button("OK", role: .cancel) { errorText = nil }
            } message: {
                Text(errorText ?? "")
            }
        }
    }

    private var loginView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Spacer(minLength: 30)
                Text("Global 7→2→1→1").font(.largeTitle.bold())
                Text("Sign in to continue the same JANUS identity, memory and message outbox across devices.")
                    .foregroundStyle(.secondary)

                Picker("Account", selection: $authMode) {
                    Text("Sign in").tag(0)
                    Text("Create account").tag(1)
                }
                .pickerStyle(.segmented)

                if authMode == 0 {
                    TextField("Username or email", text: $identifier)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().textFieldStyle(.roundedBorder)
                    SecureField("Password", text: $password).textFieldStyle(.roundedBorder)
                    Button(authBusy ? "Signing in…" : "Sign in") { Task { await signIn() } }
                        .buttonStyle(.borderedProminent).disabled(authBusy || identifier.isEmpty || password.isEmpty)
                } else {
                    TextField("Username", text: $registerUsername)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().textFieldStyle(.roundedBorder)
                    TextField("Email", text: $registerEmail)
                        .textInputAutocapitalization(.never).keyboardType(.emailAddress).autocorrectionDisabled().textFieldStyle(.roundedBorder)
                    SecureField("Password (12+ characters, letter + number)", text: $registerPassword).textFieldStyle(.roundedBorder)
                    Button(authBusy ? "Creating…" : "Create account") { Task { await createAccount() } }
                        .buttonStyle(.borderedProminent)
                        .disabled(authBusy || registerUsername.isEmpty || registerEmail.isEmpty || registerPassword.isEmpty)
                }
                Spacer(minLength: 30)
            }
            .padding()
        }
    }

    private var appView: some View {
        TabView(selection: $selectedTab) {
            chatView.tabItem { Label("Chat", systemImage: "bubble.left.and.bubble.right") }.tag(0)
            messagesView.tabItem { Label("Messages", systemImage: unread > 0 ? "tray.full" : "tray") }.badge(unread).tag(1)
            observeView.tabItem { Label("Observe", systemImage: "eye") }.tag(2)
            optionsView.tabItem { Label("Options", systemImage: "slider.horizontal.3") }.tag(3)
        }
        .onChange(of: selectedTab) { _, tab in Task { await refresh(tab: tab) } }
        .refreshable { await refresh(tab: selectedTab) }
    }

    private var chatView: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 10) {
                        ForEach(Array(chat.enumerated()), id: \.offset) { index, item in
                            HStack {
                                if item.0 == "You" { Spacer(minLength: 40) }
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(item.0).font(.caption.bold())
                                    Text(item.1).textSelection(.enabled)
                                }
                                .padding(10)
                                .background(item.0 == "You" ? Color.accentColor.opacity(0.15) : Color.secondary.opacity(0.12))
                                .clipShape(RoundedRectangle(cornerRadius: 14))
                                if item.0 != "You" { Spacer(minLength: 40) }
                            }.id(index)
                        }
                    }.padding()
                }
                .onChange(of: chat.count) { _, _ in proxy.scrollTo(max(chat.count - 1, 0), anchor: .bottom) }
            }
            Divider()
            HStack(alignment: .bottom) {
                TextField("Message JANUS", text: $chatText, axis: .vertical)
                    .textFieldStyle(.roundedBorder).lineLimit(1...5)
                Button("Send") { Task { await sendChat() } }
                    .buttonStyle(.borderedProminent)
                    .disabled(chatText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }.padding()
        }
    }

    private var messagesView: some View {
        List {
            if messages.isEmpty {
                ContentUnavailableView("No JANUS messages", systemImage: "tray", description: Text("Questions, observations and useful follow-ups will appear here."))
            }
            ForEach(messages) { message in
                VStack(alignment: .leading, spacing: 8) {
                    Text((message.state == "unread" ? "New · " : "") + (message.message_type ?? "Follow-up")).font(.headline)
                    Text(message.created_at ?? "").font(.caption).foregroundStyle(.secondary)
                    Text(message.detail ?? "").textSelection(.enabled)
                    HStack {
                        Button("Answer in Chat") {
                            chatText = "Regarding your \(message.message_type ?? "message") from \(message.created_at ?? ""):\n“\(message.detail ?? "")”\n\n"
                            selectedTab = 0
                            Task { try? await api.setMessageState(id: message.id, profile: profile, state: "read"); await loadMessages() }
                        }
                        Button("Read") { Task { try? await api.setMessageState(id: message.id, profile: profile, state: "read"); await loadMessages() } }
                        Button("Dismiss") { Task { try? await api.setMessageState(id: message.id, profile: profile, state: "dismissed"); await loadMessages() } }
                    }.buttonStyle(.bordered)
                }.padding(.vertical, 6)
            }
        }
    }

    private var observeView: some View {
        List(observeItems.indices, id: \.self) { index in
            let item = observeItems[index]
            VStack(alignment: .leading, spacing: 6) {
                Text((item.event_type ?? "note").replacingOccurrences(of: "_", with: " ")).font(.headline)
                Text(item.created_at ?? "").font(.caption).foregroundStyle(.secondary)
                Text(item.detail ?? "").textSelection(.enabled)
            }
        }
        .overlay { if observeItems.isEmpty { ContentUnavailableView("No observation notes", systemImage: "eye") } }
    }

    private var optionsView: some View {
        List {
            Section("Account") {
                LabeledContent("JANUS profile", value: profile)
                Button("Sign out", role: .destructive) { Task { await signOut() } }
            }
            Section("Global Core") {
                LabeledContent("Server", value: api.baseURL.absoluteString)
                LabeledContent("Status", value: home?.status ?? api.status)
                LabeledContent("Background cycle", value: home?.background_interval_minutes.map { "\($0) min" } ?? "Unknown")
                LabeledContent("Unread messages", value: "\(unread)")
                Button("Refresh now") { Task { await refresh(tab: selectedTab) } }
            }
            Section("Memory") {
                ForEach(memoryItems.indices, id: \.self) { index in
                    let item = memoryItems[index]
                    VStack(alignment: .leading, spacing: 6) {
                        Text("\(item.level ?? "trace") · \(item.role ?? "memory")").font(.headline)
                        Text(item.content ?? "").textSelection(.enabled)
                    }
                }
            }
            Section("Activity") {
                ForEach(activityItems.indices, id: \.self) { index in
                    let item = activityItems[index]
                    VStack(alignment: .leading, spacing: 6) {
                        Text((item.event_type ?? "event").replacingOccurrences(of: "_", with: " ")).font(.headline)
                        Text(item.created_at ?? "").font(.caption).foregroundStyle(.secondary)
                        Text(item.detail ?? "").textSelection(.enabled)
                    }
                }
            }
        }
    }

    private func startup() async {
        identifier = savedIdentifier
        registerEmail = savedIdentifier.contains("@") ? savedIdentifier : ""
        await api.health()
        guard !api.accessToken.isEmpty else { profile = ""; return }
        do {
            let account = try await api.me()
            profile = account.username
            savedIdentifier = account.email
            await loadMessages(); await loadHome()
        } catch {
            await api.logout()
            profile = ""
        }
    }

    private func signIn() async {
        authBusy = true; defer { authBusy = false }
        do {
            let response = try await api.login(identifier: identifier.trimmingCharacters(in: .whitespacesAndNewlines), password: password)
            profile = response.account.username
            savedIdentifier = response.account.email
            password = ""
            await loadMessages(); await loadHome()
        } catch { errorText = error.localizedDescription }
    }

    private func createAccount() async {
        authBusy = true; defer { authBusy = false }
        do {
            let response = try await api.register(
                username: registerUsername.trimmingCharacters(in: .whitespacesAndNewlines),
                email: registerEmail.trimmingCharacters(in: .whitespacesAndNewlines),
                password: registerPassword
            )
            profile = response.account.username
            savedIdentifier = response.account.email
            registerPassword = ""
            if response.verification_required == true && response.email_delivery != true {
                errorText = "Account created. Email verification is pending, but email delivery is not configured yet."
            }
            await loadMessages(); await loadHome()
        } catch { errorText = error.localizedDescription }
    }

    private func signOut() async {
        await api.logout()
        profile = ""
        messages = []; unread = 0; home = nil; observeItems = []; activityItems = []; memoryItems = []
        identifier = savedIdentifier
    }

    private func refresh(tab: Int) async {
        guard signedIn else { return }
        switch tab {
        case 1: await loadMessages()
        case 2: await loadObserve()
        case 3: await loadHome(); await loadMemory(); await loadActivity()
        default: await loadMessages()
        }
    }

    private func sendChat() async {
        let text = chatText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        chatText = ""; chat.append(("You", text))
        do {
            let reply = try await api.chat(profile: profile, message: text)
            chat.append(("JANUS", reply)); await loadMessages()
        } catch { chat.append(("System", error.localizedDescription)) }
    }

    private func loadHome() async {
        do { home = try await api.home(profile: profile); unread = home?.unread_messages ?? unread } catch { errorText = error.localizedDescription }
    }
    private func loadMessages() async {
        do { let r = try await api.messages(profile: profile); messages = r.items ?? []; unread = r.unread ?? messages.filter { $0.state == "unread" }.count } catch { errorText = error.localizedDescription }
    }
    private func loadObserve() async { do { observeItems = try await api.observe(profile: profile) } catch { errorText = error.localizedDescription } }
    private func loadActivity() async { do { activityItems = try await api.activity(profile: profile) } catch { errorText = error.localizedDescription } }
    private func loadMemory() async { do { memoryItems = try await api.memory(profile: profile) } catch { errorText = error.localizedDescription } }
}
