import importlib
import asyncio


def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("JANUS_DB_PATH", str(tmp_path / "degrade.sqlite3"))
    monkeypatch.setenv("JANUS_COST_PROFILE_DAILY_USD", "0.10")
    monkeypatch.setenv("JANUS_COST_PROFILE_MONTHLY_USD", "1.00")
    monkeypatch.setenv("JANUS_COST_BACKGROUND_DAILY_USD", "0.03")
    monkeypatch.setenv("JANUS_COST_GLOBAL_DAILY_USD", "10.0")
    import cost_governor
    import cost_governor_hooks
    return importlib.reload(cost_governor), importlib.reload(cost_governor_hooks)


def test_repeated_provider_failures_do_not_exhaust_budget(tmp_path, monkeypatch):
    budget, hooks = fresh(tmp_path, monkeypatch)

    def boom(*args, **kwargs):
        raise TimeoutError("provider timed out")

    proxy = hooks._CallableProxy(boom)
    with budget.scope("alice", "background_web"):
        for _ in range(8):
            try:
                proxy(model="test")
            except TimeoutError:
                pass

    status = budget.status("alice")
    assert status["today_estimated_usd"] == 0
    assert len(status["recent_failures"]) == 8
    assert all(x["status"] == "timeout" for x in status["recent_failures"])
    assert budget.authorize("alice", "chat", 0.03)["allowed"] is True


def test_background_budget_denial_does_not_block_foreground_chat(tmp_path, monkeypatch):
    budget, hooks = fresh(tmp_path, monkeypatch)
    budget.record("alice", "background_web", estimated_usd=0.03)
    with budget.scope("alice", "background_model"):
        try:
            hooks._CallableProxy(lambda: "unused")()
            assert False, "background call should be denied"
        except hooks.BudgetDenied:
            pass
    assert budget.authorize("alice", "chat", 0.03)["allowed"] is True


def test_malformed_provider_failure_is_recorded_without_charge(tmp_path, monkeypatch):
    budget, hooks = fresh(tmp_path, monkeypatch)

    def malformed(*args, **kwargs):
        raise ValueError("invalid response payload")

    with budget.scope("alice", "foreground_core"):
        try:
            hooks._CallableProxy(malformed)(model="test")
        except ValueError:
            pass

    status = budget.status("alice")
    assert status["today_estimated_usd"] == 0
    assert status["recent_failures"][0]["status"] == "malformed"
    assert "ValueError" in status["recent_failures"][0]["detail"]


def test_async_timeout_has_same_non_cascading_behavior(tmp_path, monkeypatch):
    budget, hooks = fresh(tmp_path, monkeypatch)

    async def boom(*args, **kwargs):
        raise TimeoutError("async provider timeout")

    async def run():
        with budget.scope("alice", "image"):
            try:
                await hooks._AsyncCallableProxy(boom)(model="image-test")
            except TimeoutError:
                pass

    asyncio.run(run())
    status = budget.status("alice")
    assert status["today_estimated_usd"] == 0
    assert status["recent_failures"][0]["status"] == "timeout"
