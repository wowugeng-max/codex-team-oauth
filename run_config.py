import os


def get_run_count(env=None):
    env = os.environ if env is None else env
    raw_value = str(env.get("RUN_COUNT", "") or "").strip()
    if not raw_value:
        return 1

    try:
        run_count = int(raw_value, 10)
    except ValueError as exc:
        raise ValueError("RUN_COUNT must be a positive integer") from exc

    if run_count < 1:
        raise ValueError("RUN_COUNT must be a positive integer")
    return run_count
