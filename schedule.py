from __future__ import unicode_literals
from collections import namedtuple, defaultdict, OrderedDict, Iterable
from itertools import chain
from OrderedSet import OrderedSet
import datetime as dt
import re
import os
import warnings


NORTH = 'North'
SOUTH = 'South'

_MIDDLE_LEG = ['Tasman', 'River Oaks', 'Orchard', 'Bonaventura',
               'Component', 'Karina', 'Metro/Airport', 'Gish',
               'Civic Center', 'Japantown/Ayer', 'St. James', 'Santa Clara',
               'Paseo de San Antonio', 'San Jose Convention Center']

_MTNVIEW_LEG = ['Mountain View', 'Evelyn', 'Whisman', 'Middlefield',
                'Bayshore/NASA', 'Moffett Park', 'Lockheed Martin', 'Borregas',
                'Crossman', 'Fair Oaks', 'Vienna', 'Reamwood',
                'Old Ironsides', 'Great America', 'Lick Mill', 'Champion',
                'Tasman']

_WINCHESTER_LEG = ['San Jose Convention Center', 'San Fernando',
                   'San Jose Diridon', 'Race', 'Fruitdale',
                   'Bascom', 'Hamilton', 'Downtown Campbell',
                   'Winchester']

_ALUMROCK_LEG = ['Alum Rock', 'McKee', 'Penitencia Creek', 'Berryessa',
                 'Hostetter', 'Cropley', 'Montague', 'Great Mall',
                 'I-880/Milpitas', 'Cisco Way', 'Baypointe', 'Tasman']

_SNTTERESA_LEG = ['San Jose Convention Center', "Children's Discovery Museum",
                  'Virginia', 'Tamien', 'Curtner', 'Capitol',
                  'Branham', 'Ohlone/Chynoweth', 'Blossom Hill',
                  'Snell', 'Cottle', 'Santa Teresa']

_ALMADEN_LEG = ['Ohlone/Chynoweth', 'Oakridge', 'Almaden']

ALL_LEGS = (_MTNVIEW_LEG, _ALUMROCK_LEG, _MIDDLE_LEG,
            _WINCHESTER_LEG, _SNTTERESA_LEG, _ALMADEN_LEG)
ALL_STATIONS = OrderedSet(chain.from_iterable([_MTNVIEW_LEG, _ALUMROCK_LEG,
                                               _MIDDLE_LEG, _WINCHESTER_LEG,
                                               _SNTTERESA_LEG, _ALMADEN_LEG]))
EXPRESS_NONSTOP_STATIONS = ["Children's Discovery Museum", 'Virginia',
                            'Tamien', 'Curtner', 'Capitol', 'Branham']


_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def punct_split_lower(text):
    return [w for w in _punct_re.split(text.lower()) if w]

def slugify(text, delim='_'):
    return unicode(delim.join(punct_split_lower(text)))

class FuzzyMatcher(object):
    def __init__(self, candidates):
        candidates = list(candidates)
        self.candidates = candidates
        cand_tokens = [punct_split_lower(c) for c in candidates]
        token_map = defaultdict(set)
        for cand, t_list in zip(candidates, cand_tokens):
            for i in range(len(t_list) + 1):
                for j in range(i):
                    cur_token = ''.join(t_list[j:i])
                    if cur_token:
                        token_map[cur_token].add(cand)

        full_prefix_map = defaultdict(set)
        for pref, matches in token_map.items():
            for i in range(len(pref)):
                full_prefix_map[pref[:i + 1]].update(matches)

        self.full_prefix_map = dict(full_prefix_map)
        self.token_map = dict(token_map)
        self.unique_prefix_map = dict([(p, list(cnd)[0]) for p, cnd
                                       in full_prefix_map.items() if len(cnd) == 1])
        self.unique_token_map = dict([(ct, list(cnd)[0]) for ct, cnd
                                      in token_map.items() if len(cnd) == 1])

    def __getitem__(self, in_str):
        if not in_str:
            raise KeyError('FuzzyMatcher expected non-empty unicode string.')
        in_slug = slugify(in_str, '')
        match = self.full_prefix_map[in_slug]
        if len(match) == 1:
            return list(match)[0]
        else:
            raise KeyError('multiple matching values for ' + str(in_str))

    def find(self, in_str):
        if not in_str:
            raise KeyError('FuzzyMatcher expected non-empty unicode string.')
        in_slug = slugify(in_str, '')
        return list(self.full_prefix_map.get(in_slug, []))

    def extended_find(self, in_str):
        ret = []
        tokens = punct_split_lower(in_str)
        for i, t in enumerate(tokens):
            search_str = ''.join(tokens[:i + 1])
            ret = self.full_prefix_map.get(search_str, [])
            if len(ret) == 1:
                break
        return list(ret)


