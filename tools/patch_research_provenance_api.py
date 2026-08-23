from pathlib import Path

path = Path('bootstrap.py')
text = path.read_text(encoding='utf-8')

old_import = '    from maintenance_review import install as install_maintenance_review, status as maintenance_status, run_review as run_maintenance_review\n'
new_import = old_import + '    from research_provenance_api import router as research_provenance_router\n'
if 'from research_provenance_api import router as research_provenance_router' not in text:
    if old_import not in text:
        raise SystemExit('research provenance bootstrap import marker missing')
    text = text.replace(old_import, new_import, 1)

old_include = '    app.include_router(image_inline_router)\n'
new_include = old_include + '    app.include_router(research_provenance_router)\n'
if 'app.include_router(research_provenance_router)' not in text:
    if old_include not in text:
        raise SystemExit('research provenance bootstrap router marker missing')
    text = text.replace(old_include, new_include, 1)

marker = '            "quarterly_maintenance_review_enabled": bool(getattr(app.state, "janus_maintenance_review_installed", False)),\n'
addition = marker + '            "research_provenance_route_present": "/research-provenance/status" in routes,\n'
if 'research_provenance_route_present' not in text:
    pos = text.find('    @app.get("/diagnostics/auth-config")')
    end = text.find('    @app.get("/diagnostics/maintenance")', pos)
    block = text[pos:end]
    if marker not in block:
        raise SystemExit('research provenance diagnostics marker missing')
    block = block.replace(marker, addition, 1)
    text = text[:pos] + block + text[end:]

path.write_text(text, encoding='utf-8')
print('Applied research provenance API bootstrap patch')
