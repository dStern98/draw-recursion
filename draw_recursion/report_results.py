import os
from dataclasses import dataclass
from typing import Any
import re
import shutil
import glob
from colorama import just_fix_windows_console, Fore, Style

just_fix_windows_console()

PATH_TO_HTML_TEMPLATE = os.path.join(
    os.path.dirname(__file__), "template.html")

with open(PATH_TO_HTML_TEMPLATE, "r") as file:
    HTML_TEMPLATE = file.read()


@dataclass
class ProcessedRecursiveCall:
    """
    Class representing the final values recorded for
    a recursive function call.
    """
    fn_name: str
    runtime_seconds: float
    total_fn_calls: int
    max_recursion_depth: int
    first_fn_call: str
    return_value: Any
    uncaught_exception: str | None
    dot_graph: str

    def get_boundary_printout(self) -> str:
        """
        Build the top printout for each recursive report.

        If the function successfully returned, then the printout is green.
        It will be red if the function raised an Exception.
        """
        terminal_size = shutil.get_terminal_size()
        if not self.uncaught_exception:
            boundary_colors = Fore.GREEN
            message = f" {self.first_fn_call} successfully returned in {round(self.runtime_seconds, 4)}s "
        else:
            boundary_colors = Fore.RED
            message = f" {self.first_fn_call} failed "

        equals_to_print = "=" * ((terminal_size.columns - len(message)) // 2)

        return f"{boundary_colors}{equals_to_print}{message}{equals_to_print}{Style.RESET_ALL}"

    def report_to_stdout(self):
        """
        Prints a message to stdout about the results of the recursive
        function call.
        """
        boundary_printout = self.get_boundary_printout()
        print("\n", boundary_printout)
        if not self.uncaught_exception:
            print(f"Return Value: {self.return_value}")
            print(f"Max Recursion Depth: {self.max_recursion_depth}")
            print(f"Total Recursive Calls: {self.total_fn_calls}")
        else:
            print(
                f"{self.first_fn_call} failed with uncaught exception: {self.uncaught_exception}")

    def write_html_file(self):
        """
        Write the HTML file to a folder either named for the 
        """
        dir_path = os.path.realpath(os.path.join(
            os.path.dirname(__file__), "..", "htmlreports"))
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)

        replacements = {
            "{graph_dot_string}": self.dot_graph,
            "{function_call}": self.first_fn_call,
            "{total_recursive_calls}": str(self.total_fn_calls),
            "{max_recursion_depth}": str(self.max_recursion_depth),
            "{function_outcome}": "Successfully Returned" if
            self.uncaught_exception is None else f"{self.uncaught_exception}",
            "{total_function_runtime}": str(round(self.runtime_seconds, 6)),
            "{function_return_value}": str(self.return_value)
        }

        # How many of this functions HTML files are already in the folder.
        preexisting_files_count = len(glob.glob(
            os.path.join(dir_path, f"{self.fn_name}*.html")))

        # Use Regex to efficiently replace the HTML String, rather than
        # just change the replacements.
        rep = {re.escape(k): v for k, v in replacements.items()}
        pattern = re.compile("|".join(rep.keys()))
        html = pattern.sub(lambda m: rep[re.escape(m.group(0))], HTML_TEMPLATE)

        full_file_path = os.path.join(
            dir_path, f"{self.fn_name}_v{preexisting_files_count + 1}.html")
        with open(full_file_path, "w") as file:
            file.write(html)
