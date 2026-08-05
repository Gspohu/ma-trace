#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON bridge for the web front. Reads a request on stdin, writes the plan on stdout"""

import contextlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli.engine import EXPECTED, handle_request


def _run(request):
    """Answer the request while nothing at all is allowed to reach the real stdout.

    The caller parses stdout as json, and a single stray print anywhere down the call
    stack would corrupt the answer. No library is trusted to stay quiet : stdout is
    swapped for a buffer, then forwarded to stderr once the trace is writen"""
    captured = io.StringIO()

    with contextlib.redirect_stdout(captured):
        result = handle_request(
            request, log=lambda message: print(message, file=sys.stderr))

    noise = captured.getvalue()
    if (noise):
        sys.stderr.write(noise)

    return result


def main():
    try:
        request = json.load(sys.stdin)
    except ValueError as exc:
        json.dump({"error": "requete illisible : %s" % exc}, sys.stdout)
        return 1  

    try:
        result = _run(request)
    except EXPECTED as exc:
        json.dump({"error": str(exc)}, sys.stdout)
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False)
    return 0


if (__name__ == "__main__"):
    raise SystemExit(main())
