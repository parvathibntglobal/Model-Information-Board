"""E2 harvest — one adapter class per platform.

What differs between platforms is auth, rate limits, pagination and response
shape. None of that needs a language model, and none of it may make an
unidentified request: every adapter fetches through `collect.http.build_client`
and nothing else.
"""
