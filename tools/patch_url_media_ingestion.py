from pathlib import Path
p=Path('bootstrap.py'); s=p.read_text(encoding='utf-8')
a='    from maintenance_review import install as install_maintenance_review, status as maintenance_status, run_review as run_maintenance_review\n'
if 'from url_media_ingest import install as install_url_media_ingest' not in s:
    if a not in s: raise SystemExit('bootstrap import anchor missing')
    s=s.replace(a,a+'    import curiosity_search as curiosity_search_module\n    from url_media_ingest import install as install_url_media_ingest\n',1)
b='    install_maintenance_review(app, janus_sleep_cycle)\n'
if 'install_url_media_ingest(app, curiosity_search_module)' not in s:
    if b not in s: raise SystemExit('bootstrap install anchor missing')
    s=s.replace(b,b+'    install_url_media_ingest(app, curiosity_search_module)\n',1)
# Runtime-health reports whether the bridge actually installed; it must not reference local auth-config variables.
runtime_anchor='            "quarterly_maintenance_review_enabled": bool(getattr(app.state, "janus_maintenance_review_installed", False)),\n'
if '"url_media_ingestion_enabled": bool(getattr(app.state, "janus_url_media_ingest", False))' not in s:
    if runtime_anchor not in s: raise SystemExit('runtime diagnostic anchor missing')
    s=s.replace(runtime_anchor,runtime_anchor+'            "url_media_ingestion_enabled": bool(getattr(app.state, "janus_url_media_ingest", False)),\n',1)
# Public auth-config already builds `routes`; expose the Step 1 routes there so deployment can be verified from a phone.
auth_anchor='            "image_inline_route_present": any(path.startswith("/images/{file_id}/inline") for path in routes),\n'
if '"research_capabilities_route_present": "/capabilities/research" in routes' not in s:
    if auth_anchor not in s: raise SystemExit('auth-config diagnostic anchor missing')
    s=s.replace(auth_anchor,auth_anchor+'            "research_capabilities_route_present": "/capabilities/research" in routes,\n            "url_media_ingestion_enabled": bool(getattr(app.state, "janus_url_media_ingest", False)),\n            "youtube_transcript_attempt_enabled": bool(getattr(app.state, "janus_url_media_ingest", False)),\n',1)
p.write_text(s,encoding='utf-8')
print('URL/media ingestion bootstrap installed with safe diagnostics')
