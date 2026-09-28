import time

from agent.cache_manager import CacheManager


def test_set_then_get_returns_data(tmp_path):
    cache = CacheManager(cache_dir=str(tmp_path), default_ttl=60)
    cache.set("k", {"team": "Real Madrid"})
    assert cache.get("k") == {"team": "Real Madrid"}


def test_entry_survives_restart_via_file_cache(tmp_path):
    CacheManager(cache_dir=str(tmp_path)).set("k", {"v": 1})
    fresh = CacheManager(cache_dir=str(tmp_path))  # empty memory cache
    assert fresh.get("k") == {"v": 1}


def test_expired_entry_is_a_miss(tmp_path, monkeypatch):
    cache = CacheManager(cache_dir=str(tmp_path), default_ttl=10)
    cache.set("k", {"v": 1})
    real_time = time.time()
    monkeypatch.setattr(time, "time", lambda: real_time + 11)
    assert cache.get("k") is None


def test_get_or_fetch_calls_fetcher_once(tmp_path):
    cache = CacheManager(cache_dir=str(tmp_path))
    calls = []

    def fetch(league):
        calls.append(league)
        return {"league": league}

    assert cache.get_or_fetch({"league": "PD"}, fetch) == {"league": "PD"}
    assert cache.get_or_fetch({"league": "PD"}, fetch) == {"league": "PD"}
    assert calls == ["PD"]


def test_errors_are_not_cached(tmp_path):
    cache = CacheManager(cache_dir=str(tmp_path))
    calls = []

    def fetch(q):
        calls.append(q)
        return {"error": "rate limited"}

    cache.get_or_fetch({"q": "x"}, fetch)
    cache.get_or_fetch({"q": "x"}, fetch)
    assert len(calls) == 2
