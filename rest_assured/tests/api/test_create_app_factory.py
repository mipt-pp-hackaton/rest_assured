from rest_assured.src.main import create_app


def test_create_app_returns_new_instance_each_time():
    a = create_app()
    b = create_app()
    assert a is not b


def test_no_module_level_listener_singleton():
    import rest_assured.src.main as main_mod
    # listener должен быть инстанцирован только внутри create_app(), не на module-level
    assert not hasattr(main_mod, "listener") or callable(getattr(main_mod, "listener", None))


def test_no_module_level_runner_singleton():
    import rest_assured.src.main as main_mod
    sr = getattr(main_mod, "scheduler_runner", None)
    assert sr is None or callable(sr)
