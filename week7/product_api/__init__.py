def create_app(config=None):
    from .factory import create_app as create_application

    return create_application(config)

__all__ = ["create_app"]
