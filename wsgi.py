from __future__ import unicode_literals

import os
import sys

sys.path.insert(0, '../clastic')

from clastic import Application
from clastic.render.mako_templates import MakoRenderFactory
from clastic.middleware import (GetParamMiddleware,
                                SimpleContextProcessor)
from clastic.middleware.profile import SimpleProfileMiddleware
from clastic.middleware.client_cache import HTTPCacheMiddleware
from clastic.errors import NotFound

from schedule import Schedule, NAME_MATCHER, ALL_LEGS

from localtime import get_pacific_time
from fetch import RAW_SCHED_DIR, get_newest_sched_dir

CUR_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(CUR_DIR, 'templates')


def home(schedule):
    return {}


def parse_date_params(start_date, start_time):
    from datetime import datetime
    now = get_pacific_time()
    sdate, stime = now.date(), now.time()
    try:
        if len(start_date) % 2 == 1:
            start_date = '0' + start_date
        if len(start_date) == 4:
            sdate = sdate.replace(month=int(start_date[:2]),
                                  day=int(start_date[2:4]))
        elif len(start_date) == 8:
            sdate = sdate.replace(year=int(start_date[:4]),
                                  month=int(start_date[4:6]),
                                  day=int(start_date[6:8]))
    except (TypeError, ValueError):
        pass
    try:
        if len(start_time) % 2 == 1:
            start_time = '0' + start_time
        if len(start_time) == 4:
            stime = stime.replace(hour=int(start_time[:2]),
                                  minute=int(start_time[2:4]))
    except (TypeError, ValueError):
        pass
    return datetime.combine(sdate, stime)


def get_stops(schedule, name_index, station_name, sdate=None, stime=None):
    try:
        station_name = name_index[station_name]
    except KeyError:
        return NotFound(is_breaking=False)
    start_dt = parse_date_params(sdate, stime)
    start_dt = get_pacific_time(start_dt)
    stops = schedule.get_stops(station_name, start_dt)
    return {'station_name': station_name, 'stops': stops}


def create_app(schedule_dir, template_dir):
    schedule = Schedule.from_directory(schedule_dir)
    resources = {'schedule': schedule,
                 'name_index': NAME_MATCHER,
                 'LEGS': ALL_LEGS}
    subroutes = [('/', home, 'station_list.html'),
                 ('/favicon.ico', lambda: NotFound()),
                 ('/<station_name>', get_stops, 'stop_times.html')]

    mako_factory = MakoRenderFactory(template_dir)
    cc_mw = HTTPCacheMiddleware(max_age=30, must_revalidate=True)
    middlewares = [SimpleProfileMiddleware(),
                   GetParamMiddleware(['sdate', 'stime']),
                   SimpleContextProcessor(LEGS=ALL_LEGS),
                   cc_mw]
    app = Application(subroutes, resources, mako_factory, middlewares)

    #routes = [('/', app), ('/v2/', app)]
    #app = Application(routes)
    return app


sched_path = get_newest_sched_dir(RAW_SCHED_DIR)
print 'loading schedules from %s...' % sched_path
if not sched_path:
    raise Exception('no schedules found')


application = create_app(sched_path, TEMPLATE_DIR)


if __name__ == '__main__':
    application.serve()
