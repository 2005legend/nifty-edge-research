import pytest

from quantdesk.power import ES_CONTINUOUS, ES_SYSTEM_REQUIRED, keep_awake


def test_keep_awake_holds_the_request_until_the_job_ends():
    calls = []
    with keep_awake(set_state=calls.append):
        assert calls == [ES_CONTINUOUS | ES_SYSTEM_REQUIRED]
    assert calls == [ES_CONTINUOUS | ES_SYSTEM_REQUIRED, ES_CONTINUOUS]


def test_keep_awake_releases_the_request_when_the_job_fails():
    calls = []
    with pytest.raises(RuntimeError):
        with keep_awake(set_state=calls.append):
            raise RuntimeError("feed died")
    assert calls[-1] == ES_CONTINUOUS
