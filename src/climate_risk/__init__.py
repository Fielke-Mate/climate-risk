"""Physical climate risk (extreme heat) proof of concept."""

# pywbgt compiles pvlib's solar-position code with numba, which only works if it is
# the first to import pvlib.spa. Import it before anything else pulls in pvlib.
try:  # pragma: no cover - optional at import time
    import pywbgt  # noqa: F401
except ImportError:
    pass

__version__ = "0.1.0"
