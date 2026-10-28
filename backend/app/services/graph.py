"""Dependency-graph rules for work item links."""

import uuid
from collections import defaultdict, deque
from collections.abc import Iterable


def find_path(
    edges: Iterable[tuple[uuid.UUID, uuid.UUID]], start: uuid.UUID, goal: uuid.UUID
) -> list[uuid.UUID] | None:
    """Breadth-first search over directed edges; returns the node path start→goal, if any."""
    adjacency: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for src, dst in edges:
        adjacency[src].append(dst)
    previous: dict[uuid.UUID, uuid.UUID | None] = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == goal:
            path: list[uuid.UUID] = []
            cursor: uuid.UUID | None = node
            while cursor is not None:
                path.append(cursor)
                cursor = previous[cursor]
            return list(reversed(path))
        for nxt in adjacency[node]:
            if nxt not in previous:
                previous[nxt] = node
                queue.append(nxt)
    return None


def cycle_if_added(
    edges: Iterable[tuple[uuid.UUID, uuid.UUID]], source: uuid.UUID, target: uuid.UUID
) -> list[uuid.UUID] | None:
    """Adding source→target closes a cycle iff target already reaches source.

    Returns the resulting cycle (source → target → … → source) or None.
    """
    path = find_path(edges, target, source)
    if path is None:
        return None
    return [source, *path]
