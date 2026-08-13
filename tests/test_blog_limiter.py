"""Per-host politeness, measured rather than waited for.

The clock and the sleep are injected, so these tests check the arithmetic in
milliseconds. A limiter tested with real sleeps gets tested with
`min_interval=0` instead, which is a different code path.
"""

from __future__ import annotations

from collect.adapters.blog.limiter import HostLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def limiter(clock: Clock, **kwargs) -> HostLimiter:
    return HostLimiter(clock=clock, sleeper=clock.sleep, **kwargs)


def test_first_request_to_a_host_does_not_wait():
    clock = Clock()
    assert limiter(clock).wait("https://a.example.invalid/x") == 0.0
    assert clock.slept == []


def test_second_request_waits_the_remainder():
    clock = Clock()
    limit = limiter(clock, min_interval=1.0)
    limit.wait("https://a.example.invalid/one")
    clock.now += 0.25
    waited = limit.wait("https://a.example.invalid/two")
    assert round(waited, 6) == 0.75
    assert [round(s, 6) for s in clock.slept] == [0.75]


def test_no_wait_once_the_interval_has_already_passed():
    clock = Clock()
    limit = limiter(clock, min_interval=1.0)
    limit.wait("https://a.example.invalid/one")
    clock.now += 5.0
    assert limit.wait("https://a.example.invalid/two") == 0.0


def test_hosts_are_independent():
    """Forty feeds on forty hosts must not serialise behind each other."""
    clock = Clock()
    limit = limiter(clock, min_interval=1.0)
    limit.wait("https://a.example.invalid/x")
    assert limit.wait("https://b.example.invalid/x") == 0.0
    assert clock.slept == []


def test_two_feeds_on_one_host_share_its_budget():
    clock = Clock()
    limit = limiter(clock, min_interval=1.0)
    limit.wait("https://a.example.invalid/feed-one.xml")
    waited = limit.wait("https://a.example.invalid/feed-two.xml")
    assert round(waited, 6) == 1.0


def test_a_crawl_delay_widens_the_interval_for_that_request():
    clock = Clock()
    limit = limiter(clock, min_interval=1.0)
    limit.wait("https://slow.example.invalid/x")
    waited = limit.wait("https://slow.example.invalid/y", min_interval=5.0)
    assert round(waited, 6) == 5.0


def test_a_shorter_crawl_delay_never_narrows_our_floor():
    """Their robots.txt is permission to go slower, not an instruction to speed up."""
    clock = Clock()
    limit = limiter(clock, min_interval=1.0)
    limit.wait("https://quick.example.invalid/x")
    waited = limit.wait("https://quick.example.invalid/y", min_interval=0.1)
    assert round(waited, 6) == 1.0


def test_the_interval_is_measured_from_request_start():
    """A slow response must not shorten the gap to the next request."""
    clock = Clock()
    limit = limiter(clock, min_interval=1.0)
    limit.wait("https://a.example.invalid/one")
    clock.now += 0.4  # the response took 0.4s
    waited = limit.wait("https://a.example.invalid/two")
    assert round(waited, 6) == 0.6
