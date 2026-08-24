from server_v2 import maintenance_channel


def test_boundary_has_no_source_or_execution_authority():
    status = maintenance_channel.boundary_status()
    assert status["storage_channel"] == "validated_server_database"
    assert status["source_repository_credentials_exposed_to_janus"] is False
    assert status["arbitrary_repository_read"] is False
    assert status["arbitrary_repository_write"] is False
    assert status["arbitrary_file_write"] is False
    assert status["shell_or_process_execution"] is False
    assert status["package_install"] is False
    assert status["configuration_mutation"] is False
    assert status["maintenance_self_approval"] is False
    assert status["self_deploy"] is False
    assert status["owner_supervisor_authorization_required"] is True


def test_channel_module_does_not_import_repo_or_process_clients():
    source = open("server_v2/maintenance_channel.py", encoding="utf-8").read().lower()
    forbidden = ("github", "subprocess", "os.system", "gitpython", "requests.", "httpx.", "pathlib")
    # 'GitHub' appears in the explanatory docstring; executable import/call patterns must not.
    executable = "\n".join(line for line in source.splitlines() if not line.strip().startswith(('"', "#")))
    assert "import github" not in executable
    assert "import subprocess" not in executable
    assert "os.system" not in executable
    assert "gitpython" not in executable
    assert "requests." not in executable
    assert "httpx." not in executable
    assert "from pathlib" not in executable