fm = FuzzyMatcher(ALL_STATIONS)


def get_interstitial_stations(s1, s2):
    for leg in ALL_LEGS:
        if s1 in leg and s2 in leg:
            s1_i, s2_i = leg.index(s1), leg.index(s2)
            if s1_i < s2_i:
                return leg[s1_i + 1:s2_i]
            else:
                return leg[s1_i - 1:s2_i:-1]  # reverse order
            break
    else:
        raise ValueError('could not find interstitial stations for ' +
                         s1 + ' and ' + s2 + '.')


def split_list(src, key=None, maxsplit=None):
    """
    Splits a list based on a separator, iterable of separators, or
    function that evaluates to True when a separator is encountered.

    Frankly, this feature should be part of the list builtin.

    TODO: This works with iterators but could itself be an generator.
    """
    if maxsplit is not None:
        maxsplit = int(maxsplit)
        if maxsplit == 0:
            return [src]

    if callable(key):
        key_func = key
    elif isinstance(key, Iterable) and not isinstance(key, basestring):
        key = set(key)
        key_func = lambda x: x in key
    else:
        key_func = lambda x: x == key

    ret = []
    cur_list = []
    for s in src:
        if key_func(s):
            ret.append(cur_list)
            cur_list = []
            if maxsplit is not None and len(ret) >= maxsplit:
                key_func = lambda x: False
        else:
            cur_list.append(s)
    ret.append(cur_list)

    if key is None:
        # If sep is none, str.split() "groups" separators, check the docs
        return [x for x in ret if x]
    else:
        return ret


SourceInfo = namedtuple('SourceInfo', 'filename, line')


class Station(unicode):
    pass


class Route(object):
    def __init__(self, name, direction, day, stations=None):
        self.name = name
        self.direction = direction
        self.day = day
        self.stations = tuple(stations)

    def __repr__(self):
        tmpl = "Route('{}', '{}', '{}')"
        return tmpl.format(self.name,
                           self.direction,
                           self.day)


def parse_stop_time(time_str):
    time_str = time_str.strip()
    if not time_str:
        return None
    time_obj = dt.datetime.strptime(time_str + 'M', '%I:%M%p')
    time_delt = dt.timedelta(hours=time_obj.hour, minutes=time_obj.minute)
    return time_delt


def get_route_day_name(day_num):
    "Python datetime.weekday() format. 0-6, 0=Monday, 6=Sunday"
    if 0 <= day_num < 5:
        return 'Weekday'
    elif day_num == 5:
        return 'Saturday'
    elif day_num == 6:
        return 'Sunday'
    else:
        raise ValueError('Unrecognized day number: ' + repr(day_num))


class Schedule(object):
    def __init__(self, timetables):
        self.timetables = list(timetables)
        self.routes = [ t.route for t in timetables ]
        self.stations = set(chain.from_iterable([r.stations for r in self.routes]))

        day_dict = {}
        for t in timetables:
            r = t.route
            day_dict.setdefault(r.day, []).append(t.trains)

        stop_sigs = {}

        station_sets = defaultdict(set)
        week_trains = []
        one_week = dt.timedelta(days=7)
        for i in range(7):
            day_name = get_route_day_name(i)
            day_trains = list(chain.from_iterable(day_dict[day_name]))
            if not day_trains:
                warnings.warn('No trains found for '+str(day_name)+'.')
                continue # DEBUG (?)

            offset = dt.timedelta(days=i)
            for j, train in enumerate(day_trains):
                offset_train = train.offset_copy(offset)
                for stop in offset_train.stops:
                    if stop.stop_time >= one_week:
                        stop.stop_time -= one_week
                    station_sets[stop.station].add(offset_train)

                    stop_sig = (train.route.day,
                                train.route.name,
                                train.route.direction,
                                stop.station,
                                stop.stop_time)
                    if stop_sig in stop_sigs:
                        print stop_sigs[stop_sig], j, stop_sig, train.stops[0], train.stops[-1], len(week_trains)
                        raise Exception('Duplicate stops detected at the same location at the same time.')
                    else:
                        stop_sigs[stop_sig] = j

                week_trains.append(offset_train)

        station_dict = {}
        for stn, trains in station_sets.items():
            station_dict[stn] = sorted(trains, key=lambda x, s=stn: x[s].stop_time)

        self._unsorted_trains = week_trains
        self.all_trains = sorted(week_trains, key=lambda t: t.stops[0].stop_time)
        self.station_dict = station_dict

    @classmethod
    def from_directory(cls, path, ext='.tdl'):
        filenames = [ fn for fn in os.listdir(path)
                      if not fn.startswith('.') and (not ext or fn.endswith(ext)) ]
        route_dict = defaultdict(list)
        for fn in filenames:
            tt = Timetable.from_file(os.path.join(path, fn))
            r = tt.route
            route_dict[(r.name,r.direction,r.day)].append(tt)

        multi_routes = [ (r_desc, [tt.filename for tt in tts])
                         for r_desc, tts in route_dict.items()
                         if len(tts) > 1 ]
        if multi_routes:
            warnings.warn('Duplicate definitions detected: '+repr(multi_routes))

        timetables = [rd[0] for rd in route_dict.values()]
        return cls(timetables)

    def get_stops(self, station, start_time=None, count=5):
        if start_time is None:
            start_time = dt.datetime.now()
        start_td = dt.timedelta(days=start_time.weekday(),
                                hours=start_time.hour,
                                minutes=start_time.minute)
        ret = {}
        for direction in (NORTH, SOUTH):
            ret[direction] = [ ConcreteStop(t, t[station], start_time)
                               for t in self.station_dict[station]
                               if t[station].stop_time > start_td
                               and t.route.direction == direction ][:count]
        return ret


