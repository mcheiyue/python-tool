__all__ = ["AppContainer"]


def __getattr__(name):
    if name == "AppContainer":
        from .container import AppContainer

        return AppContainer
    raise AttributeError(name)
