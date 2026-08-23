from pathlib import Path

path = Path('bootstrap.py')
text = path.read_text(encoding='utf-8')

old_import = '    from maintenance_review import install as install_maintenance_review, status as maintenance_status, run_review as run_maintenance_review\n'
new_import = old_import + '    from protocol_capabilities import router as protocol_capabilities_router\n'
if 'from protocol_capabilities import router as protocol_capabilities_router' not in text:
    if old_import not in text:
        raise SystemExit('protocol capability bootstrap import pattern missing')
    text = text.replace(old_import, new_import, 1)

old_include = '    app.include_router(image_inline_router)\n'
new_include = old_include + '    app.include_router(protocol_capabilities_router)\n'
if 'app.include_router(protocol_capabilities_router)' not in text:
    if old_include not in text:
        raise SystemExit('protocol capability bootstrap router pattern missing')
    text = text.replace(old_include, new_include, 1)

path.write_text(text, encoding='utf-8')
print('Applied protocol capability bootstrap patch')
