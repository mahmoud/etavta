#!/usr/bin/env python
from __future__ import unicode_literals, print_function

import os
import urllib2
from functools import partial
import json

from datetime import datetime
from localtime import get_pacific_time, ISO_FORMAT, Pacific
from schedule import Schedule

FETCH_TIMEOUT = 15 # in seconds
RAW_SCHED_DIR = 'raw_schedules'
ROOT_WEB_ADDR = 'http://www.vta.org/schedules/tdl/'

LINES = ('900', '901', '902')
DIRECTIONS = ('NO', 'SO')
DAYS = ('WK', 'SA', 'SU')
EXTENSION = 'tdl'

CUR_DIR = os.path.abspath(os.path.dirname(__file__))

_DATE_DIR_FORMAT = '%Y%m%d'


def debug(*a, **kw):
    return


def make_filename(line, direction, day, ext=EXTENSION):
    return 'SC_{line}{direction}_{day}.{ext}'.format(**locals())


def make_target_dirname(dt=None):
    if not dt:
        dt = get_pacific_time()
    return dt.strftime(_DATE_DIR_FORMAT)


def get_newest_sched_dir(root_dir, date_format=_DATE_DIR_FORMAT, dt=None):
    dirnames = []
    for dn in os.listdir(root_dir):
        if os.path.isdir(os.path.join(root_dir, dn)):
            dirnames.append(dn)
    if dirnames:
        dirnames.sort(key=lambda x: datetime.strptime(x.strip(),
                                                      _DATE_DIR_FORMAT))
        return os.path.join(root_dir, dirnames[-1])
    else:
        return None


def get_sched_filenames():
    ret = []
    for line in LINES:
        for direction in DIRECTIONS:
            for day in DAYS:
                fn = make_filename(line, direction, day)
                ret.append(fn)
    return ret


def download_file(url):
    response = urllib2.urlopen(url)
    return response.read()


def download_schedules(sched_root=None):
    if sched_root is None:
        sched_root = os.path.join(CUR_DIR, RAW_SCHED_DIR)
    target_dirname = make_target_dirname()
    target_dir_path = os.path.join(sched_root, target_dirname)

    journal = FetchJournal(target_dir_path)
    can_proceed = journal.lock()
    if not can_proceed:
        return # journal.some_info

    filenames = get_sched_filenames()
    for fname in filenames:
        debug('downloading', fname, '...')
        url = ROOT_WEB_ADDR + fname
        try:
            sched = download_file(url)
            journal.add_schedule(fname, sched)
        except urllib2.HTTPError as e:
            msg = '{} {}'.format(e.code, e.msg)
            journal.add_error(fname, msg)

    successful = journal.commit()
    if successful:
        debug('yay')


# an experiment gone slightly awry. not enough awry to be unusable though.
class FetchJournal(object):
    def __init__(self, target_dir_path, filename='report.txt'):
        self.target_dir_path = target_dir_path
        self.filename = filename
        self._reinit()
        try:
            self._load()
            self.clean = True
        except IOError:
            self._reinit()

    @property
    def path(self):
        return os.path.join(self.target_dir_path, self.filename)

    def _reinit(self):
        self.start_time = get_pacific_time()
        self.schedules = {}
        self.errors = {}
        self.clean = False
        self.finish_time = None
        self.pid = os.getpid()

    def _load(self):
        with open(self.path, 'r') as f:
            content = f.read()
        cdict = json.loads(content)
        self.start_time = datetime.strptime(cdict['start_time'], ISO_FORMAT)
        self.start_time = self.start_time.replace(tzinfo=Pacific)
        self.pid = cdict['pid']
        self.schedules = dict([(fn, None) for fn in cdict['schedules']])
        self.errors = cdict['errors']
        if cdict.get('finish_time'):
            self.finish_time = datetime.strptime(cdict['finish_time'], ISO_FORMAT)
            self.finish_time = self.finish_time.replace(tzinfo=Pacific)
            # TODO
            #self.duration =

    def write_file(self, path=None):
        path = path or self.path
        cdict = {'start_time': self.start_time.replace(tzinfo=None).strftime(ISO_FORMAT),
                 'pid': os.getpid(),
                 'schedules': sorted(self.schedules.keys()),
                 'errors': self.errors,
                 'finish_time': self.finish_time}
        if self.finish_time:
            cdict['finish_time'] = self.finish_time.replace(tzinfo=None).strftime(ISO_FORMAT)
        text = json.dumps(cdict, indent=2, sort_keys=True)
        with open(self.path, 'w') as f:
            f.write(text)

    def add_schedule(self, fname, sched_text):
        self.schedules[fname] = sched_text

    def add_error(self, fname, err_msg):
        self.errors[fname] = err_msg

    def lock(self):
        if self.clean:
            cur_time = get_pacific_time()
            total_seconds = (cur_time - self.start_time).total_seconds()
            if FETCH_TIMEOUT and total_seconds > FETCH_TIMEOUT:
                self._reinit()
                self._purge()
            else:
                return False
        if not os.path.exists(self.target_dir_path):
            os.makedirs(self.target_dir_path)
        self.write_file()
        return True

    def _purge(self):
        fnames = self.schedules.keys() + self.errors.keys() + [self.filename]
        for fname in fnames:
            try:
                os.remove(os.path.join(self.target_dir_path, fname))
            except:
                pass
        return

    def commit(self):
        self._check_integrity()
        for fname, sched_content in self.schedules.items():
            file_path = os.path.join(self.target_dir_path, fname)
            with open(file_path, 'w') as f:
                f.write(sched_content)
        self.write_file()

    def _check_integrity(self):
        try:
            self._schedule = Schedule.from_directory(target_dir_path)
        except Exception as e:
            # something's bork'd, add it to the report
            pass



if __name__ == '__main__':
    debug = print
    download_schedules()
