from __future__ import unicode_literals

from werkzeug.exceptions import NotFound
from clastic import Application, Middleware
from clastic.render.mako_templates import MakoRenderFactory
from clastic.middleware import SimpleContextProcessor

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


def not_found(*a, **kw):
    raise NotFound()


class HTTPCacheMiddleware(Middleware):
    cache_attrs = ('max_age', 's_maxage', 'no_cache', 'no_store',
                   'no_transform', 'must_revalidate', 'proxy_revalidate',
                   'public', 'private')
    def __init__(self,
                 max_age=None,
                 s_maxage=None,
                 no_cache=None,
                 no_store=None,
                 no_transform=None,
                 must_revalidate=None,
                 proxy_revalidate=None,
                 public=None,
                 private=None,
                 use_etags=True):
        for attr in self.cache_attrs:
            setattr(self, attr, locals()[attr])
        self.use_etags = use_etags

    def request(self, next, request):
        resp = next()
        if hasattr(resp, 'cache_control'):
            for attr in self.cache_attrs:
                cache_val = getattr(self, attr, None)
                if cache_val:
                    setattr(resp.cache_control, attr, cache_val)
            if self.use_etags and not resp.is_streamed:
                # TODO: do streamed responses too?
                resp.add_etag()
                resp.make_conditional(request)
        return resp


from gzip import GzipFile
from StringIO import StringIO
def compress(data, level=6):
    out = StringIO()
    f = GzipFile(fileobj=out, mode='wb', compresslevel=level)
    f.write(data)
    f.close()
    return out.getvalue()


class GzipMiddleware(Middleware):
    def __init__(self, compress_level=6):
        self.compress_level = compress_level

    def request(self, next, request):
        resp = next()
        # TODO: shortcut redirects/304s/responses without content?
        resp.vary.add('Accept-Encoding')
        if resp.content_encoding or not request.accept_encodings['gzip']:
            return resp

        if 'msie' in request.user_agent.browser:
            if not (resp.content_type.startswith('text/') or
                    'javascript' in resp.content_type):
                return resp

        if resp.is_streamed:
            return resp  # TODO
        else:
            comp_content = compress(resp.data, self.compress_level)
            if len(comp_content) >= len(resp.data):
                return resp
            resp.response = [comp_content]
            resp.content_length = len(comp_content)

        resp.content_encoding = 'gzip'
        # TODO: regenerate etag?
        return resp


import cProfile
from pstats import Stats
from cStringIO import StringIO
import sys

_prof_tmpl = '<html><body><pre>%s</pre></body</html>'
_sort_keys = {'cumulative': 'cumulative time, i.e., includes time in called functions.',
              'file': 'source file',
              'line': 'line number',
              'name': 'function name',
              'module': 'source module',
              'nfl': 'name/file/line',
              'pcalls': 'primitive (non-recursive) calls',
              'stdname': 'standard name (includes path)',
              'time': 'internal time, i.e., time in this function scope'}


class ProfilerMiddleware(Middleware):
    def __init__(self, sort_param_name='_prof_sort', get_param_name='_prof'):
        self.get_param_name = get_param_name
        self.sort_param_name = sort_param_name

    def request(self, next, request):
        if not request.args.get(self.get_param_name):
            return next()
        sort_param = request.args.get(self.sort_param_name, 'time')
        if sort_param not in _sort_keys:
            raise KeyError('%s is not a supported sort_key. choose from: %r'
                           % (sort_param, _sort_keys))
        profiler = cProfile.Profile()
        try:
            ret = profiler.runcall(next)
        except:
            if self.raise_exc:
                raise
        buff = StringIO()
        stats = Stats(profiler, stream=buff).sort_stats(sort_param).print_stats()
        ret.response = [_prof_tmpl % buff.getvalue()]
        return ret


from clastic.exceptions import make_error_handler_map

err_handlers = make_error_handler_map()


def create_app(schedule_dir, template_dir):
    schedule = Schedule.from_directory(schedule_dir)
    resources = {'schedule': schedule,
                 'name_index': fm,
                 'LEGS': ALL_LEGS}
    subroutes = [('/', home, 'station_list.html'),
                 ('/<path:station_name>', get_stops, 'stop_times.html'),
                 ('/favicon.ico', not_found)]

    mako_response = MakoRenderFactory(template_dir)
    cc_mw = HTTPCacheMiddleware(max_age=30, must_revalidate=True)
    middlewares = [GzipMiddleware(), ProfilerMiddleware(), SimpleContextProcessor(LEGS=ALL_LEGS), cc_mw]
    subapp = Application(subroutes, resources, mako_response, middlewares,
                         error_handlers=err_handlers)

    routes = [('/', subapp), ('/v2/', subapp)]
    app = Application(routes, error_handlers=err_handlers)
    return app

sched_path = get_newest_sched_dir(RAW_SCHED_DIR)
if not sched_path:
    raise Exception('no schedules found')
application = create_app(sched_path, './templates')


if __name__ == '__main__':
    application.serve()
