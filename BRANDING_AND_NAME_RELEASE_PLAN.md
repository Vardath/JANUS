# JANUS branding and public-name release plan

Updated: 2026-08-28

## Current decision

The current internal/project name remains **JANUS** during development. Do **not** perform a repository-wide rename yet.

The preferred candidate public product name is **JANUS 137**.

This is intentionally a reversible branding decision until the legal-release audit is complete. The existing JANUS architecture, internal terminology, package structure, server identifiers, repository name and historical documentation should not be renamed merely to reflect the candidate public brand.

## Why the rename is deferred

Renaming immediately would create avoidable churn across Android resources, package metadata, OAuth configuration, signing/release configuration, server labels, documentation, build artifacts, tests, deployment references and historical checkpoints.

The public name should therefore be finalized as part of the release process, after trademark/name clearance and before store listing/public launch.

## Release naming gate

Before public release, perform a fresh legal/brand clearance pass for **JANUS 137**, including at minimum:

- Australian trade mark search for exact and confusingly similar marks in relevant software/AI classes;
- major international jurisdictions/markets likely to matter to launch;
- Google Play and Apple App Store name conflicts;
- existing AI/software products and companies using JANUS, JANUS 137 or confusingly similar forms;
- domain/social-brand availability where commercially relevant;
- assessment of whether the full combined mark `JANUS 137` is sufficiently distinguishable from existing JANUS uses;
- decision whether registration is worthwhile at that stage. Registration is not itself a prerequisite to release, but clearance is a release gate.

If JANUS 137 remains acceptable after that audit, use **JANUS 137** as the public-facing product brand.

If JANUS 137 is not acceptably clear, select a replacement public name before release. Preserve the internal JANUS architecture/project terminology unless there is a concrete legal reason to change it too.

## Rename implementation plan if JANUS 137 is approved

Treat the public-name change as a controlled release task, not a blind global search-and-replace.

1. Inventory every user-visible occurrence of `JANUS` across Android, server-generated UI/messages, release documentation, website/store metadata, icons/splash assets and downloadable artifact names.
2. Separate **public branding** from **architectural/internal identifiers**. Rename only what users should see unless a technical identifier must change for store/release reasons.
3. Update Android application label, About/help/legal surfaces, notification/channel display names, splash/launcher presentation and release artifact naming to `JANUS 137`.
4. Update public web/store descriptions, screenshots, privacy policy, terms, support text and any release landing pages so naming is consistent.
5. Review OAuth consent-screen branding and any identity-provider configuration that displays the app name. Change identifiers only where required; do not casually change application IDs/package names because that can break upgrade continuity.
6. Review server-visible product strings and emails/messages so users do not see a confusing mix of JANUS and JANUS 137. Internal protocol/core identifiers may remain JANUS where appropriate.
7. Re-run signing, OAuth, authentication, migration, deep-link, notification, upgrade-path, build and store-packaging checks after branding changes.
8. Verify existing users can update without losing account state, local state, memory, authentication or federation identity.
9. Produce a final branding consistency audit before the release candidate is declared ready.

## Fallback rename plan if JANUS 137 is rejected

If legal/name clearance identifies unacceptable risk:

- do not rewrite JANUS architectural history;
- choose a new distinctive public product name;
- keep a single configurable/display-brand source where practical so another rename does not require scattered edits;
- perform the same controlled public-brand migration described above;
- preserve package/application identifiers where possible to maintain update continuity;
- re-check OAuth/store/legal text under the replacement name before release.

## Trademark policy for release

A registered trade mark is **not required merely to publish the app**. The required release decision is whether the chosen public name can be used with an acceptable level of legal/confusion risk.

If the project has sufficient commercial value at release or shortly afterward, reassess whether to apply to register the combined mark **JANUS 137** in the relevant classes. Any filing/application should use the final cleared name and carefully scoped goods/services wording.

Do not use the registered-trade-mark symbol `®` unless the relevant mark is actually registered. `™` may be considered for an unregistered brand where appropriate.

## Relationship to the wider legal-release audit

Brand clearance is only one release gate. The final legal-release audit must also reconcile the actual application/server behavior with privacy policy, terms, AI disclosures, data handling/retention/deletion, account security, third-party licences/attribution, provider requirements, app-store policies and applicable Australian legal obligations.

Do not declare the product legally/release ready merely because CI is green or the name looks available in a casual search.

## Current instruction

For now:

- keep development branding/internal naming as JANUS;
- record **JANUS 137** as the preferred future public name;
- make no broad rename solely because of this plan;
- revisit this file during the legal-release audit;
- if clearance passes, apply the controlled public-facing rename before final release packaging;
- if clearance fails, use the fallback rename plan without disturbing the underlying JANUS architecture unnecessarily.
