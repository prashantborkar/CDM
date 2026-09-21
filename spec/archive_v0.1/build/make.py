import os, sys
sys.path.insert(0, os.path.dirname(__file__))
OUT = os.path.join(os.path.dirname(__file__), "..", "diagrams")
os.makedirs(OUT, exist_ok=True)

import importlib
which = sys.argv[1:]
import diagrams_a as A
tasks = {
    "01": (A.d01_context, "Fig02_system_context.png"),
    "02": (A.d02_layers, "Fig03_logical_architecture.png"),
    "03": (A.d03_workflow, "Fig06_deployment_workflow.png"),
}
try:
    import diagrams_b as B
    tasks.update({
        "04": (B.d04_sequence, "Fig07_sequence_issue_deploy.png"),
        "05": (B.d05_adapters, "Fig08_adapter_routing_matrix.png"),
        "06": (B.d06_security, "Fig04_security_network_zones.png"),
        "07": (B.d07_lifecycle, "Fig05_certificate_lifecycle.png"),
    })
except ImportError:
    pass
try:
    import diagrams_c as C
    tasks.update({
        "08": (C.d08_erd, "Fig10_data_model.png"),
        "09": (C.d09_poc, "Fig01_poc_current_topology.png"),
        "10": (C.d10_platforms, "Fig09_platform_deployment_paths.png"),
        "11": (C.d11_roadmap, "Fig11_roadmap.png"),
    })
except ImportError:
    pass
for k, (fn, name) in tasks.items():
    if not which or k in which:
        fn(os.path.join(OUT, name))
        print("wrote", name)
