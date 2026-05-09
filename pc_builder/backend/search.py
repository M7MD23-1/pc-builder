import heapq
from collections import deque
from constraints import (
    cpu_mb_compatible,
    ram_mb_compatible,
    storage_mb_compatible,
    psu_sufficient,
    apply_purpose_pruning,
)

COMPONENT_ORDER = ["cpu", "mb", "ram", "storage", "gpu", "psu"]
MAX_RESULTS = 5


def normalize_purpose_name(purpose):
    text = str(purpose or "").strip()
    aliases = {
        "AI / ML Workstation": "AI Workstation",
        "AI/ML Workstation": "AI Workstation",
    }
    return aliases.get(text, text)


def get_next_component(state, purpose):
    purpose = normalize_purpose_name(purpose)
    for comp in COMPONENT_ORDER:
        if comp in state:
            continue
        if comp == "gpu" and purpose == "Office":
            cpu = state.get("cpu")
            if cpu and cpu.get("integrated_graphics", False):
                continue
        return comp
    return None


def is_compatible(state, comp_type, candidate):
    if comp_type == "mb":
        return cpu_mb_compatible(state["cpu"], candidate)
    if comp_type == "ram":
        return ram_mb_compatible(candidate, state["mb"])
    if comp_type == "storage":
        return storage_mb_compatible(candidate, state["mb"])
    if comp_type == "psu":
        gpu = state.get("gpu", {"tdp_watts": 0})
        return psu_sufficient(candidate, state["cpu"], gpu)
    return True


