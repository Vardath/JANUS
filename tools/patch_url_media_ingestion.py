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
p.write_text(s,encoding='utf-8'); print('URL/media ingestion bootstrap installed')
