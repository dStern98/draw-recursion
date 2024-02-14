from collections.abc import Callable, Iterable
from collections import deque
import time
from typing import Any, ParamSpec, TypeVar
from functools import wraps
from typing_extensions import Annotated, Doc

from .report_results import ProcessedRecursiveCall


class ExceptionDuringRecursion(Exception):
    ...


class _TrackedFn:
    """
    The core class that keeps track of the recursive calls. This class is private,
    and users should never directly invoke this Class or any of its methods.

    Each `TrackedFn` instance represents a single function call.
    The shared state between recursive calls in maintained by the class attributes
    `call_ledger`, `virtual_call_stack`, and `func_start_time`
    """
    _call_ledger: list["_TrackedFn"] = []
    _virtual_call_stack: list["_TrackedFn"] = []
    _func_start_time: float | None = None

    def __init__(
            self,
            func: Callable,
            kwargs_to_ignore: Iterable[str] | None = None,
            *args,
            **kwargs):
        self.func = func
        self.return_value: Any = "!"
        self.args = args
        self.kwargs = kwargs
        self.kwargs_to_ignore = tuple(
            kwargs_to_ignore) if kwargs_to_ignore is not None else tuple()
        self.child_calls: list["_TrackedFn"] = []
        self.parent_caller = None
        self.uncaught_exception = None
        self.depth = 0 if not self._virtual_call_stack else self._virtual_call_stack[-1].depth + 1
        self.call_number = len(self._call_ledger) + 1

    @property
    def args_as_str(self):
        return ",".join((repr(arg)
                         for arg in self.args)) if self.args else ""

    @property
    def kwargs_as_str(self):
        return ",".join((f"{key}={repr(value)}")
                        for key, value in self.kwargs.items() if key not in self.kwargs_to_ignore)

    @property
    def args_kwargs_sep(self):
        return "," if self.kwargs_as_str else ""

    def __str__(self):
        return (
            f"{self.func.__name__}({self.args_as_str}{self.args_kwargs_sep}{self.kwargs_as_str})"
            f"-> {self.return_value}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__qualname__}({self.func.__name__},"
            f"{self.args_as_str}{self.args_kwargs_sep}{self.kwargs_as_str})")

    def __call__(
            self,
            report_to_stdout: Annotated[bool, Doc(
                "Whether the funcion results should be printed to stdout"
            )] = False,
            generate_html_report: Annotated[bool, Doc(
                "Whether or not the HTML file should be created."
            )] = True,
            process_results: Annotated[bool, Doc(
                """
                Whether or not to process the call ledger
                after the final recursive call.
                For testing purposes only. If set to False in production, 
                the decorator will not work.
                """
            )] = True
    ):
        """
        Execute the decorated callable, tracking all desired information.

        The `virtual_call_stack` is used to simulate a real function call stack, 
        while the `call_ledger` stores all function invocations.  
        """
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

        # If the virtual_call_stack is empty, then this self is the first function call
        # and we have a responsibility to process the results
        # and dump the contents to a file before returning.
        if len(self._virtual_call_stack) == 0 and process_results:
            self.__class__._process_results_and_cleanup(
                print_to_stdout=report_to_stdout,
                build_html_file=generate_html_report
            )

        if self.uncaught_exception is not None:
            raise self.uncaught_exception
        return self.return_value

    @classmethod
    def _build_dot_graph_string(cls) -> str:
        """
        Use the content from the `call_ledger` and build a dot graph string.

        See https://en.wikipedia.org/wiki/DOT_(graph_description_language) for details.
        The HTML file generated will contain JavaScript that parses the graph string into a graph, 
        and visualizes it.
        """
        base_graph_string = "digraph graphname {\n "

        if not cls._call_ledger:
            raise RuntimeError("The call ledger had no first function call!")

        for func_call in cls._call_ledger:
            if func_call.uncaught_exception is not None:
                node_color = "red"
            elif len(func_call.child_calls) == 0:
                node_color = "lightgreen"
            else:
                node_color = "orange"
            base_graph_string += f'{func_call.call_number} [label="{str(func_call)}" color={node_color}];\n'

        # Use a deque for efficient operations on both sides.
        breadth_first_queue = deque([cls._call_ledger[0]])
        while breadth_first_queue:
            this_fn_call = breadth_first_queue.popleft()
            for child_call in this_fn_call.child_calls:
                base_graph_string += f"{this_fn_call.call_number} -> {child_call.call_number};\n"
                breadth_first_queue.append(child_call)
        base_graph_string += "}"
        return base_graph_string

    @classmethod
    def _into_processed_call(cls) -> ProcessedRecursiveCall:
        """
        Convert the contents of the `call_ledger` into an instance of the `ProcessedRecursiveCall` class.
        """
        if cls._func_start_time is None:
            raise RuntimeError(
                "Runtime timer was set to None during analysis.")
        # Note the total function runtime
        total_fn_runtime = time.perf_counter() - cls._func_start_time
        if not cls._call_ledger:
            raise RuntimeError(
                "Call Ledger is not allowed to be empty during analysis.")
        base_fn_call = cls._call_ledger[0]
        return ProcessedRecursiveCall(
            runtime_seconds=total_fn_runtime,
            fn_name=base_fn_call.func.__name__,
            total_fn_calls=len(cls._call_ledger),
            max_recursion_depth=max((call.depth for call in cls._call_ledger)),
            first_fn_call=str(base_fn_call),
            dot_graph=cls._build_dot_graph_string(),
            uncaught_exception=str(
                base_fn_call.uncaught_exception) if base_fn_call.uncaught_exception else None,
            return_value=base_fn_call.return_value
        )

    @classmethod
    def _process_results_and_cleanup(
        cls,
        print_to_stdout: bool,
        build_html_file: bool
    ):
        """
        Write the results to an HTML file and clear the ledger.

        First: Takes the `call_ledger` content and build the HTML file.
        Second: Wipes the `call_ledger` and `virtual_call_stack` so that the next decorated function call
        is not corrupted by data from a different function. The `virtual_call_stack` should
        already be empty when this method is invoked, but just as a precaution, clear it anyway.
        """
        processed_call = cls._into_processed_call()
        if build_html_file:
            processed_call.write_html_file()
        if print_to_stdout:
            processed_call.report_to_stdout()

        # Clear both ledger an virtual_call_stack lists.
        cls._call_ledger.clear()
        cls._virtual_call_stack.clear()
        cls._func_start_time = None


P = ParamSpec("P")
T = TypeVar("T")


def track_recursion(
        report_stdout: Annotated[
            bool,
            Doc(
                "Whether or not to report the function outcome to stdout"
            )] = False,
        report_html: Annotated[bool, Doc(
            """
            Whether or not to report the function outcome to an HTML file.
            This is recommended, as its essentially the whole purpose of the package.
            The HTML file draws an interactible tree representing the recursive calls. 
            """
        )] = True,
        kwargs_to_ignore: Annotated[
            Iterable[str] | None,
            Doc(
                """
                Specifies keyword arguments to not display in the HTML file etc.
                This can be especially useful when using memoization.
                """
            )] = None):
    """
    Decorator factory that can be used to generate an HTML 
    file visualizing the tree of a recursive function.
    """
    def wrapper(fn: Callable[P, T]) -> Callable[P, T]:
        @wraps(fn)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            return _TrackedFn(
                fn,
                kwargs_to_ignore,
                *args,
                **kwargs)(
                report_stdout,
                report_html
            )
        return inner
    return wrapper
