import importlib
import sqlite3


def _module(tmp_path, monkeypatch):
    path=tmp_path/'janus.sqlite3'
    monkeypatch.setenv('JANUS_DB_PATH', str(path))
    import persistence_matrix as p
    importlib.reload(p)
    return p, path


def test_clean_install_allows_missing_tables(tmp_path, monkeypatch):
    p, path=_module(tmp_path, monkeypatch)
    out=p.preflight_existing()
    assert out['ok'] is True
    assert not out['incompatible']
    assert path.exists()


def test_incompatible_existing_critical_table_fails_before_writes(tmp_path, monkeypatch):
    p, path=_module(tmp_path, monkeypatch)
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE desktop_memory(id INTEGER PRIMARY KEY, profile_id TEXT)')
    try:
        p.preflight_existing()
        assert False, 'expected incompatible schema failure'
    except RuntimeError as exc:
        text=str(exc)
        assert 'refusing full startup before writes' in text
        assert 'desktop_memory' in text


def test_additive_extra_columns_are_restart_safe(tmp_path, monkeypatch):
    p, path=_module(tmp_path, monkeypatch)
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE desktop_memory(id INTEGER PRIMARY KEY AUTOINCREMENT,profile_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,level TEXT NOT NULL,created_at TEXT NOT NULL,future_column TEXT)')
        c.execute('CREATE TABLE desktop_events(id INTEGER PRIMARY KEY AUTOINCREMENT,profile_id TEXT NOT NULL,event_type TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL)')
    first=p.preflight_existing()
    assert first['ok']
    row=next(x for x in first['tables'] if x['table']=='desktop_memory')
    assert 'future_column' in row['extra_columns']
    p.record_current_matrix()
    second=p.preflight_existing()
    assert second['ok']
    status=p.status()
    assert status['meta']['persistence_matrix_version']['value']==str(p.MATRIX_VERSION)


def test_incompatible_optional_registered_table_also_fails_closed(tmp_path, monkeypatch):
    p, path=_module(tmp_path, monkeypatch)
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE janus_message_threads(event_id INTEGER PRIMARY KEY,profile_id TEXT)')
    try:
        p.preflight_existing()
        assert False, 'expected incompatible schema failure'
    except RuntimeError as exc:
        assert 'janus_message_threads' in str(exc)
