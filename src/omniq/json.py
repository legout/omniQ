import msgspec


def dump(obj, fp):
    """Write obj as JSON to a file-like object using msgspec."""
    # Must be opened in binary mode
    if "b" not in getattr(fp, "mode", "b"):
        raise ValueError("File must be opened in binary mode for dump")
    fp.write(msgspec.json.encode(obj))


def load(fp):
    """Read JSON from a file-like object using msgspec."""
    # Must be opened in binary mode
    if "b" not in getattr(fp, "mode", "b"):
        raise ValueError("File must be opened in binary mode for load")
    return msgspec.json.decode(fp.read())


def dumps(obj):
    """Return JSON string for obj using msgspec."""
    return msgspec.json.encode(obj).decode("utf-8")


def loads(s):
    """Parse JSON string using msgspec."""
    if isinstance(s, str):
        s = s.encode("utf-8")
    return msgspec.json.decode(s)
