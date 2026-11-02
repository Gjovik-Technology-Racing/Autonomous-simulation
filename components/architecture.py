"""Safe architecture directory resolution."""
import re
from pathlib import Path

NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]*$')


def architecture_path(root, name):
    parts = name.split('/') if isinstance(name, str) else []
    if len(parts) != 2 or not all(NAME.fullmatch(p) for p in parts):
        raise ValueError('Architecture must be family/implementation')
    base = (Path(root) / 'architectures').resolve()
    path = (base / parts[0] / parts[1]).resolve()
    if not path.is_relative_to(base):
        raise ValueError('Architecture path escapes architectures directory')
    return path

