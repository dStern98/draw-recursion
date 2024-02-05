from typing import Callable
from collections import deque
from .build_html import ProcessedRecursiveCall
import time
from typing import Any, Literal
from functools import wraps


def stringify(value: Any) -> str:
    value = str(value)
    if len(value) < 10:
        return value
    return value[:10]


class TrackedFunc:
    call_ledger: list["TrackedFunc"] = []
    virtual_call_stack: list["TrackedFunc"] = []
    func_start_time: float | None = None

    def __init__(
            self,
            func: Callable,
            *args,
            **kwargs):
        self.func = func
        self.return_value: Any = "!"
        self.args = args
        self.kwargs = kwargs
        self.child_calls: list["TrackedFunc"] = []
        self.func_call = f"{self.func.__name__}({self.args_as_str}{self})"
        self.parent_caller = None
        self.uncaught_exception = None
        self.depth = 0 if not self.virtual_call_stack else self.virtual_call_stack[-1].depth + 1
        self.call_number = len(self.call_ledger) + 1

    @property
    def args_as_str(self):
        return ",".join((stringify(arg)
                         for arg in self.args)) if self.args else ""

    @property
    def kwargs_as_str(self):
        return ",".join((f"{str(key)}={stringify(value)}")
                        for key, value in self.kwargs.items())

    @property
    def args_kwargs_sep(self):
        return "," if self.kwargs_as_str else ""

    def __str__(self):
        return (
            f"{self.func.__name__}({self.args_as_str}{self.args_kwargs_sep}{self.kwargs_as_str})"
            f"=> {self.return_value}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__qualname__}({self.func.__name__},"
            f"{self.args_as_str}{self.args_kwargs_sep}{self.kwargs_as_str})")

    def __call__(
            self,
            fn_alias: str | None = None,
            report_to_stdout: Literal["summary", "verbose", "none"] = "none",
            generate_html_report: bool = True
    ):
        """
        Execute the decorated callable, tracking all desired information.

        The `virtual_call_stack` is used to simulate a real function call stack, 
        while the `call_ledger` stores all function invocations.  
        """
        # If the virtual_call_stack is not empty, then this __call__
        # is a recursive call whose direct parent is the `TrackedFunc` at the end of the call stack.
        # Log this invocation as a child call of the parent for later.
        if self.__class__.virtual_call_stack:
            latest_func_call = self.__class__.virtual_call_stack[-1]
            latest_func_call.child_calls.append(self)
            self.parent_caller = latest_func_call

        # Add self both to the virtual call stack (a temporary storage)
        # and the call_ledger (a permanent thing).
        self.__class__.virtual_call_stack.append(self)
        self.call_ledger.append(self)

        if self.__class__.func_start_time is None:
            self.__class__.func_start_time = time.perf_counter()

        # Directly invoke the function.
        try:
            self.return_value = self.func(*self.args, **self.kwargs)
        except Exception as exc:
            self.uncaught_exception = exc
            if len(self.virtual_call_stack) > 1:
                raise exc
        finally:
            # Remove self from the virtual_call_stack
            self.virtual_call_stack.pop()

        # If the virtual_call_stack is empty, then this self is the first function call
        # and we have a responsibility to process the results
        # and dump the contents to a file before returning.
        if len(self.virtual_call_stack) == 0:
            self.__class__.process_results_and_cleanup()

        if self.uncaught_exception is not None:
            raise self.uncaught_exception
        return self.return_value

    @classmethod
    def build_dot_string(cls) -> str:
        """
        Use the content from the `call_ledger` and build a dot graph string.

        See https://en.wikipedia.org/wiki/DOT_(graph_description_language) for details.
        The HTML file generated will contain JavaScript that parses the graph string into a graph, 
        and visualizes it.
        """
        base_graph_string = "digraph graphname {\n "

        if not cls.call_ledger:
            raise RuntimeError("The call ledger had no first function call!")

        for func_call in cls.call_ledger:
            if func_call.uncaught_exception is not None:
                node_color = "red"
            elif len(func_call.child_calls) == 0:
                node_color = "lightgreen"
            else:
                node_color = "orange"
            base_graph_string += f'{func_call.call_number} [label="{str(func_call)}" color={node_color}];\n'

        # Use a deque for efficient operations on both sides.
        breadth_first_queue = deque([cls.call_ledger[0]])
        while breadth_first_queue:
            this_fn_call = breadth_first_queue.popleft()
            for child_call in this_fn_call.child_calls:
                base_graph_string += f"{this_fn_call.call_number} -> {child_call.call_number};\n"
                breadth_first_queue.append(child_call)
        base_graph_string += "}"
        return base_graph_string

    @classmethod
    def into_processed_call(cls) -> ProcessedRecursiveCall:
        # Write the processed results to an HTML file.
        if cls.func_start_time is None:
            raise RuntimeError(
                "Runtime timer was set to None during analysis.")
        total_fn_runtime = time.perf_counter() - cls.func_start_time
        if not cls.call_ledger:
            raise RuntimeError(
                "Call Ledger is not allowed to be empty during analysis.")
        base_fn_call = cls.call_ledger[0]
        return ProcessedRecursiveCall(
            runtime_seconds=total_fn_runtime,
            fn_name=base_fn_call.func.__name__,
            total_fn_calls=len(cls.call_ledger),
            max_recursion_depth=max((call.depth for call in cls.call_ledger)),
            first_fn_call=str(base_fn_call),
            dot_graph=cls.build_dot_string(),
            uncaught_exception=str(
                base_fn_call.uncaught_exception) if base_fn_call.uncaught_exception else None,
            return_value=base_fn_call.return_value
        )

    @classmethod
    def process_results_and_cleanup(cls):
        """
        Write the results to an HTML file and clear the ledger.

        First: Takes the `call_ledger` content and build the HTML file.
        Second: Wipes the `call_ledger` and `virtual_call_stack` so that the next decorated function call
        is not corrupted by data from a different function. The `virtual_call_stack` should
        already be empty when this method is invoked, but just as a precaution, clear it anyway.
        """
        processed_call = cls.into_processed_call()
        processed_call.write_html_file()

        # Clear both ledger an virtual_call_stack lists.
        cls.call_ledger.clear()
        cls.virtual_call_stack.clear()
        cls.func_start_time = None
        assert len(cls.call_ledger) == 0
        assert len(cls.virtual_call_stack) == 0


def track_recursion(
        report_to_stdout: Literal["summary", "verbose", "none"] = "none",
        fn_alias: str | None = None,
        generate_html_report: bool = True):
    def wrapper(fn: Callable):
        @wraps(fn)
        def inner(*args, **kwargs):
            return TrackedFunc(fn, *args, **kwargs)()
        return inner
    return wrapper