class Timetable(object):
    def __init__(self, route, trains, filename=None):
        self.route = route
        self.trains = trains
        self.filename = filename

    @classmethod
    def from_file(cls, filename):
        with open(filename, 'r') as f:
            return cls.from_string(f.read(), filename)

    @classmethod
    def from_string(cls, in_str, filename=None):
        stations = []
        in_str = in_str.decode()  # TODO
        lines = [ x for x in in_str.split('\n') ]
        pos = 0

        route_num, direction, day = [x.strip() for x in lines[pos].split(' - ')]
        route_num = route_num.split()[-1]
        pos += 1

        short_map = OrderedDict()
        for line in lines[pos:]:
            pos += 1
            if not line:
                break  # eat blank line separating station names from timetable
            s_name, _, f_name = [n.strip() for n in line.partition('\t')]
            if not s_name.startswith('LVE'):
                station_names = fm.extended_find(f_name.strip())
                if not station_names or len(station_names) > 1:
                    raise ValueError('Could not find station with name: ' +
                                     f_name.strip())
                short_map[s_name.strip()] = Station(station_names[0])
        stations = []
        for s1, s2 in zip(short_map.values(), short_map.values()[1:]):
            stations.append(s1)
            i_stations = get_interstitial_stations(s1, s2)
            stations.extend([Station(new_s) for new_s in i_stations])

        stations.append(s2)
        route = Route(route_num, direction, day, stations)

        short_names = [x.strip() for x in lines[pos].split('\t') if x]
        pos += 1
        assert short_map.keys() == [x for x in short_names if not x.startswith('LVE')]

        trains = []
        for line in lines[pos:]:
            pos += 1
            if not line:
                break  # and we're done
            cur_known_stops = []
            cur_stop = None
            stop_times = [parse_stop_time(x) for x in line.split('\t')][:len(short_names)]
            assert any(stop_times)
            src_info = SourceInfo(filename, pos)
            for i, stop_time in enumerate(stop_times):
                cur_short_name = short_names[i]
                if not stop_time:
                    continue
                elif cur_stop and cur_short_name.startswith('LVE'):
                    cur_stop.leave_time = stop_time
                    continue
                else:
                    cur_station = short_map[cur_short_name]
                    cur_stop = Stop(cur_station, stop_time, source=src_info)
                    cur_known_stops.append(cur_stop)
            t = Train.from_known_stops(route, cur_known_stops, source=src_info)
            trains.append(t)

        first_stop_time = trains[0].stops[0].stop_time
        one_day = dt.timedelta(days=1)
        for train in trains:
            for stop in train.stops:
                if stop.stop_time < first_stop_time:
                    stop.stop_time += one_day

        sched = cls(route, trains, filename)
        return sched


def interpolate_stops(known_stops, stations):
    "Known stops are currently expected to be in order (and other constraints, blargh)."
    ret = []
    ks1, ks2 = None, None
    for ks1, ks2 in zip(known_stops, known_stops[1:]):
        ret.append(ks1)

        ks1_i = stations.index(ks1.station)
        ks2_i = stations.index(ks2.station)
        inters = [ stn for stn in stations[ks1_i+1:ks2_i] ]
        time_d = ks2.stop_time - ks1.leave_time
        time_per = time_d / (len(inters) + 1)

        i_stops = [Stop(stn, ks1.leave_time + (time_per*(i+1)) )
                   for i, stn in enumerate(inters)]
        ret.extend(i_stops)
    ret.append(ks2)

    if stations[0] != ret[0].station:
        print 'first stop station mismatch:'
        print stations[0], ret[0].station
    if stations[-1] != ret[-1].station:
        # semi-hack for cases like Gish terminus
        uk_i = stations.index(ret[-1].station) + 1
        delta = ret[-1].stop_time - ret[-2].leave_time
        for i in range(uk_i, len(stations)):
            new_stop_time = ret[-1].leave_time + delta
            ret.append(Stop(stations[i], new_stop_time))
    return ret


