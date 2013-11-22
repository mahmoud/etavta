from __future__ import unicode_literals

import sys
sys.path.insert(0, '../clastic')

from clastic import Application
from clastic.render.mako_templates import MakoRenderFactory
from clastic.middleware import SimpleContextProcessor
from clastic.middleware.profile import SimpleProfileMiddleware
from clastic.middleware.client_cache import HTTPCacheMiddleware
from clastic.errors import NotFound

from schedule import Schedule, fm, ALL_LEGS

from localtime import get_pacific_time
from fetch import RAW_SCHED_DIR, get_newest_sched_dir


def home(schedule):
    #return {'pre_content': pformat([s for s in schedule.stations])}
    return {}


def parse_date_params(start_date, start_time):
    from datetime import datetime
    now = datetime.now()
    sdate, stime = now.date(), now.time()
    if start_date:
        if len(start_date) % 2 == 1:
            start_date = '0' + start_date
        if len(start_date) == 4:
            sdate = sdate.replace(month=int(start_date[:2]),
                                  day=int(start_date[2:4]))
        elif len(start_date) == 8:
            sdate = sdate.replace(year=int(start_date[:4]),
                                  month=int(start_date[4:6]),
                                  day=int(start_date[6:8]))
    if start_time:
        pass

    return datetime.combine(sdate, stime)


def get_stops(schedule, name_index, station_name, sdate=None, stime=None):
    start_dt = parse_date_params(sdate, stime)
    start_dt = get_pacific_time(start_dt)
    station_name = name_index[station_name]
    stops = schedule.get_stops(station_name, start_dt)
    return {'stops': stops}


def create_app(schedule_dir, template_dir):
    schedule = Schedule.from_directory(schedule_dir)
    resources = {'schedule': schedule,
                 'name_index': fm,
                 'LEGS': ALL_LEGS}
    subroutes = [('/', home, 'station_list.html'),
                 ('/favicon.ico', lambda: NotFound()),
                 ('/<station_name>', get_stops, 'stop_times.html')]

    mako_factory = MakoRenderFactory(template_dir)
    cc_mw = HTTPCacheMiddleware(max_age=30, must_revalidate=True)
    middlewares = [SimpleProfileMiddleware(),
                   SimpleContextProcessor(LEGS=ALL_LEGS),
                   cc_mw]
    subapp = Application(subroutes, resources, mako_factory, middlewares)

    routes = [('/', subapp), ('/v2/', subapp)]
    app = Application(routes)
    return app


sched_path = get_newest_sched_dir(RAW_SCHED_DIR)
print 'loading schedules from %s...' % sched_path
if not sched_path:
    raise Exception('no schedules found')
application = create_app(sched_path, './templates')


if __name__ == '__main__':
    application.serve()
