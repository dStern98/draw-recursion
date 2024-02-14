from draw_recursion.track_recursion import _TrackedFn,  ExceptionDuringRecursion
import pytest
from .conftest import expose_call_ledger, ExposeCallLedger


@expose_call_ledger
def will_panic(x: int):
    """
    Just for testing failing functions.
    """
    if x <= 0:
        raise RuntimeError("Panic!")
    will_panic(x-1)


@expose_call_ledger
def fast_exp(n: int, exp: int):
    """
    Efficient recursive function for computing exponentionals
    by exploiting the fact that n**exp == (n**exp/2) ** 2
    """
    if exp == 1:
        return n
    if exp % 2 == 0:
        return fast_exp(n, exp/2) ** 2
    else:
        # In the odd case, we need an extra n
        # to offset the floor divide
        return n * fast_exp(n, exp//2) ** 2


def test_repr_and_str():
    fast_exp_tracked = _TrackedFn(
        fast_exp,
        None,
        7,
        5
    )
    assert repr(fast_exp_tracked) == "_TrackedFn(fast_exp,7,5)"
    # The String representation should show the function invocation
    # Since __call__ has not yet been called, the return value is !
    assert str(fast_exp_tracked) == "fast_exp(7,5)-> !"


def test_no_call_ledger(clear_call_ledger):
    with pytest.raises(RuntimeError):
        ExposeCallLedger._build_dot_graph_string()


def test_fast_exp_dot_string(clear_call_ledger):
    fast_exp(17, 19)

    # Check the dot string generated from the fast_exp call
    dot_string = ExposeCallLedger._build_dot_graph_string()
    answer = """digraph graphname {
 1 [label="fast_exp(17,19)-> 239072435685151324847153" color=orange];
2 [label="fast_exp(17,9)-> 118587876497" color=orange];
3 [label="fast_exp(17,4)-> 83521" color=orange];
4 [label="fast_exp(17,2.0)-> 289" color=orange];
5 [label="fast_exp(17,1.0)-> 17" color=lightgreen];
1 -> 2;
2 -> 3;
3 -> 4;
4 -> 5;
}"""
    assert answer == dot_string


def test_will_panic_dot_string(clear_call_ledger):
    with pytest.raises(ExceptionDuringRecursion):
        will_panic(5)
    # Check the dot string
    dot_string = ExposeCallLedger._build_dot_graph_string()
    # Check the dot string generated from a panic
    assert dot_string == """digraph graphname {
 1 [label="will_panic(5)-> !" color=red];
2 [label="will_panic(4)-> !" color=red];
3 [label="will_panic(3)-> !" color=red];
4 [label="will_panic(2)-> !" color=red];
5 [label="will_panic(1)-> !" color=red];
6 [label="will_panic(0)-> !" color=red];
1 -> 2;
2 -> 3;
3 -> 4;
4 -> 5;
5 -> 6;
}"""


def test_processed_call_no_timer(clear_call_ledger):
    with pytest.raises(RuntimeError) as exc:
        ExposeCallLedger._into_processed_call()
    assert str(exc.value) == "Runtime timer was set to None during analysis."


def test_processed_call_no_call_ledger(clear_call_ledger):
    ExposeCallLedger._func_start_time = 1.6
    with pytest.raises(RuntimeError):
        ExposeCallLedger._into_processed_call()


def test_into_processed_call(clear_call_ledger):
    fast_exp(37, 45)
    processed_call = ExposeCallLedger._into_processed_call()
    assert processed_call.total_fn_calls == 6
    assert processed_call.max_recursion_depth == 5
    assert processed_call.uncaught_exception is None
    assert processed_call.return_value == 37074694665532807170105663883978228276095096806613832327136970789759157
