import os
from dataclasses import dataclass
from typing import Any

HTML_TEMPLATE = """
<html>

<head>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>

    <style type="text/css">
        #mynetwork {
            margin: 5px;
            margin-left: 5%;
            margin-right: 5%;
            width: 90%;
            height: 80%;
            border: 1px solid lightgray;
        }

        .top-container {
            height: 18%;
            margin-left: 5%;
            margin-right: 5%;
            display: flex;
            flex-direction: row;
            justify-content: space-around;
            flex-wrap: wrap;
            border: 1px solid lightgray;
        }

        .metadata-box {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .metadata-label {
            font-size: small;
        }

        .metadata-value {
            font-size: large;
        }
    </style>
</head>

<body>
    <div class="top-container">
        <div class="metadata-box">
            <span class="metadata-label">First Fn Call</span>
            <span class="metadata-value">{function_call}</span>
        </div>
        <div class="metadata-box">
            <span class="metadata-label">Total Fn Calls</span>
            <span class="metadata-value">{total_recursive_calls}</span>
        </div>
        <div class="metadata-box">
            <span class="metadata-label">Function Outcome</span>
            <span class="metadata-value">{function_outcome}</span>
        </div>
        <div class="metadata-box">
            <span class="metadata-label">Return Value</span>
            <span class="metadata-value">{function_return_value}</span>
        </div>
        <div class="metadata-box">
            <span class="metadata-label">Max Recursion Depth</span>
            <span class="metadata-value">{max_recursion_depth}</span>
        </div>
        <div class="metadata-box">
            <span class="metadata-label">Total Runtime</span>
            <span class="metadata-value">{total_function_runtime}s</span>
        </div>
    </div>
    <div id="mynetwork"></div>

    <script type="text/javascript">
        var DOTstring = `{graph_dot_string}`;
        var parsedData = vis.parseDOTNetwork(DOTstring);

        var data = {
            nodes: parsedData.nodes,
            edges: parsedData.edges
        }
        // create a network
        var container = document.getElementById('mynetwork');

        var options = parsedData.options;


        // you can extend the options like a normal JSON variable:
        options.layout = {
            hierarchical: {
                direction: "UD",
                sortMethod: "directed"
            },
        };

        // create a network
        var network = new vis.Network(container, data, options);

    </script>
</body>

</html>
"""


@dataclass
class ProcessedRecursiveCall:
    fn_name: str
    runtime_seconds: float
    total_fn_calls: int
    max_recursion_depth: int
    first_fn_call: str
    return_value: Any
    uncaught_exception: str | None
    dot_graph: str

    def write_html_file(self):
        dir_path = os.path.realpath(os.path.join(
            os.path.dirname(__file__), "..", "htmlreports"))
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)

        html_file = (
            HTML_TEMPLATE
            .replace("{graph_dot_string}", self.dot_graph)
            .replace("{function_call}", self.first_fn_call)
            .replace("{total_recursive_calls}", str(self.total_fn_calls))
            .replace("{max_recursion_depth}", str(self.max_recursion_depth))
            .replace("{function_outcome}", "Successfully Returned" if
                     self.uncaught_exception is None else f"Uncaught Exception: {self.uncaught_exception}")
            .replace("{total_function_runtime}", str(round(self.runtime_seconds, 6)))
            .replace("{function_return_value}", str(self.return_value))
        )

        full_file_path = os.path.join(dir_path, f"{self.fn_name}.html")
        with open(full_file_path, "w") as file:
            file.write(html_file)
