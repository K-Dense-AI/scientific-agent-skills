# Synthetic FlowJo import fixture

`data_set_simple_line_100.fcs` and `simple_poly_and_rect_v2_poly50.wsp`
come from [FlowKit's synthetic line example](https://github.com/whitews/FlowKit/tree/f2159043b6a56e527d4baacf97490caf8354618e/data/simple_line_example).
The upstream commit is `f2159043b6a56e527d4baacf97490caf8354618e`.
Its BSD-3-Clause license is preserved in `LICENSE`.

The FCS contains 100 generated points, not biological samples. The workspace
was saved by FlowJo 10.6.1 and defines a polygon containing 50 points and a
rectangle containing none. The only change to the upstream WSP is replacement
of its original absolute `file:/V:/flowkit/flowjo_workspace_parsing/simple_line_example/`
URI prefix with `file:`. Tests supply FCS paths explicitly and do not follow
workspace URIs. These files validate import and transform semantics, not
compatibility with all FlowJo features or biological gating accuracy.
