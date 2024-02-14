from draw_recursion.track_recursion import _TrackedFn, ExceptionDuringRecursion
from typing import Callable
from functools import wraps
import pytest
import time


class ExposeCallLedger(_TrackedFn):
    """
    New class that inherits from `_TrackedFn`, and overwrites
    its __call__ methods to expose the call_ledger and call_stack at each stage
    of the recursion. This allows for easy testing without exposing in the actual 
    public API.
    """

    def __call__(self):
        # If the virtual_call_stack is not empty, then this __call__
        # is a recursive call whose direct parent is the `TrackedFunc` at the end of the call stack.
        # Log this invocation as a child call of the parent for later.
        if self.__class__._virtual_call_stack:
            latest_func_call = self.__class__._virtual_call_stack[-1]
            latest_func_call.child_calls.append(self)
            self.parent_caller = latest_func_call

        # Add self both to the virtual call stack (a temporary storage)
        # and the call_ledger (a permanent thing).
        self.__class__._virtual_call_stack.append(self)
        self._call_ledger.append(self)
        if self.__class__._func_start_time is None:
            self.__class__._func_start_time = time.perf_counter()

        # Directly invoke the function.
        try:
            self.return_value = self.func(*self.args, **self.kwargs)
        except Exception as exc:
            self.uncaught_exception = (
                ExceptionDuringRecursion(
                    f"{exc} at depth {self.depth} caused by call: {str(self)}")
                if not isinstance(exc, ExceptionDuringRecursion) else exc)

        # Remove self from the virtual_call_stack
        self._virtual_call_stack.pop()
        if self.uncaught_exception is not None:
            raise self.uncaught_exception
        return self.return_value

    @classmethod
    def wipe_maps(cls):
        cls._call_ledger.clear()
        cls._virtual_call_stack.clear()
        cls._func_start_time = None


@pytest.fixture
def clear_call_ledger():
    yield
    ExposeCallLedger.wipe_maps()


def expose_call_ledger(fn: Callable):
    @wraps(fn)
    def inner(*args, **kwargs):
        return ExposeCallLedger(
            fn,
            None,
            *args,
            **kwargs)(
        )
    return inner
