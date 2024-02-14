from draw_recursion import track_recursion
from draw_recursion.track_recursion import ExceptionDuringRecursion
import pytest
import random
import os
import glob


@pytest.fixture
def setup_reports_folder() -> str:
    """
    Ensure that the HTML Reports folder is empty if it
    currently exists.
    """
    path_to_dir = os.path.realpath(os.path.join(
        os.path.dirname(__file__), "..", "htmlreports"
    ))
    if os.path.isdir(path_to_dir):
        for file_name in glob.glob(os.path.join(path_to_dir, "*")):
            os.remove(file_name)

    return path_to_dir


@track_recursion(report_stdout=True)
def panic():
    """
    Function that randomly panics 25% of the time.
    Infinitely recursive until that panic occurs.
    """
    if random.randint(0, 25) == 3:
        raise RuntimeError("Panic!")
    panic()


@track_recursion(report_stdout=True)
def fib(n: int):
    """
    Classic Fibonacci recursive algorithm without memoization.
    """
    if n < 2:
        return n
    return fib(n-1) + fib(n-2)


@track_recursion(kwargs_to_ignore=("memo",), report_stdout=True)
def grid_traveler(pos_x: int, pos_y: int, memo={}) -> int:
    """
    A classic dynamic programming problem.

    Memoized Grid Traveler (How many unique ways are there to traverse
    from the top left of a rectangular grid of dimension (x, y)
    to the bottom right, when you can only move right or down.
    )
    """
    if (pos_x, pos_y) in memo:
        return memo[(pos_x, pos_y)]
    if pos_x < 0 or pos_y < 0:
        return 0
    elif pos_x == 0 and pos_y == 1:
        return 1

    recursive_response = grid_traveler(pos_x-1, pos_y,
                                       memo=memo) + grid_traveler(pos_x, pos_y - 1, memo=memo)
    memo[(pos_x, pos_y)] = recursive_response
    return recursive_response


def test_fibonacci(setup_reports_folder):
    assert fib(7) == 13
    html_reports = glob.glob(os.path.join(setup_reports_folder, "*"))
    # After running fib(7), there should be one html file in the htmlreports folder
    assert {os.path.basename(file_name)
            for file_name in html_reports} == {"fib(7).html"}
    # After running fib(9), there should be a second html file
    assert fib(9) == 34
    html_reports = glob.glob(os.path.join(setup_reports_folder, "*"))

    assert {os.path.basename(file_name) for file_name in html_reports} == {
        "fib(7).html", "fib(9).html"}


def test_panic(setup_reports_folder):
    # The panic function is guranteed to fail
    with pytest.raises(ExceptionDuringRecursion) as exc:
        panic()
    assert str(exc.value).startswith("Panic! at depth") and str(
        exc.value).endswith("caused by call: panic()-> !")
    html_reports = glob.glob(os.path.join(setup_reports_folder, "*"))
    assert len(html_reports) == 1
    assert set((os.path.basename(file_name)
               for file_name in html_reports)) == {"panic().html"}


def test_grid_traveler(setup_reports_folder):
    grid_traveler(25, 25)
    html_reports = glob.glob(os.path.join(setup_reports_folder, "*"))
    # After running fib(7), there should be one html file in the htmlreports folder
    assert {os.path.basename(file_name)
            for file_name in html_reports} == {"grid_traveler(25,25).html"}


def test_grid_traveler_no_dir(setup_reports_folder):
    if os.path.isdir(setup_reports_folder):
        os.rmdir(setup_reports_folder)

    grid_traveler(17, 19)
