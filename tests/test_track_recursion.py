from draw_recursion import track_recursion
from draw_recursion.track_recursion import TrackedFn, ExceptionDuringRecursion
import pytest
import random
import os
import glob


@pytest.fixture
def setup_html_reports() -> str:
    """
    Ensure that the HTML Reports folder is empty if it
    currently exists.
    """
    path_to_dir = os.path.realpath(os.path.join(
        os.path.dirname(__file__), "..", "htmlreports"
    ))
    print(path_to_dir)
    if os.path.isdir(path_to_dir):
        for file_name in glob.glob(os.path.join(path_to_dir, "*")):
            os.remove(file_name)

    return path_to_dir


@track_recursion()
def fast_exp(n: int, exp: int):
    if exp == 1:
        return n
    if exp % 2 == 0:
        return fast_exp(n, exp/2) ** 2
    else:
        return n * fast_exp(n, exp//2) ** 2


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


@track_recursion(kwargs_to_ignore=("memo",), generate_stdout_report=True)
def grid_traveler(current_x: int, current_y: int, memo={}) -> int:
    """
    Memoized Grid Traveler (How many unique ways are there to traverse
    from the top left of a rectangular grid of dimension (x, y)
    to the bottom right, when you can only move right or down.
    )
    """
    if (current_x, current_y) in memo:
        return memo[(current_x, current_y)]
    if current_x < 0 or current_y < 0:
        return 0
    elif current_x == 0 and current_y == 1:
        return 1

    memo[(current_x, current_y)] = grid_traveler(current_x-1, current_y,
                                                 memo=memo) + grid_traveler(current_x, current_y - 1, memo=memo)
    return memo[(current_x, current_y)]


def test_fibonacci(setup_html_reports):
    assert fib(7) == 13
    html_reports = glob.glob(os.path.join(setup_html_reports, "*"))
    # After running fib(7), there should be one html file in the htmlreports folder
    assert {os.path.basename(file_name)
            for file_name in html_reports} == {"fib_v1.html"}
    # After running fib(9), there should be a second html file
    assert fib(9) == 34
    html_reports = glob.glob(os.path.join(setup_html_reports, "*"))

    assert {os.path.basename(file_name) for file_name in html_reports} == {
        "fib_v1.html", "fib_v2.html"}


def test_panic():
    # The panic function is guranteed to fail
    with pytest.raises(ExceptionDuringRecursion) as exc:
        panic()
    assert str(exc.value).startswith("Panic! at depth") and str(
        exc.value).endswith("caused by call: panic()=> !")
