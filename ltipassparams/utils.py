from typing import Callable, Iterable, Optional, TypeVar


T = TypeVar('T')
def indexof(lst: Iterable[T], predicate: Callable[[T], bool]) -> Optional[int]:
    """ Finds an item in a list by applying a function.  Returns
        the index if found, otherwise None. """
    for i, x in enumerate(lst):
        if predicate(x):
            return i
    return None

def find(lst: Iterable[T], predicate: Callable[[T], bool]) -> Optional[T]:
    """ Finds an item in a list by applying a function.  Returns
        the item itself if found, otherwise None. """
    for x in lst:
        if predicate(x):
            return x
    return None