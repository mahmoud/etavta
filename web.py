from __future__ import unicode_literals

import os
from pprint import pformat

from werkzeug.exceptions import NotFound
from werkzeug.wsgi import SharedDataMiddleware
from clastic import Application
from clastic.render.mako_templates import MakoRenderFactory

from schedule import Schedule, fm

def home():
    return {'content': 'hi'}


def get_stops(schedule, name_index, station_name):
    station_name = name_index[station_name]
    content = pformat(schedule.get_stops(station_name))
    return {'content': content}


def not_found(*a, **kw):
    raise NotFound()


def create_app(schedule_dir, template_dir, with_static=True):
    schedule = Schedule.from_directory(schedule_dir)
    subroutes = [('/', home, 'base.html'),
                 ('/<path:station_name>', get_stops, 'base.html'),
                 ('/favicon.ico', not_found)]
    mako_response = MakoRenderFactory(template_dir)
    subapp = Application(subroutes, {
        'schedule': schedule,
        'name_index': fm
    }, mako_response)

    routes = [('/', subapp), ('/v2/', subapp)]
    app = Application(routes)
    if with_static:
        app.__call__ = SharedDataMiddleware(app.__call__, {
            '/static':  os.path.join(os.path.dirname(__file__), 'static')
        })
    return app


if __name__ == '__main__':
    app = create_app('raw_schedules', './templates')
    app.serve()
