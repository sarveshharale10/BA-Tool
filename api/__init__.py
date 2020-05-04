from flask import Blueprint

api = Blueprint(
    name='api',
    url_prefix='/api',
    import_name=__name__
)

from . import routes
