# coding: utf-8
from cStringIO import StringIO
from datetime import datetime
from fnmatch import fnmatch
from glob import iglob
from os import chdir, makedirs, path
from sys import argv
from time import sleep, time
from traceback import format_exc

from colorama import Fore, Style, init
from watchdog.observers import Observer


class Log(object):
    datefmt = '[%Y-%m-%d %H:%M:%S]'

    @classmethod
    def timestamp(cls):
        return cls.fore(datetime.now().strftime(cls.datefmt),
                        'BLACK',
                        bright=True)

    @classmethod
    def _log(cls, message, color, prefix):
        message = cls.fore(message, color)

        if prefix:
            print cls.timestamp(), prefix + ':', message
        else:
            print cls.timestamp(), message

    @classmethod
    def fore(cls, text, color=None, dim=False, bright=False):
        if color:
            if dim:
                text = Style.DIM + text

            if bright:
                text = Style.BRIGHT + text

            return Fore.__getattribute__(color) + text + Style.RESET_ALL
        else:
            return text

    @classmethod
    def info(cls, message, prefix=None):
        cls._log(message, None, prefix)

    @classmethod
    def error(cls, message, prefix=None):
        cls._log(Style.BRIGHT + message, 'RED', prefix)

    @classmethod
    def success(cls, message, prefix=None):
        cls._log(message, 'GREEN', prefix)

    @classmethod
    def warning(cls, message, prefix=None):
        cls._log(message, 'YELLOW', prefix)

    __call__ = info


class Product(object):
    _path = None
    ext = None
    data = None
    abspath = None
    ignore = False
    last_dest = None
    changed = False

    @property
    def size(self):
        return len(self.data)

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value
        self.ext = path.splitext(value)[1]

    def rename(self, new_filename):
        dirs, basename = path.split(new_filename)
        self.path = path.join(dirs, new_filename)

    def change_ext(self, new_ext):
        self.path = path.splitext(self.path)[0] + new_ext
        self.ext = new_ext
        return self.path

    def match(self, path, pattern):
        rv = fnmatch(path, pattern)
        if rv:
            return rv

        if pattern.startswith('**/') or pattern.startswith('**\\'):
            rv = rv or fnmatch(path[3:], pattern)
        return rv

    @classmethod
    def load_product(cls, filepath, rel_filepath, open_mode='rb'):
        new_product = cls()

        if path.isabs(filepath):
            Log.warning('absolute filepath will be ignored: %s', filepath)
            new_product.ignore = True
            return

        try:
            f = open(filepath, open_mode)
            new_product.data = f.read()
            new_product.path = rel_filepath
            f.close()

            return new_product
        except IOError as ex:
            Log.error('cannot load: ' + ex.filename)

    def save_product(self, dest, open_mode='wb'):
        new_path = path.join(dest, self.path)

        # Ingore overwrite
        if path.abspath(new_path) == self.abspath:
            return

        dirs, filename = path.split(new_path)
        if path.exists(dirs):
            if not path.isdir(dirs):
                Log.error('cannot create folder, because path `%s` is a file' %
                          dirs, 'product')
                exit()

        else:
            try:
                makedirs(dirs)
            except Exception as ex:
                Log.error('cannot create folder, exception occurs: %s' %
                          ex.message, 'product')
                exit()

        try:
            f = open(new_path, open_mode)
            f.write(self.data)
            f.close()
            self.last_dest = new_path
        except IOError as ex:
            Log.error('cannot save product, exception occurs: %s' % ex.message,
                      'product')
            exit()


