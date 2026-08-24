package com.vardath.janus;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.WeakHashMap;

/**
 * v0.90 Messages -> Chat reply-context bridge.
 *
 * MainActivity historically pasted the surfaced JANUS message into the visible
 * composer so the context reached /desktop/chat. This layer preserves that
 * transport contract while presenting the quoted JANUS message as a separate
 * native context card. The user's composer therefore contains only their reply.
 * Immediately before Send is dispatched, the hidden context is restored to the
 * payload text; the existing Chat sender then transmits the same contextual
 * message as before. No server or cognition contract changes are required.
 */
public final class JanusReplyContextPolish {
    private static final String PREFIX = "Regarding your message:\n“";
    private static final String SUFFIX = "”\n\n";
    private static final WeakHashMap<EditText, ReplyState> STATES = new WeakHashMap<>();

    private JanusReplyContextPolish() {}

    public static void install(Activity activity) {
        if (activity == null || activity.getWindow() == null) return;
        View decor = activity.getWindow().getDecorView();
        decor.post(() -> scan(decor));
        decor.getViewTreeObserver().addOnGlobalLayoutListener(() -> scan(decor));
    }

    private static void scan(View view) {
        if (view instanceof EditText) {
            EditText edit = (EditText) view;
            CharSequence hint = edit.getHint();
            if (hint != null && "Message JANUS".contentEquals(hint)) attach(edit);
        }
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) scan(group.getChildAt(i));
        }
    }

    private static void attach(EditText composer) {
        if (STATES.containsKey(composer)) return;
        ReplyState state = new ReplyState();
        STATES.put(composer, state);
        composer.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {}
            @Override public void afterTextChanged(Editable editable) {
                if (state.internalChange) return;
                String text = editable == null ? "" : editable.toString();
                if (text.startsWith(PREFIX)) {
                    int end = text.indexOf(SUFFIX, PREFIX.length());
                    if (end > PREFIX.length()) {
                        state.context = text.substring(PREFIX.length(), end);
                        state.internalChange = true;
                        composer.setText(text.substring(end + SUFFIX.length()));
                        composer.setSelection(composer.length());
                        state.internalChange = false;
                        showContextCard(composer, state);
                    }
                } else if (text.isEmpty() && state.sending) {
                    state.sending = false;
                    state.context = "";
                    removeContextCard(state);
                }
            }
        });
        wireSendButton(composer, state);
    }

    private static void wireSendButton(EditText composer, ReplyState state) {
        View parent = (View) composer.getParent();
        if (!(parent instanceof ViewGroup)) return;
        ViewGroup row = (ViewGroup) parent;
        for (int i = 0; i < row.getChildCount(); i++) {
            View child = row.getChildAt(i);
            if (!(child instanceof Button)) continue;
            Button button = (Button) child;
            if (!"Send".contentEquals(button.getText())) continue;
            button.setOnTouchListener((v, event) -> {
                if (event.getAction() == MotionEvent.ACTION_DOWN && !state.context.isEmpty()) {
                    String reply = composer.getText().toString();
                    state.sending = true;
                    state.internalChange = true;
                    composer.setText(PREFIX + state.context + SUFFIX + reply);
                    composer.setSelection(composer.length());
                    state.internalChange = false;
                }
                return false;
            });
        }
    }

    private static void showContextCard(EditText composer, ReplyState state) {
        removeContextCard(state);
        View parent = (View) composer.getParent();
        if (!(parent instanceof LinearLayout)) return;
        View grand = (View) parent.getParent();
        if (!(grand instanceof LinearLayout)) return;
        LinearLayout container = (LinearLayout) grand;
        int index = container.indexOfChild(parent);
        if (index < 0) return;

        TextView card = new TextView(composer.getContext());
        card.setText("Replying to JANUS\n“" + state.context + "”");
        card.setTextSize(13f);
        card.setTypeface(Typeface.DEFAULT, Typeface.NORMAL);
        card.setTextColor(Color.rgb(205, 216, 230));
        card.setBackgroundColor(Color.rgb(37, 46, 58));
        int p = dp(composer, 12);
        card.setPadding(p, dp(composer, 9), p, dp(composer, 9));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.setMargins(0, dp(composer, 4), 0, dp(composer, 6));
        container.addView(card, index, lp);
        state.card = card;
    }

    private static void removeContextCard(ReplyState state) {
        if (state.card == null) return;
        ViewGroup parent = (ViewGroup) state.card.getParent();
        if (parent != null) parent.removeView(state.card);
        state.card = null;
    }

    private static int dp(View view, int value) {
        return Math.round(value * view.getResources().getDisplayMetrics().density);
    }

    private static final class ReplyState {
        String context = "";
        boolean internalChange;
        boolean sending;
        TextView card;
    }
}
