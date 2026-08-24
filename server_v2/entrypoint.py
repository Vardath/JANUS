"""Production entrypoint for the clean JANUS server reconstruction."""
from . import storage
from .migrate import migrate_persistent_data_once

storage.init_schema()
MIGRATION_RESULT = migrate_persistent_data_once()

from .app import app  # noqa: E402

app.state.server_generation = "v2-clean-reconstruction"
app.state.persistence_migration = MIGRATION_RESULT
