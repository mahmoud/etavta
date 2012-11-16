from __future__ import unicode_literals

import os
from pprint import pformat

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect

import mako
from mako.lookup import TemplateLookup

from workles import WorklesBase, Route, DummyMiddleware
from schedule import Schedule, fm

def home():
    return Response('hi')


def get_stops(schedule, name_index, station_name):
    station_name = name_index[station_name]
    content = pformat(schedule.get_stops(station_name))
    return {'content': content}


def not_found(*a, **kw):
    raise NotFound()

def create_app(schedule_dir, template_dir, with_static=True):
    def mako_response(template_file):
        template_lookup = TemplateLookup(template_dir, format_exceptions=True)
        def render_mako_response(context_dict=None, **kw):
            context_dict = context_dict or {}
            context_dict.update(kw)

            tmpl = template_lookup.get_template(template_file)
            return Response(tmpl.render(**context_dict), mimetype='text/html')
        return render_mako_response

    routes = [Route('/', home, 'base.html'),
              Route('/<path:station_name>', get_stops, 'base.html'),
              Rule('/favicon.ico', endpoint=not_found)]

    app = WorklesBase(routes, {
        'schedule': Schedule.from_directory('raw_schedules'),
        'name_index': fm
    }, mako_response, [DummyMiddleware()])
    if with_static:
        app.__call__ = SharedDataMiddleware(app.__call__, {
            '/static':  os.path.join(os.path.dirname(__file__), 'static')
        })
    return app


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app('raw_schedules', './templates')
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
