import re
import time

from dataclasses import dataclass, field
from typing import Callable, ClassVar, Dict, Optional

def find(pred, iterable):
    for element in iterable:
        if pred(element):
            return element
    return None


class TimerError(Exception):
    """A custom exception used to report errors in use of Timer class"""


# timer.py, from https://realpython.com/python-timer/

@dataclass
class Timer:
    timers: ClassVar[Dict[str, float]] = {}
    name: Optional[str] = None
    text: str = "Elapsed time: {:0.4f} seconds"
    logger: Optional[Callable[[str], None]] = print
    _start_time: Optional[float] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Add timer to dict of timers after initialization"""
        if self.name is not None:
            self.timers.setdefault(self.name, 0)

    def start(self) -> None:
        """Start a new timer"""
        if self._start_time is not None:
            self.logger(f"[WARN] Timer is running. Using .stop() to abort")
            self.stop(silent=True)

        self._start_time = time.perf_counter()

    def stop(self, silent=False) -> float:
        """Stop the timer, and report the elapsed time"""
        if self._start_time is None:
            raise TimerError(f"Timer is not running. Use .start() to start it")

        # Calculate elapsed time
        elapsed_time = time.perf_counter() - self._start_time
        self._start_time = None

        # Report elapsed time
        if self.logger and not silent:
            self.logger(self.text.format(elapsed_time))

        if self.name:
            self.timers[self.name] += elapsed_time

        return elapsed_time


def split_sentences(string, **kwargs):
    """
    Very simple sentence splitter (replace with RiTa or other)
    """
    return re_split(r'[?!.]\s+', string, re.DOTALL, strip_parts=True)


def split_sentences_full(text):
    if not text or not len(text): return [text]

    delim = r'___'
    pattern = r'(\S.+?[.!?]["\u201D]?)(?=\s+|$)'
    clean = re.sub(r'(\r?\n)+', text, re.DOTALL)

    def unescapeAbbrevs(arr):
        return map(arr, lambda a: re.sub(pattern, a, re.DOTALL))

    def escapeAbbrevs(txt):
        abbrevs = ["Adm.", "Capt.", "Cmdr.", "Col.", "Dr.", "Gen.", "Gov.", "Lt.", "Maj.", "Messrs.", "Mr.", "Mrs.",
                   "Ms.", "Prof.", "Rep.", "Reps.", "Rev.", "Sen.", "Sens.", "Sgt.", "Sr.", "St.", "A.k.a.", "C.f.",
                   "I.e.", "E.g.", "Vs.", "V.", "Jan.", "Feb.", "Mar.", "Apr.", "Mar.", "Jun.", "Jul.", "Aug.", "Sept.",
                   "Oct.", "Nov.", "Dec."]
        for abv in abbrevs:
            idx = txt.indexOf(abv)
            while idx > -1:
                dabv = abv.replace('.', delim)
                txt = abv.replace(abv, dabv)
                idx = text.indexOf(abv)
        return txt

    arr = escapeAbbrevs(clean).match(pattern)  # ??

    if arr and len(arr):
        return unescapeAbbrevs(arr)

    return [text]



def re_split(pattern, string, flags, **kwargs):
    """
    Split a string into parts, maintaining the delimiter in the prior part
    """
    result = []
    strip_parts = kwargs.get('strip_parts', False)
    match = re.search(pattern, string, flags)
    while match:
        idx = match.start()
        idx += (match.end() - idx)
        sent = string[:idx]
        result.append(sent.strip() if strip_parts else sent)
        string = string[idx:]
        match = re.search(pattern, string, flags)
    result.append(string.strip() if strip_parts else string)
    return result
