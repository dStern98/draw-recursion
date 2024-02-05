from draw_recursion import track_recursion
from draw_recursion.track_recursion import TrackedFunc
import pytest
import random


@track_recursion()
def panic():
    if random.randint(0, 3) == 3:
        raise RuntimeError("Panic!")
    panic()


@track_recursion()
def fib(n: int):
    if n < 2:
        return n
    return fib(n-1) + fib(n-2)


@track_recursion()
def grid_traveler(current_x: int, current_y: int, memo={}) -> int:
    if (current_x, current_y) in memo:
        return memo[(current_x, current_y)]
    if current_x < 0 or current_y < 0:
        return 0
    elif current_x == 0 and current_y == 1:
        return 1

    memo[(current_x, current_y)] = grid_traveler(current_x-1, current_y,
                                                 memo) + grid_traveler(current_x, current_y - 1, memo)
    return memo[(current_x, current_y)]


def test_fibonacci():
    response = fib(10)


def test_panic():
    with pytest.raises(RuntimeError):
        panic()


def test_grid_traveler():
    grid_traveler(5, 5)
