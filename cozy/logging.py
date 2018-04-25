from collections import defaultdict
from contextlib import contextmanager
import datetime

from cozy.opts import Option

verbose = Option("verbose", bool, False)

_times = defaultdict(float)
_task_stack = []

def log(string):
    if verbose.value:
        print(string)

def task_begin(name, **kwargs):
    start = datetime.datetime.now()
    _task_stack.append((name, start))
    if not verbose.value:
        return
    indent = "  " * (len(_task_stack) - 1)
    log("{indent}{name}{maybe_kwargs}...".format(
        indent = indent,
        name   = name,
        maybe_kwargs = (" [" + ", ".join("{}={}".format(k, v) for k, v in kwargs.items()) + "]") if kwargs else ""))

def task_end():
    end = datetime.datetime.now()
    key = tuple(name for name, start in _task_stack)
    name, start = _task_stack.pop()
    duration = (end-start).total_seconds()
    _times[key] += duration
    if not verbose.value:
        return
    indent = "  " * len(_task_stack)
    log("{indent}Finished {name} [duration={duration:.3}s]".format(indent=indent, name=name, duration=duration))

@contextmanager
def task(name, **kwargs):
    yield task_begin(name, **kwargs)
    task_end()

def event(name):
    if not verbose.value:
        return
    indent = "  " * len(_task_stack)
    log("{indent}{name}".format(indent=indent, name=name))

def dump_profile():
    with open("/tmp/cozy.profile", "w") as f:
        f.write("Currently in: {}\n\n".format(", ".join(name for (name, start) in _task_stack)))
        for k in sorted(_times.keys(), key=_times.get, reverse=True):
            f.write("{:16.3}".format(_times[k]))
            f.write(" ")
            f.write(", ".join(k))
            f.write("\n")