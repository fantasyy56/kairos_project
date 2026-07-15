"""
In-memory entity (node) model for the provenance graph.

A CDM record is either an *object* (Subject, NetFlowObject, FileObject, ...) or
an *Event*. Objects become graph nodes; Events become graph edges (see
graph_builder.py). This module owns the node representation and the logic that
turns a raw CDM object body into a normalized Node.

Two CADETS-E3 quirks handled here (both discovered empirically, see
seed_probe.py / seed_probe2.py, not assumed):

  1. File paths are NOT on FileObject in CDM v18. A FileObject only carries a
     uuid + type. The human-readable path shows up on the *Event* that touches
     the file (predicateObjectPath / predicateObject2Path). So a FileObject node
     starts path-less and gets its path back-filled when the graph builder sees
     an event referencing it. See Node.paths.

  2. Subject.cmdLine is almost always null on this DTrace-based source. The
     process image name instead lives in Event.properties.map["exec"]. So a
     Subject node's human name is likewise back-filled from events (Node.exec_names).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# CDM object record types we turn into nodes. Anything not listed still becomes
# a generic node if it is referenced by an edge, so nothing is silently dropped.
OBJECT_TYPES = frozenset({
    "Subject",
    "NetFlowObject",
    "FileObject",
    "UnnamedPipeObject",
    "MemoryObject",
    "SrcSinkObject",
    "RegistryKeyObject",
    "Principal",
    "Host",
})


@dataclass(slots=True)
class Node:
    uuid: str
    kind: str                              # short CDM type, e.g. "Subject", or "Unknown"
    # kind-specific identity (only the relevant ones are populated)
    subtype: Optional[str] = None          # body["type"], e.g. SUBJECT_PROCESS / FILE_OBJECT_FILE
    cid: Optional[int] = None              # pid, for Subject
    parent: Optional[str] = None           # parentSubject uuid, for Subject
    principal: Optional[str] = None        # localPrincipal uuid, for Subject
    local_address: Optional[str] = None    # NetFlowObject
    local_port: Optional[int] = None
    remote_address: Optional[str] = None
    remote_port: Optional[int] = None
    # back-filled from Events (see module docstring)
    paths: set[str] = field(default_factory=set)          # FileObject / any pathful object
    exec_names: set[str] = field(default_factory=set)     # Subject image names seen via events

    def label(self) -> str:
        """Short human label for reporting/graph output.

        Decided by CONTENT (paths/exec_names/remote_address present) rather
        than strictly by `self.kind`, because under the memory-bounded graph
        build (graph_builder.py) a node may be lazily created with
        kind="Unknown" (e.g. it was only ever an edge endpoint, never a
        materialized object record) yet still have had its path/exec
        back-filled from an Event -- we don't want to lose a perfectly good
        "file(/tmp/x)" / "proc(nginx:123)" label just because the kind tag
        itself wasn't set.
        """
        if self.kind == "Subject" or self.exec_names:
            name = sorted(self.exec_names)[0] if self.exec_names else "?"
            pid = f":{self.cid}" if self.cid is not None else ""
            return f"proc({name}{pid})"
        if self.kind == "NetFlowObject" or self.remote_address:
            return f"net({self.remote_address}:{self.remote_port})"
        if self.paths:
            return f"file({sorted(self.paths)[0]})"
        return f"{self.kind}({self.uuid[:8]})"


def node_from_object(short_type: str, body: dict, unwrap) -> Optional[Node]:
    """
    Build a Node from a CDM object body. `unwrap` is raw_reader.unwrap, used to
    strip Avro union wrappers like {"string": ...} / {"int": ...}. Returns None
    if the body has no uuid (shouldn't happen for valid objects).
    """
    uuid = body.get("uuid")
    if not uuid:
        return None

    node = Node(uuid=uuid, kind=short_type)
    node.subtype = body.get("type")

    if short_type == "Subject":
        cid = unwrap(body.get("cid"))
        node.cid = int(cid) if isinstance(cid, (int, str)) and str(cid).lstrip("-").isdigit() else None
        node.parent = unwrap(body.get("parentSubject"))
        node.principal = unwrap(body.get("localPrincipal"))
        cmdline = unwrap(body.get("cmdLine"))
        if cmdline:  # rarely present, but use it when it is
            node.exec_names.add(cmdline.split()[0] if isinstance(cmdline, str) else str(cmdline))

    elif short_type == "NetFlowObject":
        node.local_address = unwrap(body.get("localAddress"))
        node.local_port = unwrap(body.get("localPort"))
        node.remote_address = unwrap(body.get("remoteAddress"))
        node.remote_port = unwrap(body.get("remotePort"))

    return node
