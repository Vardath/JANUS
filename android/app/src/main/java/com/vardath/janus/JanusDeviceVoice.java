package com.vardath.janus;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.util.ArrayList;
import java.util.Locale;
import java.util.UUID;

/**
 * Zero-OpenAI-cost device voice surface for JANUS.
 * Recognition is push-to-talk only; language follows JanusLanguageSettings.
 */
final class JanusDeviceVoice {
    static final int REQUEST_RECORD_AUDIO = 731;

    interface Listener {
        void onReady(boolean onDevice);
        void onPartial(String text);
        void onRecognized(String text, boolean onDevice);
        void onError(String message);
    }

    private final Activity activity;
    private SpeechRecognizer recognizer;
    private TextToSpeech tts;
    private boolean usingOnDevice;

    JanusDeviceVoice(Activity activity) { this.activity = activity; }

    boolean recognitionAvailable() { return SpeechRecognizer.isRecognitionAvailable(activity); }
    boolean onDeviceRecognitionAvailable() { return Build.VERSION.SDK_INT >= 31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(activity); }
    boolean hasMicPermission() { return ContextCompat.checkSelfPermission(activity, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED; }
    void requestMicPermission() { ActivityCompat.requestPermissions(activity, new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_RECORD_AUDIO); }

    void startPushToTalk(Listener listener) {
        if (listener == null) return;
        if (!hasMicPermission()) {
            listener.onError("Microphone permission is required only while using push-to-talk.");
            requestMicPermission();
            return;
        }
        if (!recognitionAvailable()) {
            listener.onError("No speech-recognition service is available on this device.");
            return;
        }
        stopRecognition();
        try {
            usingOnDevice = onDeviceRecognitionAvailable();
            recognizer = usingOnDevice ? SpeechRecognizer.createOnDeviceSpeechRecognizer(activity) : SpeechRecognizer.createSpeechRecognizer(activity);
            recognizer.setRecognitionListener(new RecognitionListener() {
                @Override public void onReadyForSpeech(Bundle params) { listener.onReady(usingOnDevice); }
                @Override public void onBeginningOfSpeech() {}
                @Override public void onRmsChanged(float rmsdB) {}
                @Override public void onBufferReceived(byte[] buffer) {}
                @Override public void onEndOfSpeech() {}
                @Override public void onError(int error) { listener.onError(errorText(error)); }
                @Override public void onResults(Bundle results) {
                    ArrayList<String> values = results == null ? null : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    String text = first(values);
                    if (text.isEmpty()) listener.onError("No speech was recognized.");
                    else listener.onRecognized(text, usingOnDevice);
                }
                @Override public void onPartialResults(Bundle partialResults) {
                    ArrayList<String> values = partialResults == null ? null : partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    String text = first(values);
                    if (!text.isEmpty()) listener.onPartial(text);
                }
                @Override public void onEvent(int eventType, Bundle params) {}
            });
            Locale speechLocale = JanusLanguageSettings.speechLocale(activity);
            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, speechLocale.toLanguageTag());
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, speechLocale.toLanguageTag());
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
            recognizer.startListening(intent);
        } catch (Exception e) {
            stopRecognition();
            listener.onError("Speech recognition could not start on this device.");
        }
    }

    void stopRecognition() {
        if (recognizer != null) {
            try { recognizer.cancel(); } catch (Exception ignored) {}
            try { recognizer.destroy(); } catch (Exception ignored) {}
            recognizer = null;
        }
    }

    void speak(String text) {
        String clean = clean(text, TextToSpeech.getMaxSpeechInputLength());
        if (clean.isEmpty()) return;
        Locale requested = JanusLanguageSettings.speechLocale(activity);
        if (tts == null) {
            tts = new TextToSpeech(activity.getApplicationContext(), status -> {
                if (status == TextToSpeech.SUCCESS && tts != null) speakWithLocale(clean, requested);
            });
            return;
        }
        speakWithLocale(clean, requested);
    }

    private void speakWithLocale(String clean, Locale requested) {
        if (tts == null) return;
        int availability = tts.isLanguageAvailable(requested);
        Locale actual = availability >= TextToSpeech.LANG_AVAILABLE ? requested : Locale.getDefault();
        tts.setLanguage(actual);
        tts.speak(clean, TextToSpeech.QUEUE_FLUSH, null, "janus-" + UUID.randomUUID());
    }

    void stopSpeaking() { if (tts != null) tts.stop(); }

    void destroy() {
        stopRecognition();
        if (tts != null) {
            try { tts.stop(); } catch (Exception ignored) {}
            try { tts.shutdown(); } catch (Exception ignored) {}
            tts = null;
        }
    }

    private static String first(ArrayList<String> values) {
        if (values == null) return "";
        for (String value : values) {
            String x = clean(value, 4000);
            if (!x.isEmpty()) return x;
        }
        return "";
    }

    private static String clean(String value, int max) {
        String x = value == null ? "" : value.replace('\n', ' ').replace('\r', ' ').trim();
        if (max <= 0) max = 4000;
        return x.length() <= max ? x : x.substring(0, max);
    }

    private static String errorText(int code) {
        switch (code) {
            case SpeechRecognizer.ERROR_AUDIO: return "There was a microphone/audio error.";
            case SpeechRecognizer.ERROR_CLIENT: return "Speech recognition was cancelled.";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: return "Microphone permission was not granted.";
            case SpeechRecognizer.ERROR_NETWORK: return "The device speech service reported a network error.";
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: return "The device speech service timed out.";
            case SpeechRecognizer.ERROR_NO_MATCH: return "No clear speech match was found.";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY: return "The device speech recognizer is busy.";
            case SpeechRecognizer.ERROR_SERVER: return "The device speech-recognition service reported an error.";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: return "No speech was heard.";
            default: return "Speech recognition stopped (code " + code + ").";
        }
    }
}
