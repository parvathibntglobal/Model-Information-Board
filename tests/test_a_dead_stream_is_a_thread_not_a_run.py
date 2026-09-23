"""A connection that dies mid-stream costs the thread, not the batch (#397).

Found by @anoojntglobal-sudo on run 3 of the e5.5 batch (#427), 2026-09-23:

    -- E5  Extract ------------------------------- error  13:00:16
        peer closed connection without sending complete message body
        (incomplete chunked read)

      RUN ERROR   1 stage(s) errored and the run did not complete: E5

Thread 14 of 23. Ten threads unread, and E5b, E5c, E5d, E6 and E7 never ran.

⚠ THAT IS #397's ORIGINAL DEFECT ARRIVING THROUGH A DOOR #399's FIX DID NOT
  COVER. The retry loop catches `ExtractorUnavailable`, and the taxonomy behind
  it classifies exceptions WE raise — three sites, all in `client.py`. This one
  is httpx's own `RemoteProtocolError`, raised inside `response.iter_lines()`,
  and `judge/` caught no httpx exception anywhere. So it walked out past
  `except ExtractorUnavailable` and ended the run.

⚠ CAUGHT, NOT CLASSIFIED — and the distinction is the whole point of the reply
  that reported it. Whether this should be RETRIED is genuinely open:

      a connection dying mid-stream     reads as "a bad minute"     -> retry
      the 300s timeout, deliberately    the call was working        -> no retry
                                        slowly, and a retry re-pays

  It is the second shape wearing the first's clothes, and one instance cannot
  tell them apart. What would is how far through the response it died, which
  nothing records. So `transient` takes its default of False: the thread is
  lost, the batch survives, and the thread is never written to the extraction
  ledger — so the next ordinary run reads it again.

  Not retrying costs one thread on one run. Not catching cost ten.
"""

from __future__ import annotations

import pathlib

import pytest

from judge.extract.client import ExtractorUnavailable, _stream_died, _stream_lines

CLIENT = pathlib.Path(__file__).resolve().parents[1] / "judge" / "extract" / "client.py"


class _DeadAfter:
    """A response whose stream stops part-way, as httpx's does."""

    def __init__(self, lines, exc):
        self._lines, self._exc = lines, exc

    def iter_lines(self):
        yield from self._lines
        raise self._exc


class TestTheDeadStreamBecomesOurOwnFailure:
    @pytest.mark.parametrize("cls", _stream_died())
    def test_every_guarded_class_is_converted(self, cls):
        """All four arrive at the same place for the same reason. Classifying
        only the one we have seen is how the next one escapes too."""
        stream = _DeadAfter(["a", "b"], cls("peer closed connection"))
        with pytest.raises(ExtractorUnavailable):
            list(_stream_lines(stream, chars_so_far=lambda: 0))

    def test_it_is_not_retried_by_default(self):
        """⚠ THE OPEN QUESTION IS LEFT OPEN. `transient` is False unless a
        raise site asks otherwise, which is the default @anoojntglobal-sudo
        argued me into on #399: failing toward not-spending is right when the
        cost of being wrong is money."""
        stream = _DeadAfter([], _stream_died()[0]("gone"))
        with pytest.raises(ExtractorUnavailable) as caught:
            list(_stream_lines(stream, chars_so_far=lambda: 0))
        assert caught.value.transient is False

    def test_the_message_says_how_much_had_arrived(self):
        """The number that would eventually separate "a bad minute" from "we
        lost the tail of a working call" — recorded now so the classification
        has something to be made from later."""
        stream = _DeadAfter(["x"], _stream_died()[0]("gone"))
        with pytest.raises(ExtractorUnavailable) as caught:
            list(_stream_lines(stream, chars_so_far=lambda: 8412))
        assert "8412 chars" in str(caught.value)

    def test_a_healthy_stream_is_untouched(self):
        stream = _DeadAfter(["one", "two"], None)
        stream.iter_lines = lambda: iter(["one", "two"])
        assert list(_stream_lines(stream, chars_so_far=lambda: 0)) == ["one", "two"]


class TestTheGuardIsWhereTheExceptionArrives:
    def test_it_wraps_the_yield_rather_than_the_call(self):
        """⚠ MY FIRST VERSION WRAPPED THE CALL AND CAUGHT NOTHING. A generator
        raises where it is CONSUMED: `iter_lines()` returns immediately and the
        socket dies later, inside the caller's `for`. A `try` around the call
        site is a guard around the wrong instant."""
        src = CLIENT.read_text(encoding="utf-8")
        body = src[src.index("def _stream_lines("):]
        body = body[:body.index("\nclass ")]
        assert "yield from response.iter_lines()" in body
        assert "except _stream_died() as exc:" in body

    def test_the_caller_passes_a_callable_for_the_count(self):
        """The count is only meaningful at the moment of failure, which is
        after this function has returned its generator."""
        src = CLIENT.read_text(encoding="utf-8")
        assert "chars_so_far=lambda: sum(len(f) for f in fragments)" in src


class TestItDoesNotSwallowWhatIsAlreadyClassified:
    def test_httpx_status_errors_are_not_caught_here(self):
        """⚠ NOT `httpx.HTTPError`, WHICH WOULD TAKE TOO MUCH. That base class
        also covers `HTTPStatusError`, and a status is already classified above
        with the code that produced it — 429 and the 5xx family retried, 4xx
        not. A broad catch would replace a precise classification with a vague
        one."""
        import httpx

        assert httpx.HTTPStatusError not in _stream_died()
        assert httpx.HTTPError not in _stream_died()

    def test_our_own_exception_passes_through(self):
        """The 300s deadline raises `ExtractorUnavailable` from inside the same
        loop. Catching httpx only is what lets it past untouched."""
        stream = _DeadAfter([], ExtractorUnavailable("still sending after 300s"))
        with pytest.raises(ExtractorUnavailable) as caught:
            list(_stream_lines(stream, chars_so_far=lambda: 0))
        assert "still sending" in str(caught.value)

    def test_httpx_is_still_imported_lazily(self):
        """The module deliberately has no top-level `import httpx`, and a
        module-level tuple of its exception classes would reintroduce one."""
        src = CLIENT.read_text(encoding="utf-8")
        head = src[:src.index("def _stream_died")]
        assert "\nimport httpx" not in head