class Beltline(object):
    # to initialize the list with an object make linter work perfect.
    _products = [Product()]
    _filtered_products = {}
    _filename_hashsets = set()
    _create_time = None

    _current_cwd = '.'

    def __init__(self, *beltlines):
        self._products = []
        self.merge(*beltlines)
        self._create_time = time()

    def configure(self, cwd=None):
        self._current_cwd = cwd or self._current_cwd
        chdir(self._current_cwd)

    @property
    def time_elapsed(self):
        return time() - self._create_time

    @property
    def products(self):
        for product in self._products:
            if product.ignore:
                continue
            yield product

    def _load_products(self, glob):
        for filepath, rel_filepath in iglob(glob):

            # Prevent file duplicating
            abspath = path.abspath(filepath)
            if abspath in self._filename_hashsets:
                continue
            self._filename_hashsets.add(abspath)

            # Ignore directory
            if path.isdir(filepath):
                continue

            new_product = Product.load_product(filepath, rel_filepath)
            if new_product.ignore:
                continue
            new_product.abspath = abspath
            self._products.append(new_product)

    def clear(self):
        self._products = []
        self._filtered_products = {}
        self._filename_hashsets = set()

        return self

    def src(self, *source):
        for glob in source:
            if isinstance(glob, (basestring, unicode)):
                glob = str(glob)
            else:
                Log.error('Unsupported source type: %s', type(source))
                Beltline.terminate()

            self._load_products(glob)

        return self

    def dest(self, destination):
        destination = path.normpath(destination)
        for product in self.products:
            product.save_product(destination)
        return self

    def delete(self, pattern=None):
        if not pattern:
            return self.clear()
        else:
            for product in self.products:
                if fnmatch(product.path, pattern):
                    self._filename_hashsets.remove(product.abspath)
                    self._products.remove(product)

        return self

    def debug(self):
        count = 0
        Log.info(Log.fore('Product List:', 'LIGHTBLUE_EX'), 'debug')
        for product in self.products:
            Log.warning('-> ' + product.path, 'debug')
            count += 1
        Log.success(str(count) + ' Product(s)', 'debug')

        return self

    def ignore(self, pattern, recover_id=None):
        recover_list = []

        if recover_id is None:
            return self.delete(pattern)

        if recover_id in self._filtered_products:
            Log.error('Duplicated recover id `%d`' % recover_id, 'filter')
            exit()

        for product in self._products:
            if product.ignore:
                continue

            if product.match(product.path, pattern):
                product.ignore = True
                recover_list.append(product)

        self._filtered_products[recover_id] = recover_list

        return self

    def recover(self, recover_id=None, recover_all=False):
        if recover_all:
            for prouduct in self._products:
                prouduct.ignore = False
            self._filtered_products.clear()

        else:
            recover_list = self._filtered_products.pop(recover_id, [])
            for product in recover_list:
                product.ignore = False

        return self

    def concat(self, new_filename):
        new_product = Product()
        new_product.path = new_filename
        new_product.changed = True
        data = StringIO()

        count = 0
        for product in self.products:
            count += 1

            self._filename_hashsets.remove(product.abspath)
            self._products.remove(product)

            new_product.data.write(product.data.getvalue())
            del product

        if count:
            new_product.data = data.getvalue()
            self._products.insert(0, new_product)

        return self

    def merge(self, *beltlines):
        for beltline in beltlines:
            for product in beltline.products:
                if product.abspath in self._filename_hashsets:
                    continue
                self._products.append(product)
                self._filename_hashsets.add(product.abspath)

        return self

    def roll(self, worker, exception_handler=None, **kwargs):
        try:
            worker(self, **kwargs)
        except Exception as ex:
            if callable(exception_handler):
                exception_handler(ex)
            elif exception_handler is False:
                pass
            elif isinstance(ex, BeltlineTermination):
                exit()
            raise

        return self


class BeltlineTermination(Exception):
    pass


class Factory(object):
    _tasks = {}
    _print_mode = False
    _observer = None

    def __init__(self):
        init(autoreset=True)
        self._observer = Observer()

    def add_task(self, task_func, task_name=None):
        self._tasks[task_name or task_func.__name__] = task_func

    def task(self, task_name=None):
        def decorator(func):
            self.add_task(func, task_name)
            return func

        return decorator

    def run_task(self, *tasks):
        for task in tasks:
            task_func = self._tasks.get(task)
            if not task_func:
                Log.error('task `%s` doesn\'t exist.' % task)
                exit()

            task_display_name = Log.fore(task, 'CYAN')
            Log.info('task `%s` starts rolling.' % task_display_name)

            start_time = time()
            try:
                task_func()
            except Exception as ex:
                Log.error('Unhandle exception: ' + ex.__class__.__name__)
                for tb_line in format_exc().splitlines(False):
                    Log.error(tb_line)

            finally:
                Log.info('task `%s` ends up rolling, time elapsed: %.3fs' %
                         (task_display_name, time() - start_time))

    def print_help(self, extra_message=None):
        dirs, filename = path.split(argv[0])
        program_name = filename

        print('Beltline, a streaming file process tools.\r\n'
              '       Automatically & Efficient.\r\n'
              '\r\n'
              'Usage:\r\n'
              '  %s task_queue\r\n'
              '\r\n'
              'Example:\r\n'
              '  %s task1 task2 task3 task4\r\n'
              '  # run task from task1 to task4 one by one\r\n'
              '\r\n'
              'Avaiable Tasks:\r\n'
              '  %s' % (program_name, program_name, ' '.join(self._tasks)))

        if extra_message:
            print '=' * 30
            print extra_message

    def add_watcher(self, pattern, *handler_or_tasks):
        pass

    def start_watch(self):
        self._observer.start()
        try:
            while 1:
                sleep(1)
        except KeyboardInterrupt:
            self._observer.stop()
        self._observer.join()

    def start(self):
        params = argv[1:]
        if not params:
            params = ['default']

        if params[0] == '-h' \
                or params[0] == '--help':
            self.print_help()
            exit()

        self.run_task(*params)
