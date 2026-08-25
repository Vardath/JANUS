# JANUS Android v1.10 safe-area/readability checkpoint — 2026-08-25

This checkpoint continues the explicit-owner Android UI rebuild after theme isolation, native Stream routing and localization migration.

Implemented in this pass:

- `JanusSafeArea` owns root safe-area application directly through `WindowInsetsCompat`; no global-layout listener or live hierarchy walk is used.
- Both authentication and signed-in app roots opt into safe-area handling when they are created.
- System bars and display cutouts are added to authored root padding; IME bottom inset raises the app above the keyboard.
- `JanusBuildInfo` is now the user-visible source for Android version/build labels, using `BuildConfig.VERSION_NAME` and `BuildConfig.VERSION_CODE` instead of hard-coded Options text.
- The five top-level pages remain first-class native pages, but navigation now sits in a horizontal scroll container with readable minimum tab widths rather than compressing all five controls into one narrow row.
- Stable Chat, Messages and Observe headings now use explicit shell translation at creation time; conversation bodies remain untouched.

Preserve:

- explicit component ownership;
- no restoration of cosmetic/global `OnGlobalLayoutListener` injectors;
- app-only JANUS theme settings;
- predictive/system Back behavior;
- Stream as an explicit page;
- local/global runtime separation and the 22-core recursive architecture;
- diagnostics and maintenance governance.

Next real-device validation should cover Chat, Messages, Observe, Stream, Options, Cores, Memory and Settings, including opening the keyboard, rotating/resuming if relevant, and checking status/navigation bar and gesture-navigation overlap.

If a detail screen still closes, expose and use the stored `JanusClientDiagnostics` report instead of adding speculative layout patches.
