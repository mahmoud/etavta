from __future__ import unicode_literals

from pprint import pformat

from werkzeug.exceptions import NotFound
from clastic import Application, Middleware
from clastic.render.mako_templates import MakoRenderFactory

from schedule import Schedule, fm, ALL_LEGS

from localtime import get_pacific_time
from fetch import RAW_SCHED_DIR, get_newest_sched_dir


def home(schedule):
    #return {'pre_content': pformat([s for s in schedule.stations])}
    return {}


def get_stops(schedule, name_index, station_name, start_time=None):
    start_time = get_pacific_time(start_time)
    station_name = name_index[station_name]
    stops = schedule.get_stops(station_name, start_time)
    return {'stops': stops}


def not_found(*a, **kw):
    raise NotFound()


class ConstantsMiddleware(Middleware):
    def __init__(self, **kw):
        self.constants = kw

    def render(self, next, context):
        context.update(self.constants)
        return next()

CONSTANTS = {'LEGS': ALL_LEGS}


def create_app(schedule_dir, template_dir):
    schedule = Schedule.from_directory(schedule_dir)
    resources = {'schedule': schedule,
                 'name_index': fm}
    subroutes = [('/', home, 'station_list.html'),
                 ('/<path:station_name>', get_stops, 'stop_times.html'),
                 ('/favicon.ico', not_found)]
    mako_response = MakoRenderFactory(template_dir)
    middlewares = [ConstantsMiddleware(**CONSTANTS)]
    subapp = Application(subroutes, resources, mako_response, middlewares)

    routes = [('/', subapp), ('/v2/', subapp)]
    app = Application(routes)
    return app

sched_path = get_newest_sched_dir(RAW_SCHED_DIR)
if not sched_path:
    raise Exception('no schedules found')
application = create_app(sched_path, './templates')


if __name__ == '__main__':
    application.serve()