def interpolate_stations(known_stations, route_stations):
    known_stations = list(known_stations)
    route_stations = list(route_stations)

    first_i = route_stations.index(known_stations[0])
    last_i = route_stations.index(known_stations[-1])
    stations = OrderedSet(route_stations[first_i:last_i+1])

    if is_express(known_stations):
        stations -= OrderedSet(EXPRESS_NONSTOP_STATIONS)
    if 'Baypointe' not in known_stations and 'Baypointe' in stations:
        stations.remove('Baypointe')
    if known_stations[-1] == 'Metro/Airport':
        stations.add('Gish')

    return list(stations)


def is_express(stations):
    if 'Baypointe' in stations and not 'Tamien' in stations:
        return True
    else:
        return False


class Train(OrderedDict):
    def __init__(self, route, all_stops, source=None):
        self.route = route
        self.known_stops = [s for s in all_stops if s.is_known]
        self.source = source
        super(Train, self).__init__([(s.station, s) for s in all_stops])

    def __hash__(self):
        return object.__hash__(self)

    @classmethod
    def from_known_stops(cls, route, known_stops, source=None):
        known_stations = [stop.station for stop in known_stops]
        stations = interpolate_stations(known_stations, route.stations)
        stops = interpolate_stops(known_stops, stations)
        return cls(route, stops, source)

    def offset_copy(self, offset):
        all_stops = [s.offset_copy(offset) for s in self.stops]
        return Train(self.route, all_stops, self.source)

    @property
    def stations(self):
        return self.keys()

    @property
    def stops(self):
        return self.values()

    @property
    def known_stations(self):
        return [stop.station for stop in self.known_stops]

    @property
    def is_express(self):
        return is_express(self.known_stations)


class ConcreteStop(object):
    def __init__(self, train, stop, start_dt):
        self.train = train
        self.route = train.route

        st = stop.stop_time
        offset_date = start_dt.date() - dt.timedelta(days=start_dt.weekday())
        offset_time = dt.datetime.utcfromtimestamp(st.total_seconds()).time()

        self.stop_time = dt.datetime.combine(offset_date, offset_time)
        self.station = stop.station
        self.dest = train.stops[-1]
        self.is_express = train.is_express

    def __repr__(self):
        tmpl = "ConcreteStop('{}', '{} {}', '{}', '{}')"
        return tmpl.format(self.station,
                           self.route.name,
                           self.route.direction,
                           self.dest.station,
                           self.stop_time)


class Stop(object):
    """
    TODO: repr's still not perfect, because the constructor
    can't take string times.
    """
    def __init__(self, station, stop_time, leave_time=None, source=None):
        self.station = station
        self.stop_time = stop_time
        self._leave_time = leave_time
        self.source = source

    def offset_copy(self, offset):
        if self._leave_time:
            return Stop(self.station,
                        self.stop_time + offset,
                        self._leave_time + offset,
                        self.source)
        else:
            return Stop(self.station,
                        self.stop_time + offset,
                        source=self.source)

    @property
    def is_known(self):
        return self.source is not None

    @property
    def wait_time(self):
        if self._leave_time is not None:
            return self._leave_time - self.stop_time
        else:
            return dt.timedelta()

    @property
    def leave_time(self):
        return self.stop_time + self.wait_time

    @leave_time.setter
    def leave_time(self, leave_time):
        self._leave_time = leave_time

    def __repr__(self):
        stop_time_obj = dt.datetime.utcfromtimestamp(self.stop_time.total_seconds()).time()
        leave_time_obj = dt.datetime.utcfromtimestamp(self.leave_time.total_seconds()).time()
        return "Stop('{}', '{}', '{}')".format(self.station,
                                               stop_time_obj,
                                               leave_time_obj)


if __name__ == '__main__':
    try:
        sched1 = Timetable.from_file('raw_schedules/SC_901NO_WK.tdl')
        #sched2 = Timetable.from_file('raw_schedules/SC_902NO_WK.tdl')
        #sched3 = Timetable.from_file('raw_schedules/SC_902SO_WK.tdl')

        cs = Schedule.from_directory('raw_schedules')
        ja_stops = cs.get_stops('Japantown/Ayer')
        first_stops = [t.stops[0] for t in cs.all_trains]
        #print comp_schedl.trains[5].stations
        #print sched1.trains[5].stops
        #ex = [x for x in sched3.trains if x.stops[-1].station == 'Gish']
    except Exception as e:
        import pdb;pdb.post_mortem()
        raise
    import pdb;pdb.set_trace()