def normalize_ig(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ["yes", "true", "1", "y"]
    if isinstance(value, (int, float)):
        return value == 1
    return False


def prepare_components(components):
    prepared = {}
    for key, items in components.items():
        clean_key = key.strip()
        prepared_items = []
        for item in items:
            new_item = {k.strip(): v for k, v in item.items()}
            if clean_key == "cpu":
                new_item["integrated_graphics"] = normalize_ig(new_item.get("integrated_graphics", False))
            prepared_items.append(new_item)
        prepared[clean_key] = prepared_items
    return prepared


def sort_components(components, purpose):
    purpose = normalize_purpose_name(purpose)
    sorted_comp = {}

    for key, items in components.items():
        if purpose == "Gaming":
            if key == "gpu":
                sorted_comp[key] = sorted(items, key=lambda x: x.get("vram_gb", 0), reverse=True)
            elif key == "cpu":
                sorted_comp[key] = sorted(items, key=lambda x: x.get("cores", 0), reverse=True)
            elif key == "ram":
                sorted_comp[key] = sorted(items, key=lambda x: x.get("capacity_gb", 0), reverse=True)
            elif key == "psu":
                sorted_comp[key] = sorted(items, key=lambda x: (x.get("wattage", 0), x["price_usd"]), reverse=True)
            else:
                sorted_comp[key] = sorted(items, key=lambda x: x["price_usd"])

        elif purpose == "Office":
            sorted_comp[key] = sorted(items, key=lambda x: x["price_usd"])

        elif purpose == "Content Creation":
            if key == "cpu":
                sorted_comp[key] = sorted(items, key=lambda x: (x.get("cores", 0), x["price_usd"]), reverse=True)
            elif key == "ram":
                sorted_comp[key] = sorted(items, key=lambda x: (x.get("capacity_gb", 0), x["price_usd"]), reverse=True)
            elif key == "storage":
                sorted_comp[key] = sorted(
                    items,
                    key=lambda x: (1 if str(x.get("interface", "")).upper().startswith("NVME") else 0, x["price_usd"]),
                    reverse=True,
                )
            else:
                sorted_comp[key] = sorted(items, key=lambda x: x["price_usd"])

        elif purpose == "AI Workstation":
            if key == "gpu":
                sorted_comp[key] = sorted(items, key=lambda x: (x.get("vram_gb", 0), x["price_usd"]), reverse=True)
            elif key == "psu":
                sorted_comp[key] = sorted(items, key=lambda x: (x.get("wattage", 0), x["price_usd"]), reverse=True)
            elif key == "cpu":
                sorted_comp[key] = sorted(items, key=lambda x: (x.get("cores", 0), x["price_usd"]), reverse=True)
            elif key == "ram":
                sorted_comp[key] = sorted(items, key=lambda x: (x.get("capacity_gb", 0), x["price_usd"]), reverse=True)
            else:
                sorted_comp[key] = sorted(items, key=lambda x: x["price_usd"])

        elif purpose == "Budget Build":
            sorted_comp[key] = sorted(items, key=lambda x: x["price_usd"])

        elif purpose == "High-End Build":
            if key == "gpu":
                sorted_comp[key] = sorted(
                    items,
                    key=lambda x: (x.get("vram_gb", 0), x.get("base_clock_mhz", 0), x["price_usd"]),
                    reverse=True,
                )
            elif key == "cpu":
                sorted_comp[key] = sorted(
                    items,
                    key=lambda x: (x.get("cores", 0), x.get("base_clock_ghz", 0), x["price_usd"]),
                    reverse=True,
                )
            elif key == "ram":
                sorted_comp[key] = sorted(
                    items,
                    key=lambda x: (x.get("capacity_gb", 0), x.get("speed_mhz", 0), x["price_usd"]),
                    reverse=True,
                )
            elif key == "psu":
                sorted_comp[key] = sorted(items, key=lambda x: (x.get("wattage", 0), x["price_usd"]), reverse=True)
            else:
                sorted_comp[key] = sorted(items, key=lambda x: x["price_usd"], reverse=True)

        else:
            sorted_comp[key] = sorted(items, key=lambda x: x["price_usd"])

    return sorted_comp


def limit_candidates(components, purpose):
    # Keep the search tractable without discarding all budget-friendly tails.
    # We keep a diversified subset per component: some cheapest + some top-ranked.
    purpose = normalize_purpose_name(purpose)
    budget_focused = purpose in {"Office", "Budget Build"}
    diversified = {}

    for key, items in components.items():
        if purpose == "Gaming":
            # Gaming must stay performance-first:
            # keep top-ranked CPU/GPU/RAM candidates only and avoid cheap-tail bias.
            if key in {"gpu", "cpu", "ram"}:
                diversified[key] = items[:20]
            else:
                diversified[key] = items[:24]
            continue

        if len(items) <= 30:
            diversified[key] = items
            continue

        cheap_take = 24 if budget_focused else 18
        top_take = 8 if budget_focused else 12

        cheapest = sorted(items, key=lambda x: x["price_usd"])[:cheap_take]
        top_ranked = items[:top_take]

        seen = set()
        merged = []
        for cand in cheapest + top_ranked:
            cand_id = cand.get("name") or id(cand)
            if cand_id in seen:
                continue
            seen.add(cand_id)
            merged.append(cand)

        diversified[key] = merged

    return diversified


def score_build(state, purpose, budget):
    purpose = normalize_purpose_name(purpose)
    price = state["total_price"]
    budget_eff = 1.0 - (price / budget) if budget > 0 else 0.0

    if purpose in ["Office", "Budget Build"]:
        return budget_eff * 0.8

    if purpose == "Gaming":
        perf = (
            state.get("gpu", {}).get("vram_gb", 0) * 0.5
            + state.get("cpu", {}).get("cores", 0) * 0.3
            + state.get("ram", {}).get("capacity_gb", 0) * 0.2
        )
        return perf * 0.6 + budget_eff * 0.4

    if purpose == "Content Creation":
        perf = (
            state.get("cpu", {}).get("cores", 0) * 0.4
            + state.get("ram", {}).get("capacity_gb", 0) * 0.4
            + (1 if str(state.get("storage", {}).get("interface", "")).upper().startswith("NVME") else 0) * 0.2
        )
        return perf * 0.6 + budget_eff * 0.4

    if purpose == "AI Workstation":
        perf = (
            state.get("gpu", {}).get("vram_gb", 0) * 0.7
            + state.get("psu", {}).get("wattage", 0) * 0.3
        )
        return perf * 0.6 + budget_eff * 0.4

    if purpose == "High-End Build":
        perf = (
            state.get("gpu", {}).get("vram_gb", 0) * 0.5
            + state.get("cpu", {}).get("cores", 0) * 0.5
        )
        return perf * 0.7 + budget_eff * 0.3

    return budget_eff


def _allows_gpu_slot(state, purpose):
    if purpose != "Office":
        return True
    cpu = state.get("cpu")
    if not cpu:
        return True
    return not cpu.get("integrated_graphics", False)


def estimate_remaining_cost(state, components, purpose):
    """
    Admissible heuristic for A*:
    h(n) = sum of the minimum available prices for unfinished component slots.
    It ignores compatibility interactions, so it never overestimates true remaining cost.
    """
    remaining = 0.0

    for comp in COMPONENT_ORDER:
        if comp in state:
            continue
        if comp == "gpu" and not _allows_gpu_slot(state, purpose):
            continue

        min_price = None
        for cand in components.get(comp, []):
            if not apply_purpose_pruning(comp, cand, purpose):
                continue
            price = float(cand.get("price_usd", 0))
            if min_price is None or price < min_price:
                min_price = price

        if min_price is not None:
            remaining += min_price

    return remaining


def build_signature(state, purpose):
    purpose = normalize_purpose_name(purpose)
    parts = []
    for comp in COMPONENT_ORDER:
        if comp == "gpu" and purpose == "Office":
            cpu = state.get("cpu")
            if cpu and cpu.get("integrated_graphics", False) and "gpu" not in state:
                parts.append((comp, "__integrated__"))
                continue
        comp_data = state.get(comp)
        parts.append((comp, comp_data.get("name", "__none__") if comp_data else "__none__"))
    return tuple(parts)


def _finalize_build_results(builds, explored, algorithm):
    for build in builds:
        build["explored_states"] = explored
        build["algorithm"] = algorithm
    return builds


def estimate_min_budget(components, purpose):
    """
    Greedy minimum-budget estimator.
    Builds the cheapest purpose-valid compatible configuration in component order.
    Returns None if no valid configuration can be assembled.
    """
    purpose = normalize_purpose_name(purpose)
    components = prepare_components(components)
    by_price = {k: sorted(v, key=lambda x: x.get("price_usd", 0)) for k, v in components.items()}

    state = {"total_price": 0.0}
    for comp in COMPONENT_ORDER:
        if comp == "gpu" and purpose == "Office":
            cpu = state.get("cpu")
            if cpu and cpu.get("integrated_graphics", False):
                continue

        chosen = None
        for cand in by_price.get(comp, []):
            if not apply_purpose_pruning(comp, cand, purpose):
                continue
            if not is_compatible(state, comp, cand):
                continue
            chosen = cand
            break

        if chosen is None:
            return None

        state[comp] = chosen
        state["total_price"] += float(chosen.get("price_usd", 0))

    return round(state["total_price"], 2)


def bfs(components, budget, purpose, max_states=20000):
    purpose = normalize_purpose_name(purpose)
    components = prepare_components(components)
    components = sort_components(components, purpose)
    components = limit_candidates(components, purpose)

    queue = deque([{"total_price": 0}])
    explored = 0
    results = []
    seen_signatures = set()

    while queue:
        state = queue.popleft()
        explored += 1

        if explored >= max_states:
            break

        next_comp = get_next_component(state, purpose)

        if next_comp is None:
            sig = build_signature(state, purpose)
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                results.append(state)
                if len(results) >= MAX_RESULTS:
                    return _finalize_build_results(results, explored, "BFS")
            continue

        for cand in components[next_comp]:
            if not apply_purpose_pruning(next_comp, cand, purpose):
                continue
            new_price = state["total_price"] + cand["price_usd"]
            if new_price > budget:
                continue
            if not is_compatible(state, next_comp, cand):
                continue

            ns = dict(state)
            ns[next_comp] = cand
            ns["total_price"] = new_price
            queue.append(ns)

    if results:
        return _finalize_build_results(results, explored, "BFS")
    return []


def dfs(components, budget, purpose, max_states=20000):
    purpose = normalize_purpose_name(purpose)
    components = prepare_components(components)
    components = sort_components(components, purpose)
    components = limit_candidates(components, purpose)

    stack = [{"total_price": 0}]
    explored = 0
    results = []
    seen_signatures = set()

    while stack:
        state = stack.pop()
        explored += 1

        if explored >= max_states:
            break

        next_comp = get_next_component(state, purpose)

        if next_comp is None:
            sig = build_signature(state, purpose)
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                results.append(state)
                if len(results) >= MAX_RESULTS:
                    return _finalize_build_results(results, explored, "DFS")
            continue

        # Reverse iteration + stack gives canonical depth-first expansion
        # while still respecting the purpose-aware ranking in components[next_comp].
        for cand in reversed(components[next_comp]):
            if not apply_purpose_pruning(next_comp, cand, purpose):
                continue
            new_price = state["total_price"] + cand["price_usd"]
            if new_price > budget:
                continue
            if not is_compatible(state, next_comp, cand):
                continue

            ns = dict(state)
            ns[next_comp] = cand
            ns["total_price"] = new_price
            stack.append(ns)

    if results:
        return _finalize_build_results(results, explored, "DFS")
    return []


def ucs(components, budget, purpose, max_states=20000):
    purpose = normalize_purpose_name(purpose)
    components = prepare_components(components)
    components = sort_components(components, purpose)
    components = limit_candidates(components, purpose)

    counter = 0
    heap = [(0, counter, {"total_price": 0})]
    explored = 0
    results = []
    seen_signatures = set()

    while heap:
        cost, _, state = heapq.heappop(heap)
        explored += 1

        if explored >= max_states:
            break

        next_comp = get_next_component(state, purpose)

        if next_comp is None:
            sig = build_signature(state, purpose)
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                results.append(state)
            continue

        for cand in components[next_comp]:
            if not apply_purpose_pruning(next_comp, cand, purpose):
                continue
            new_price = state["total_price"] + cand["price_usd"]
            if new_price > budget:
                continue
            if not is_compatible(state, next_comp, cand):
                continue

            ns = dict(state)
            ns[next_comp] = cand
            ns["total_price"] = new_price
            counter += 1
            heapq.heappush(heap, (new_price, counter, ns))

    if not results:
        return []

    results = sorted(results, key=lambda x: x["total_price"])[:MAX_RESULTS]
    return _finalize_build_results(results, explored, "UCS")


def astar(components, budget, purpose, max_states=20000):
    purpose = normalize_purpose_name(purpose)
    components = prepare_components(components)
    components = sort_components(components, purpose)
    components = limit_candidates(components, purpose)

    start = {"total_price": 0}
    explored = 0
    counter = 0
    results = []
    seen_signatures = set()

    start_h = estimate_remaining_cost(start, components, purpose)
    heap = [(start_h, counter, start)]
    best_g = {tuple(): 0.0}

    while heap:
        _, _, state = heapq.heappop(heap)
        explored += 1

        if explored >= max_states:
            break

        next_comp = get_next_component(state, purpose)
        if next_comp is None:
            sig = build_signature(state, purpose)
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                results.append(state)
            continue

        for cand in components[next_comp]:
            if not apply_purpose_pruning(next_comp, cand, purpose):
                continue

            new_price = state["total_price"] + cand["price_usd"]
            if new_price > budget:
                continue
            if not is_compatible(state, next_comp, cand):
                continue

            ns = dict(state)
            ns[next_comp] = cand
            ns["total_price"] = new_price

            key = tuple(
                (comp, ns[comp].get("name", ""))
                for comp in COMPONENT_ORDER
                if comp in ns
            )

            prev_best = best_g.get(key)
            if prev_best is not None and new_price >= prev_best:
                continue

            best_g[key] = new_price
            h = estimate_remaining_cost(ns, components, purpose)
            f = new_price + h
            counter += 1
            heapq.heappush(heap, (f, counter, ns))

    if not results:
        return []

    results = sorted(results, key=lambda x: x["total_price"])[:MAX_RESULTS]
    return _finalize_build_results(results, explored, "A*")
