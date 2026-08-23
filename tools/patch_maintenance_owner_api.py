from pathlib import Path

path = Path('bootstrap.py')
text = path.read_text(encoding='utf-8')

old_import = '    from maintenance_review import install as install_maintenance_review, status as maintenance_status, run_review as run_maintenance_review\n'
new_import = old_import + '    from maintenance_owner_api import router as maintenance_owner_router\n'
if 'from maintenance_owner_api import router as maintenance_owner_router' not in text:
    if old_import not in text:
        raise SystemExit('maintenance owner API bootstrap import pattern missing')
    text = text.replace(old_import, new_import, 1)

old_include = '    app.include_router(image_inline_router)\n'
new_include = old_include + '    app.include_router(maintenance_owner_router)\n'
if 'app.include_router(maintenance_owner_router)' not in text:
    if old_include not in text:
        raise SystemExit('maintenance owner API bootstrap router pattern missing')
    text = text.replace(old_include, new_include, 1)

old_diag = '            "quarterly_maintenance_review_enabled": bool(getattr(app.state, "janus_maintenance_review_installed", False)),\n'
new_diag = old_diag + '            "maintenance_owner_status_route_present": "/maintenance/status" in routes,\n            "maintenance_owner_decision_route_present": "/maintenance/reviews/{review_id}/decision" in routes,\n'
if 'maintenance_owner_status_route_present' not in text:
    # Only patch the auth-config dictionary occurrence where `routes` is in scope.
    pos = text.find('    @app.get("/diagnostics/auth-config")')
    if pos < 0:
        raise SystemExit('auth-config diagnostics block missing')
    end = text.find('    @app.get("/diagnostics/maintenance")', pos)
    block = text[pos:end]
    if old_diag not in block:
        raise SystemExit('maintenance diagnostics marker missing')
    block = block.replace(old_diag, new_diag, 1)
    text = text[:pos] + block + text[end:]

path.write_text(text, encoding='utf-8')
print('Applied owner maintenance API bootstrap patch')
