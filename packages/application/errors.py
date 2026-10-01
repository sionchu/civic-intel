class ConcurrentWrite(RuntimeError):
    """Infrastructure signals a transaction collision without leaking connection details."""
