"""Skill dependency graph generation.

Node *structure* (what exists, what depends on what) is generated once by the
AI and cached on the SkillMap row. Node *completion* is never stored — it is
always read live from the milestone the node points at, via `merge_progress`,
the same way Goal.progress is computed rather than stored. That is what keeps
the graph from ever showing a topic as "done" that the user later reopened.

A dependency graph that contains a cycle is not really a dependency graph, so
validation actively rejects edges that would introduce one rather than
leaving it to the renderer to cope with.
"""

import logging
import re

from django.conf import settings

from common.exceptions import ServiceError

from apps.goals.services import llm

logger = logging.getLogger(__name__)

MAX_NODES = 20
MAX_EDGES = 36

SYSTEM_PROMPT = """\
You turn a roadmap's milestones into a skill dependency graph.

Reply with ONLY a JSON object. No prose, no markdown fences.

{
  "nodes": [
    { "id": "string - short kebab-case slug, unique in this graph",
      "label": "string - 1 to 4 words naming the skill or topic",
      "milestone_index": 0 }
  ],
  "edges": [
    { "from": "string - a node id", "to": "string - a node id that requires it" }
  ]
}

Rules:
- milestone_index is the 0-based position of the milestone this skill mainly
  belongs to, from the list you are given. Every node must reference a real
  index from that list.
- Produce 1 to 3 nodes per milestone — break a milestone into its real
  sub-topics rather than making one node per milestone. A milestone called
  "Master core algorithms" might become "Sorting", "Searching" and
  "Recursion", for instance.
- An edge from A to B means: you should understand A before B. Prefer real
  prerequisite relationships over just chaining milestones in order — a topic
  from an early milestone often feeds into topics in more than one later
  milestone. A graph that is just a straight line is a worse answer than one
  with genuine branches.
- Never create a cycle (a path that leads back to where it started).
- 8 to 20 nodes total. Do not pad with trivial or repeated topics.
- Never use an em dash in a label.
"""


def build_user_prompt(milestones: list[str]) -> str:
    lines = [f"{index}: {title}" for index, title in enumerate(milestones)]
    return (
        "Milestones, in order:\n" + "\n".join(lines) + "\n\n"
        "Generate the skill graph JSON."
    )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")
    return slug[:40] or "node"


def _would_create_cycle(adjacency: dict[str, set[str]], start: str, target: str) -> bool:
    """True if `target` can already reach `start` — i.e. adding start->target
    would close a loop."""
    stack, seen = [target], {target}
    while stack:
        node = stack.pop()
        if node == start:
            return True
        for neighbour in adjacency.get(node, ()):
            if neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)
    return False


def validate_skill_map(raw, milestone_count: int) -> tuple[list[dict], list[dict]]:
    if not isinstance(raw, dict):
        raise ServiceError(
            "The AI response was not in the expected format.",
            status_code=502,
            code="schema_invalid",
        )

    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ServiceError(
            "The AI did not return any skills. Try again.",
            status_code=502,
            code="schema_no_nodes",
        )

    nodes, seen_ids = [], set()
    for entry in raw_nodes[:MAX_NODES]:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label") or "").strip()[:60]
        if not label:
            continue
        node_id = _slugify(entry.get("id") or label)
        # A duplicate slug (the model repeating an id, or two labels slugifying
        # the same way) would merge two distinct topics into one node.
        if node_id in seen_ids:
            node_id = f"{node_id}-{len(seen_ids)}"
        seen_ids.add(node_id)

        try:
            milestone_index = int(entry.get("milestone_index"))
        except (TypeError, ValueError):
            milestone_index = 0
        milestone_index = max(0, min(milestone_index, milestone_count - 1))

        nodes.append({"id": node_id, "label": label, "milestone_index": milestone_index})

    if not nodes:
        raise ServiceError(
            "The AI response had no usable skills. Try again.",
            status_code=502,
            code="schema_no_valid_nodes",
        )

    valid_ids = {n["id"] for n in nodes}
    raw_edges = raw.get("edges") if isinstance(raw.get("edges"), list) else []

    edges, adjacency, seen_pairs = [], {}, set()
    for entry in raw_edges[:MAX_EDGES]:
        if not isinstance(entry, dict):
            continue
        src = _slugify(entry.get("from") or "")
        dst = _slugify(entry.get("to") or "")
        if src == dst or src not in valid_ids or dst not in valid_ids:
            continue
        if (src, dst) in seen_pairs:
            continue
        if _would_create_cycle(adjacency, src, dst):
            logger.info("Dropping edge %s -> %s: would create a cycle", src, dst)
            continue

        seen_pairs.add((src, dst))
        adjacency.setdefault(src, set()).add(dst)
        edges.append({"from": src, "to": dst})

    return nodes, edges


def _mock_skill_map(milestones: list[str]) -> tuple[list[dict], list[dict]]:
    """Deterministic offline stub: two nodes per milestone chained in order,
    plus one cross-milestone branch so the graph isn't a bare line."""
    nodes, edges = [], []
    previous_tail = None

    for index, title in enumerate(milestones):
        base = _slugify(title)
        first_id, second_id = f"{base}-core", f"{base}-practice"
        nodes.append({"id": first_id, "label": f"{title[:24]} basics", "milestone_index": index})
        nodes.append({"id": second_id, "label": f"{title[:24]} practice", "milestone_index": index})
        edges.append({"from": first_id, "to": second_id})
        if previous_tail:
            edges.append({"from": previous_tail, "to": first_id})
        previous_tail = second_id

        # A branch: the *first* milestone's core skill also feeds the last
        # milestone directly, so the graph has real structure to render.
        if index == 0:
            root_core = first_id
        elif index == len(milestones) - 1 and len(milestones) > 2:
            edges.append({"from": root_core, "to": first_id})

    return nodes[:MAX_NODES], edges[:MAX_EDGES]


def generate_skill_map(goal) -> tuple[list[dict], list[dict]]:
    milestones = list(goal.milestones.order_by("order", "id").values_list("title", flat=True))
    if not milestones:
        raise ServiceError(
            "Add at least one milestone before generating a skill map.",
            status_code=400,
            code="no_milestones",
        )

    if settings.USE_MOCK_AI:
        return _mock_skill_map(milestones)

    payload = llm.complete_json(
        system=SYSTEM_PROMPT,
        user=build_user_prompt(milestones),
        temperature=0.3,
    )
    return validate_skill_map(payload, len(milestones))


def merge_progress(goal, nodes: list[dict]) -> list[dict]:
    """Attach live completion to each node from its milestone's real tasks."""
    milestones = list(goal.milestones.order_by("order", "id").prefetch_related("tasks"))

    merged = []
    for node in nodes:
        index = node.get("milestone_index", 0)
        milestone = milestones[index] if 0 <= index < len(milestones) else None
        if milestone is None:
            merged.append({**node, "progress": 0, "complete": False, "milestone_title": ""})
            continue

        tasks = list(milestone.tasks.all())
        done = sum(1 for t in tasks if t.is_complete)
        progress = round(done * 100 / len(tasks)) if tasks else 0
        merged.append(
            {
                **node,
                "progress": progress,
                "complete": milestone.is_complete or (bool(tasks) and progress == 100),
                "milestone_id": milestone.id,
                "milestone_title": milestone.title,
            }
        )
    return merged
