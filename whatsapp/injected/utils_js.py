"""
Loads the injected Utils.js content.
Mirrors src/util/Injected/Utils.js (sets up window.WWebJS).

Strategy: Extract just the function body from the CommonJS export and
wrap it as an IIFE so page.evaluate() can run it directly.
"""
from pathlib import Path
import re

_HERE = Path(__file__).parent


def _load_utils_js() -> str:
    src = (_HERE / "_utils_source.js").read_text(encoding="utf-8")

    # Remove CommonJS strict mode declaration
    src = src.replace("'use strict';\n", "", 1)

    # The file structure is:
    #   exports.LoadUtils = () => {
    #       ... body ...
    #   };
    # We extract the body and wrap as IIFE:
    #   (function() {
    #       ... body ...
    #   })();

    # Find start of function body (first { after exports.LoadUtils)
    match = re.search(r'exports\.LoadUtils\s*=\s*\(\)\s*=>\s*\{', src)
    if not match:
        raise RuntimeError("Could not locate LoadUtils in _utils_source.js")

    body_start = match.end()  # index of char AFTER the opening {

    # Find the matching closing }; at the end
    # The file ends with };\n so just strip from the last }; backwards
    body_end = src.rstrip().rfind("};")
    if body_end == -1:
        raise RuntimeError("Could not find closing }; in _utils_source.js")

    body = src[body_start:body_end]

    return f"(function() {{{body}}})();"


LOAD_UTILS_JS = _load_utils_js()
