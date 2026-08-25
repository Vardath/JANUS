# CI no-self-mutation rule

Release, proof and diagnostic workflows must not commit generated status/proof files back to `main`.

Reason: concurrent workflows can race and produce false non-fast-forward failures, extra main commits and noisy email alerts. CI output belongs in workflow logs, summaries or artifacts. Repository status/checkpoint documents are updated intentionally during supervised maintenance/development work.
