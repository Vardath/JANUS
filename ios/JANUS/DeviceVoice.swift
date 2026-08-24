import AVFoundation
import Foundation
import Speech

/// Zero-OpenAI-cost device/system voice surface for JANUS on Apple platforms.
/// Recognition is explicit push-to-talk only; recognized text must still be sent
/// through the ordinary JANUS Chat path. Speech output uses AVSpeechSynthesizer.
@MainActor
final class DeviceVoice: ObservableObject {
    @Published private(set) var listening = false
    @Published private(set) var partialText = ""
    @Published private(set) var errorText: String?

    private let audioEngine = AVAudioEngine()
    private let synthesizer = AVSpeechSynthesizer()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?

    var recognitionAvailable: Bool {
        SFSpeechRecognizer(locale: Locale.current)?.isAvailable == true
    }

    func requestPermissions() async -> Bool {
        let speechAllowed = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status == .authorized)
            }
        }
        guard speechAllowed else {
            errorText = "Speech recognition permission was not granted."
            return false
        }

        let micAllowed: Bool
        if #available(iOS 17.0, *) {
            micAllowed = await AVAudioApplication.requestRecordPermission()
        } else {
            micAllowed = await withCheckedContinuation { continuation in
                AVAudioSession.sharedInstance().requestRecordPermission { allowed in
                    continuation.resume(returning: allowed)
                }
            }
        }
        if !micAllowed { errorText = "Microphone permission was not granted." }
        return micAllowed
    }

    func startPushToTalk(onFinal: @escaping (String) -> Void) async {
        errorText = nil
        guard await requestPermissions() else { return }
        guard let recognizer = SFSpeechRecognizer(locale: Locale.current), recognizer.isAvailable else {
            errorText = "Speech recognition is not available on this device right now."
            return
        }
        stopRecognition()

        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.record, mode: .measurement, options: .duckOthers)
            try session.setActive(true, options: .notifyOthersOnDeactivation)

            let request = SFSpeechAudioBufferRecognitionRequest()
            request.shouldReportPartialResults = true
            if recognizer.supportsOnDeviceRecognition {
                request.requiresOnDeviceRecognition = true
            }
            recognitionRequest = request

            let input = audioEngine.inputNode
            let format = input.outputFormat(forBus: 0)
            input.removeTap(onBus: 0)
            input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak request] buffer, _ in
                request?.append(buffer)
            }

            audioEngine.prepare()
            try audioEngine.start()
            listening = true
            recognitionTask = recognizer.recognitionTask(with: request) { [weak self] result, error in
                guard let self else { return }
                Task { @MainActor in
                    if let result {
                        self.partialText = result.bestTranscription.formattedString
                        if result.isFinal {
                            let final = self.partialText.trimmingCharacters(in: .whitespacesAndNewlines)
                            self.stopRecognition()
                            if !final.isEmpty { onFinal(final) }
                        }
                    }
                    if error != nil {
                        self.stopRecognition()
                        if self.partialText.isEmpty { self.errorText = "Speech recognition stopped before a clear result was produced." }
                    }
                }
            }
        } catch {
            stopRecognition()
            errorText = "Speech recognition could not start: \(error.localizedDescription)"
        }
    }

    func stopRecognition() {
        if audioEngine.isRunning { audioEngine.stop() }
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()
        recognitionTask = nil
        recognitionRequest = nil
        listening = false
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    func speak(_ text: String) {
        let clean = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { return }
        synthesizer.stopSpeaking(at: .immediate)
        let utterance = AVSpeechUtterance(string: clean)
        utterance.voice = AVSpeechSynthesisVoice(language: Locale.current.language.languageCode?.identifier)
        synthesizer.speak(utterance)
    }

    func stopSpeaking() {
        synthesizer.stopSpeaking(at: .immediate)
    }
}
