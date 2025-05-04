from .core import node
from .handlers import github


def register_handlers():
    print("Registering GITHUB handlers...")
    _ = github
