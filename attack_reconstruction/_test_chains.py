"""Throwaway correctness test for the new time-respecting search in chains.py.
Builds tiny synthetic graphs (no 11GB scan needed) to check:
  - directed forward path
  - undirected info-flow path across a REVERSED edge (the file->proc/EXECUTE case)
  - time monotonicity is enforced
  - structural (time-broken) fallback
  - unreachable -> None
  - parent-pointer stitching yields a contiguous edge list
"""
from graph_builder import ProvenanceGraph
from chains import _directed_forward, _bidirectional, link_stages


def mk(edges):
    """edges: list of (src, dst, etype, ts). Returns a ProvenanceGraph."""
    g = ProvenanceGraph()
    for src, dst, etype, ts in edges:
        g._add_edge(src, dst, etype, ts, None, None)
    return g


def contiguous(path, src_set, dst_set):
    """A returned undirected path need not be head-oriented; verify it forms a
    connected sequence touching src and dst, with each consecutive pair sharing
    a node."""
    if path == []:
        return True
    nodes_seq = []
    for e in path:
        nodes_seq.append({e.src, e.dst})
    # consecutive edges must share an endpoint
    for a, b in zip(nodes_seq, nodes_seq[1:]):
        if not (a & b):
            return False
    endpoints = nodes_seq[0] | nodes_seq[-1]
    return bool(nodes_seq[0] & (src_set | dst_set)) and bool(nodes_seq[-1] & (src_set | dst_set))


def test_directed_forward():
    g = mk([("A", "B", "EVENT_CONNECT", 10),
            ("B", "C", "EVENT_WRITE", 20)])
    p = _directed_forward(g, {"A"}, {"C"}, 8)
    assert p is not None and len(p) == 2, p
    assert [e.src for e in p] == ["A", "B"], p
    print("ok directed_forward")


def test_directed_time_blocked():
    # edge B->C happens BEFORE A->B, so no time-ordered forward path
    g = mk([("A", "B", "EVENT_CONNECT", 20),
            ("B", "C", "EVENT_WRITE", 10)])
    assert _directed_forward(g, {"A"}, {"C"}, 8) is None
    print("ok directed_time_blocked")


def test_infoflow_reversed_edge():
    # The EXECUTE case: edge is proc->file (proc EXECUTE /tmp/x), but we want to
    # link the FILE to the PROC. Forward fails; undirected time-ordered succeeds.
    g = mk([("proc_loader", "file_x", "EVENT_WRITE", 10),   # loader drops file
            ("proc_vugefal", "file_x", "EVENT_EXECUTE", 20)])  # vugefal execs it
    assert _directed_forward(g, {"file_x"}, {"proc_vugefal"}, 8) is None
    kind, p = link_stages(g, {"file_x"}, {"proc_vugefal"}, 8)
    assert kind == "infoflow", (kind, p)
    assert contiguous(p, {"file_x"}, {"proc_vugefal"}), p
    print("ok infoflow_reversed_edge")


def test_netflow_proc_netflow():
    # net3 --RECVFROM--> proc --CONNECT--> net4  (RECVFROM reversed at build time
    # here we just simulate the already-normalized edges)
    g = mk([("net3", "proc", "EVENT_RECVFROM", 10),   # already reversed => net->proc
            ("proc", "net4", "EVENT_CONNECT", 20)])
    p = _directed_forward(g, {"net3"}, {"net4"}, 8)
    assert p is not None and len(p) == 2, p
    print("ok netflow_proc_netflow forward")


def test_structural_fallback():
    # link exists but timestamps go the wrong way for a causal order
    g = mk([("X", "M", "EVENT_WRITE", 100),
            ("Y", "M", "EVENT_WRITE", 50)])   # both write M; X->M->Y only structural
    kind, p = link_stages(g, {"X"}, {"Y"}, 8)
    # time-ordered undirected: from X (last ts NEG) -> M via ts100; then M->Y needs
    # edge ts>=100 but Y-M edge is ts50 -> time fails. structural should succeed.
    assert kind in ("structural",), (kind, p)
    assert contiguous(p, {"X"}, {"Y"}), p
    print("ok structural_fallback")


def test_unreachable():
    g = mk([("A", "B", "EVENT_WRITE", 10),
            ("C", "D", "EVENT_WRITE", 20)])
    kind, p = link_stages(g, {"A"}, {"D"}, 8)
    assert kind is None and p == [], (kind, p)
    print("ok unreachable")


def test_shared_entity_zero_hop():
    g = mk([("A", "B", "EVENT_WRITE", 10)])
    kind, p = link_stages(g, {"A"}, {"A"}, 8)
    assert p == [] and kind in ("forward", "infoflow"), (kind, p)
    print("ok shared_entity_zero_hop")


if __name__ == "__main__":
    test_directed_forward()
    test_directed_time_blocked()
    test_infoflow_reversed_edge()
    test_netflow_proc_netflow()
    test_structural_fallback()
    test_unreachable()
    test_shared_entity_zero_hop()
    print("ALL PASSED")
