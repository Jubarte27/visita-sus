import math
import random
import sys

import geopandas as gpd
import networkx as nx
import osmnx as ox


def load_and_preprocess(gpkg_path, graphml_path, layer_name=None):
    G = ox.load_graphml(graphml_path, edge_dtypes={
            "oneway": str, 
            "reversed": str, 
            "bridge": str, 
            "tunnel": str,
            "junction": str
        })
    points_gdf = gpd.read_file(gpkg_path, layer=layer_name)

    if points_gdf.crs != "EPSG:4326":
        points_gdf = points_gdf.to_crs(epsg=4326)

    lons = points_gdf.geometry.x.values
    lats = points_gdf.geometry.y.values
    nearest_nodes = ox.distance.nearest_nodes(G, X=lons, Y=lats)
    points_gdf["mapped_node"] = nearest_nodes

    return G, points_gdf


def build_cost_matrix(G, unique_nodes, weight="length"):
    cost_matrix = {}
    for source in unique_nodes:
        lengths = nx.single_source_dijkstra_path_length(G, source, weight=weight)
        cost_matrix[source] = lengths
    return cost_matrix


def greedy_orienteering_solver(
    G,
    points_gdf,
    max_budget,
    start_idx=0,
    end_idx=None,
    value_col="profit",
    service_cost_col="cost",
    tw_start_col=None,
    tw_end_col=None,
    weight="length",
    alpha=1.0,
):
    """
    Efficiency Metric: Score(v) = Value(v) / (Travel Cost + Wait Time + Service Cost)^alpha
    """
    if end_idx is None:
        end_idx = start_idx

    # if value_col not in points_gdf.columns:
    #     points_gdf[value_col] = 10.0
    # if service_cost_col not in points_gdf.columns:
    #     points_gdf[service_cost_col] = 5.0

    unique_nodes = list(points_gdf["mapped_node"].unique())
    cost_matrix = build_cost_matrix(G, unique_nodes, weight=weight)

    start_node = points_gdf.loc[start_idx, "mapped_node"]
    end_node = points_gdf.loc[end_idx, "mapped_node"]

    current_node = start_node
    current_time = 0.0
    total_value = 0.0

    visited_indices = {start_idx}
    route_points = [start_idx]
    route_nodes = [start_node]

    total_value += points_gdf.loc[start_idx, value_col]
    current_time += points_gdf.loc[start_idx, service_cost_col]

    while True:
        best_candidate = None
        best_score = -1.0
        best_candidate_departure = 0.0

        for idx, row in points_gdf.iterrows():
            if idx in visited_indices:
                continue

            target_node = row["mapped_node"]

            if target_node not in cost_matrix[current_node]:
                continue
            
            travel_cost = cost_matrix[current_node][target_node]
            service_cost = row[service_cost_col]
            point_value = row[value_col]

            arrival_time = current_time + travel_cost
            wait_time = 0.0

            if tw_start_col and tw_end_col:
                tw_start = row[tw_start_col]
                tw_end = row[tw_end_col]

                if arrival_time > tw_end:
                    continue

                if arrival_time < tw_start:
                    wait_time = tw_start - arrival_time

            departure_time = arrival_time + wait_time + service_cost

            if target_node not in cost_matrix or end_node not in cost_matrix[target_node]:
                continue

            return_travel_cost = cost_matrix[target_node][end_node]
            total_projected_cost = departure_time + return_travel_cost

            if total_projected_cost > max_budget:
                continue

            effective_duration = travel_cost + wait_time + service_cost
            score = point_value / (effective_duration ** alpha)

            if score > best_score:
                best_score = score
                best_candidate = idx
                best_candidate_departure = departure_time

        if best_candidate is None:
            break

        cand_row = points_gdf.loc[best_candidate]
        visited_indices.add(best_candidate)
        route_points.append(best_candidate)
        route_nodes.append(cand_row["mapped_node"])

        current_node = cand_row["mapped_node"]
        current_time = best_candidate_departure
        total_value += cand_row[value_col]

    if current_node != end_node:
        return_cost = cost_matrix[current_node][end_node]
        current_time += return_cost
        route_nodes.append(end_node)

    full_path_nodes = []
    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i + 1]
        if u == v:
            continue
        try:
            path = nx.shortest_path(G, u, v, weight=weight)
            if full_path_nodes:
                full_path_nodes.extend(path[1:])
            else:
                full_path_nodes.extend(path)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

    if len(full_path_nodes) >= 2 and len(set(full_path_nodes)) >= 2:
        route_edges_gdf = ox.routing.route_to_gdf(G, full_path_nodes, weight=weight)
    else:
        graph_crs = G.graph.get("crs", "EPSG:4326")
        route_edges_gdf = gpd.GeoDataFrame(geometry=[], crs=graph_crs)

    results = {
        "visited_point_indices": route_points,
        "total_value": total_value,
        "total_cost_spent": current_time,
        "max_budget": max_budget,
        "visited_points_gdf": points_gdf.loc[list(visited_indices)],
        "full_route_nodes": full_path_nodes,
        "full_route_edges_gdf": route_edges_gdf,
    }

    return results


class ALNSOrienteeringSolver:
    def __init__(
        self,
        G,
        points_gdf,
        cost_matrix,
        max_budget,
        start_idx=0,
        end_idx=0,
        value_col="profit",
        service_cost_col="cost",
        tw_start_col=None,
        tw_end_col=None,
        weight="length",
    ):
        self.G = G
        self.points_gdf = points_gdf
        self.cost_matrix = cost_matrix
        self.max_budget = max_budget
        self.start_idx = start_idx
        self.end_idx = end_idx

        self.value_col = value_col
        self.service_cost_col = service_cost_col
        self.tw_start_col = tw_start_col
        self.tw_end_col = tw_end_col
        self.weight = weight

        # Pre-extract point data arrays for high-performance iteration
        self.mapped_nodes = points_gdf["mapped_node"].to_dict()
        self.values = points_gdf[value_col].to_dict()
        self.service_costs = points_gdf[service_cost_col].to_dict()

        self.tw_starts = (
            points_gdf[tw_start_col].to_dict() if tw_start_col else None
        )
        self.tw_ends = points_gdf[tw_end_col].to_dict() if tw_end_col else None

        self.all_indices = set(points_gdf.index)

        # Destroy & Repair operators lists
        self.destroy_operators = [
            self.destroy_random,
            self.destroy_worst_efficiency,
            self.destroy_shaw,
            self.destroy_segment,
            self.destroy_expensive_edges,
        ]
        self.repair_operators = [
            self.repair_greedy_insertion,
            self.repair_regret_2_insertion,
            self.repair_add_unvisited,
            self.repair_cheapest_insertion,
            self.repair_cluster_insertion,
        ]

        # Operator statistics & weights
        self.destroy_weights = [1.0] * len(self.destroy_operators)
        self.repair_weights = [1.0] * len(self.repair_operators)

    # ==========================================
    # Feasibility & Evaluation Logic
    # ==========================================
    def evaluate_route(self, route):
        """
        Calculates total value, total duration, and feasibility of a route.
        Route format: list of point indices [start_idx, p1, p2, ..., end_idx]
        """
        current_time = 0.0
        total_value = 0.0

        for i in range(len(route) - 1):
            curr_pt = route[i]
            next_pt = route[i + 1]

            curr_node = self.mapped_nodes[curr_pt]
            next_node = self.mapped_nodes[next_pt]

            # Add service time & value of current point (if not end return node)
            if i == 0 or curr_pt != self.end_idx:
                total_value += self.values[curr_pt]
                current_time += self.service_costs[curr_pt]

            # Travel cost to next node
            if next_node not in self.cost_matrix[curr_node]:
                return -1.0, float("inf"), False  # Unreachable path

            travel_cost = self.cost_matrix[curr_node][next_node]
            arrival_time = current_time + travel_cost

            # Check Time Windows if active
            wait_time = 0.0
            if self.tw_starts and self.tw_ends:
                if arrival_time > self.tw_ends[next_pt]:
                    return -1.0, float("inf"), False  # Late arrival
                if arrival_time < self.tw_starts[next_pt]:
                    wait_time = self.tw_starts[next_pt] - arrival_time

            current_time = arrival_time + wait_time

        is_feasible = current_time <= self.max_budget
        return total_value, current_time, is_feasible

    def _get_insertion_cost(self, route, idx, point_idx):
        """
        Evaluates insertion of `point_idx` into `route` at index `idx`.
        Returns (is_feasible, new_duration, value_gain)
        """
        temp_route = route[:idx] + [point_idx] + route[idx:]
        _, duration, feasible = self.evaluate_route(temp_route)
        if not feasible:
            return False, float("inf"), 0.0
        return True, duration, self.values[point_idx]

    # ==========================================
    # Destroy Operators
    # ==========================================
    def destroy_random(self, route, q):
        """Removes q random non-terminal points."""
        removable = route[1:-1]
        if not removable:
            return route, []
        q = min(q, len(removable))
        removed = random.sample(removable, q)
        removed_set = set(removed)
        new_route = [p for p in route if p not in removed_set]
        return new_route, removed

    def destroy_worst_efficiency(self, route, q):
        """Removes q points with the lowest profit per detour time."""
        removable = route[1:-1]
        if not removable:
            return route, []
        q = min(q, len(removable))

        efficiencies = []
        _, base_dur, _ = self.evaluate_route(route)

        for p in removable:
            p_idx_in_route = route.index(p)
            temp_route = [node for i, node in enumerate(route) if i != p_idx_in_route]
            _, new_dur, _ = self.evaluate_route(temp_route)
            time_saved = max(0.001, base_dur - new_dur)
            efficiency = self.values[p] / time_saved
            efficiencies.append((efficiency, p))

        efficiencies.sort(key=lambda x: x[0])
        removed = [p for _, p in efficiencies[:q]]
        removed_set = set(removed)
        new_route = [p for p in route if p not in removed_set]
        return new_route, removed

    def destroy_shaw(self, route, q):
        """Removes q points that are spatially close to a randomly selected seed point."""
        removable = route[1:-1]
        if not removable:
            return route, []
        q = min(q, len(removable))

        seed = random.choice(removable)
        seed_node = self.mapped_nodes[seed]

        # Sort remaining nodes by distance to seed
        distances = []
        for p in removable:
            p_node = self.mapped_nodes[p]
            dist = self.cost_matrix[seed_node].get(p_node, float("inf"))
            distances.append((dist, p))

        distances.sort(key=lambda x: x[0])
        removed = [p for _, p in distances[:q]]
        removed_set = set(removed)
        new_route = [p for p in route if p not in removed_set]
        return new_route, removed

    def destroy_segment(self, route, q):
        """Removes a contiguous segment of q non-terminal points, creating a larger budget window to insert new sub-paths."""
        removable_len = len(route) - 2
        if removable_len <= 0:
            return route, []
        q = min(q, removable_len)
        max_start = len(route) - 1 - q
        start = random.randint(1, max_start)
        removed = route[start : start + q]
        new_route = route[:start] + route[start + q :]
        return new_route, removed

    def destroy_expensive_edges(self, route, q):
        """Removes points associated with the highest detour / travel distances, freeing budget to add multiple closer points."""
        removable = route[1:-1]
        if not removable:
            return route, []
        q = min(q, len(removable))

        detours = []
        for i in range(1, len(route) - 1):
            p = route[i]
            prev_node = self.mapped_nodes[route[i - 1]]
            curr_node = self.mapped_nodes[p]
            next_node = self.mapped_nodes[route[i + 1]]
            d_direct = self.cost_matrix[prev_node].get(next_node, float("inf"))
            d_via = (
                self.cost_matrix[prev_node].get(curr_node, float("inf"))
                + self.cost_matrix[curr_node].get(next_node, float("inf"))
            )
            detour = d_via - d_direct + self.service_costs[p]
            detours.append((detour, p))

        detours.sort(key=lambda x: x[0], reverse=True)
        removed = [p for _, p in detours[:q]]
        removed_set = set(removed)
        new_route = [p for p in route if p not in removed_set]
        return new_route, removed

    # ==========================================
    # Repair Operators
    # ==========================================
    def repair_greedy_insertion(self, route, unvisited):
        """Inserts points prioritizing maximum value density (Value / Duration Increase)."""
        current_route = list(route)
        unvisited_set = set(unvisited)

        while unvisited_set:
            best_candidate = None
            best_pos = -1
            best_efficiency = -1.0

            _, old_dur, _ = self.evaluate_route(current_route)

            for p in unvisited_set:
                for pos in range(1, len(current_route)):
                    feasible, new_dur, val_gain = self._get_insertion_cost(
                        current_route, pos, p
                    )
                    if feasible:
                        dur_inc = new_dur - old_dur
                        efficiency = val_gain / max(0.001, dur_inc)
                        if efficiency > best_efficiency:
                            best_efficiency = efficiency
                            best_candidate = p
                            best_pos = pos

            if best_candidate is None:
                break

            current_route.insert(best_pos, best_candidate)
            unvisited_set.remove(best_candidate)

        return current_route

    def repair_regret_2_insertion(self, route, unvisited):
        """Inserts points based on value-weighted Regret-2 metric."""
        current_route = list(route)
        unvisited_set = set(unvisited)

        while unvisited_set:
            best_regret = -1.0
            best_candidate = None
            best_pos = -1

            for p in unvisited_set:
                insertion_costs = []
                _, old_dur, _ = self.evaluate_route(current_route)
                for pos in range(1, len(current_route)):
                    feasible, new_dur, _ = self._get_insertion_cost(
                        current_route, pos, p
                    )
                    if feasible:
                        insertion_costs.append((new_dur - old_dur, pos))

                insertion_costs.sort(key=lambda x: x[0])

                if not insertion_costs:
                    continue
                elif len(insertion_costs) == 1:
                    # Only one feasible position: high regret because missing it forfeits the point
                    regret = insertion_costs[0][0] * (self.values[p] / max(1.0, insertion_costs[0][0]))
                else:
                    cost_diff = insertion_costs[1][0] - insertion_costs[0][0]
                    regret = cost_diff * (self.values[p] / max(1.0, insertion_costs[0][0]))

                if regret > best_regret:
                    best_regret = regret
                    best_candidate = p
                    best_pos = insertion_costs[0][1]

            if best_candidate is None:
                break

            current_route.insert(best_pos, best_candidate)
            unvisited_set.remove(best_candidate)

        return current_route

    def repair_add_unvisited(self, route, unvisited):
        """
        Expansion-focused repair: inserts never-visited points ranked by raw value
        (not efficiency), so high-value points are inserted while budget slack is largest.
        """
        current_route = list(route)
        sorted_candidates = sorted(unvisited, key=lambda p: self.values[p], reverse=True)

        for p in sorted_candidates:
            best_pos = -1
            best_dur = float("inf")

            for pos in range(1, len(current_route)):
                feasible, new_dur, _ = self._get_insertion_cost(current_route, pos, p)
                if feasible and new_dur < best_dur:
                    best_dur = new_dur
                    best_pos = pos

            if best_pos != -1:
                current_route.insert(best_pos, p)

        return current_route

    def repair_cheapest_insertion(self, route, unvisited):
        """
        Stops-maximization repair: greedily inserts unvisited points with the minimum
        duration increase, packing as many visited points as possible into available budget.
        """
        current_route = list(route)
        unvisited_set = set(unvisited)

        while unvisited_set:
            best_candidate = None
            best_pos = -1
            best_dur_inc = float("inf")
            _, old_dur, _ = self.evaluate_route(current_route)

            for p in unvisited_set:
                for pos in range(1, len(current_route)):
                    feasible, new_dur, _ = self._get_insertion_cost(current_route, pos, p)
                    if feasible:
                        dur_inc = new_dur - old_dur
                        if dur_inc < best_dur_inc:
                            best_dur_inc = dur_inc
                            best_candidate = p
                            best_pos = pos

            if best_candidate is None:
                break

            current_route.insert(best_pos, best_candidate)
            unvisited_set.remove(best_candidate)

        return current_route

    def repair_cluster_insertion(self, route, unvisited):
        """
        Inserts a candidate point and immediately attempts to insert its closest spatial
        unvisited neighbors adjacent to it, amortizing detour costs across nearby stops.
        """
        current_route = list(route)
        unvisited_set = set(unvisited)
        if not unvisited_set:
            return current_route

        # Seed selection: point with best efficiency
        best_candidate = None
        best_pos = -1
        best_efficiency = -1.0
        _, old_dur, _ = self.evaluate_route(current_route)

        for p in unvisited_set:
            for pos in range(1, len(current_route)):
                feasible, new_dur, val_gain = self._get_insertion_cost(current_route, pos, p)
                if feasible:
                    dur_inc = new_dur - old_dur
                    eff = val_gain / max(0.001, dur_inc)
                    if eff > best_efficiency:
                        best_efficiency = eff
                        best_candidate = p
                        best_pos = pos

        if best_candidate is None:
            return current_route

        current_route.insert(best_pos, best_candidate)
        unvisited_set.remove(best_candidate)

        # Try to insert neighbors of the seed in adjacent positions
        seed_node = self.mapped_nodes[best_candidate]
        neighbors = sorted(
            list(unvisited_set),
            key=lambda p: self.cost_matrix[seed_node].get(self.mapped_nodes[p], float("inf")),
        )

        for neighbor in neighbors:
            cand_pos = current_route.index(best_candidate)
            best_n_pos = -1
            best_n_dur = float("inf")
            for p_try in [cand_pos, cand_pos + 1]:
                if 1 <= p_try < len(current_route):
                    feasible, n_dur, _ = self._get_insertion_cost(current_route, p_try, neighbor)
                    if feasible and n_dur < best_n_dur:
                        best_n_dur = n_dur
                        best_n_pos = p_try
            if best_n_pos != -1:
                current_route.insert(best_n_pos, neighbor)
                unvisited_set.remove(neighbor)

        # Fill any remaining feasible points with cheapest insertion
        return self.repair_cheapest_insertion(current_route, list(unvisited_set))

    def _fill_remaining_budget(self, route):
        """
        Exhaustively packs any unvisited points into the route.
        Pass 1: Packs points prioritizing profit density (Value / Detour).
        Pass 2: Packs any remaining unvisited points by cheapest insertion (Min Detour)
                to ensure all remaining budget slack is used to visit more stops.
        Pass 3: Runs 2-opt to compact the route, and repeats if budget slack was freed.
        """
        current_route = list(route)
        prev_len = -1

        while len(current_route) != prev_len:
            prev_len = len(current_route)

            # Pass 1: Profit density insertion
            unvisited = set(self.all_indices) - set(current_route)
            while unvisited:
                best_candidate = None
                best_pos = -1
                best_efficiency = -1.0
                _, old_dur, _ = self.evaluate_route(current_route)

                for p in unvisited:
                    for pos in range(1, len(current_route)):
                        feasible, new_dur, val_gain = self._get_insertion_cost(
                            current_route, pos, p
                        )
                        if feasible:
                            dur_inc = new_dur - old_dur
                            efficiency = val_gain / max(0.001, dur_inc)
                            if efficiency > best_efficiency:
                                best_efficiency = efficiency
                                best_candidate = p
                                best_pos = pos

                if best_candidate is None:
                    break

                current_route.insert(best_pos, best_candidate)
                unvisited.remove(best_candidate)

            # Pass 2: Cheapest insertion for any remaining points that can fit
            unvisited = set(self.all_indices) - set(current_route)
            while unvisited:
                best_candidate = None
                best_pos = -1
                best_dur_inc = float("inf")
                _, old_dur, _ = self.evaluate_route(current_route)

                for p in unvisited:
                    for pos in range(1, len(current_route)):
                        feasible, new_dur, _ = self._get_insertion_cost(
                            current_route, pos, p
                        )
                        if feasible:
                            dur_inc = new_dur - old_dur
                            if dur_inc < best_dur_inc:
                                best_dur_inc = dur_inc
                                best_candidate = p
                                best_pos = pos

                if best_candidate is None:
                    break

                current_route.insert(best_pos, best_candidate)
                unvisited.remove(best_candidate)

            # Pass 3: 2-opt reordering to compress travel duration
            current_route = self._two_opt(current_route)

        return current_route

    def _two_opt(self, route):
        """Re-orders the route sequence to uncross paths and minimize travel time."""
        if len(route) <= 4:
            return route

        best_route = list(route)
        _, best_dur, _ = self.evaluate_route(best_route)
        improved = True

        while improved:
            improved = False
            for i in range(1, len(best_route) - 2):
                for j in range(i + 1, len(best_route) - 1):
                    # Reverse segment between i and j
                    new_route = (
                        best_route[:i] 
                        + best_route[i : j + 1][::-1] 
                        + best_route[j + 1 :]
                    )
                    _, new_dur, feasible = self.evaluate_route(new_route)
                    if feasible and new_dur < (best_dur - 1e-4):
                        best_route = new_route
                        best_dur = new_dur
                        improved = True
                        break
                if improved:
                    break

        return best_route

    def solve(
        self,
        initial_route,
        iterations=500,
        decay=0.8,
        reaction_factor=0.2,
        t_start=100.0,
        t_cooling=0.99,
    ):
        # Iterative warm-start: alternate fill→2-opt until no new points can be added.
        current_route = list(initial_route)
        current_route = self._fill_remaining_budget(current_route)
        best_route = list(current_route)

        best_val, best_dur, _ = self.evaluate_route(best_route)
        current_val = best_val
        current_dur = best_dur

        temperature = t_start

        # Operator Performance Trackers
        d_scores = [0.0] * len(self.destroy_operators)
        d_counts = [0] * len(self.destroy_operators)
        r_scores = [0.0] * len(self.repair_operators)
        r_counts = [0] * len(self.repair_operators)

        # Rewards for Operator Weighting
        R_BEST = 10.0
        R_BETTER = 5.0
        R_ACCEPTED = 2.0

        for it in range(1, iterations + 1):
            # Select operators via Roulette Wheel
            d_idx = random.choices(
                range(len(self.destroy_operators)), weights=self.destroy_weights
            )[0]
            r_idx = random.choices(
                range(len(self.repair_operators)), weights=self.repair_weights
            )[0]

            d_op = self.destroy_operators[d_idx]
            r_op = self.repair_operators[r_idx]

            # Destroy step (remove between 15% and 45% of nodes)
            num_removable = max(1, len(current_route) - 2)
            q = max(2, int(num_removable * random.uniform(0.15, 0.45)))

            destroyed_route, removed = d_op(current_route, q)
            unvisited = list(self.all_indices - set(destroyed_route))

            repaired_route = r_op(destroyed_route, unvisited)
            optimized_route = self._two_opt(repaired_route)
            candidate_route = self._fill_remaining_budget(optimized_route)

            cand_val, cand_dur, cand_feasible = self.evaluate_route(candidate_route)

            # Evaluate acceptance criterion
            reward = 0.0
            if cand_feasible:
                cand_len = len(candidate_route)
                best_len = len(best_route)
                curr_len = len(current_route)

                is_new_global_best = (
                    (cand_val > best_val)
                    or (cand_val == best_val and cand_len > best_len)
                    or (cand_val == best_val and cand_len == best_len and cand_dur < best_dur - 1e-4)
                )

                if is_new_global_best:
                    best_route = list(candidate_route)
                    best_val = cand_val
                    best_dur = cand_dur
                    current_route = list(candidate_route)
                    current_val = cand_val
                    current_dur = cand_dur
                    reward = R_BEST
                elif cand_val > current_val or (cand_val == current_val and cand_len > curr_len):
                    current_route = list(candidate_route)
                    current_val = cand_val
                    current_dur = cand_dur
                    reward = R_BETTER
                elif cand_val == current_val and cand_dur < current_dur - 1e-4:
                    current_route = list(candidate_route)
                    current_val = cand_val
                    current_dur = cand_dur
                    reward = R_ACCEPTED
                else:
                    # Simulated Annealing acceptance
                    # Combines value difference and visited stops difference
                    delta = (cand_val - current_val) + 5.0 * (cand_len - curr_len)
                    prob = math.exp(delta / max(0.001, temperature))
                    if random.random() < prob:
                        current_route = list(candidate_route)
                        current_val = cand_val
                        current_dur = cand_dur
                        reward = R_ACCEPTED

            # Accumulate scores for operator updates
            d_scores[d_idx] += reward
            d_counts[d_idx] += 1
            r_scores[r_idx] += reward
            r_counts[r_idx] += 1

            # Update weights periodically (every 25 iterations)
            if it % 25 == 0:
                for i in range(len(self.destroy_operators)):
                    if d_counts[i] > 0:
                        self.destroy_weights[i] = (
                            1 - reaction_factor
                        ) * self.destroy_weights[i] + reaction_factor * (
                            d_scores[i] / d_counts[i]
                        )
                for i in range(len(self.repair_operators)):
                    if r_counts[i] > 0:
                        self.repair_weights[i] = (
                            1 - reaction_factor
                        ) * self.repair_weights[i] + reaction_factor * (
                            r_scores[i] / r_counts[i]
                        )

                # Reset segment trackers
                d_scores = [0.0] * len(self.destroy_operators)
                d_counts = [0] * len(self.destroy_operators)
                r_scores = [0.0] * len(self.repair_operators)
                r_counts = [0] * len(self.repair_operators)

            # Periodically try to expand best_route
            if it % 25 == 0:
                expanded = self._fill_remaining_budget(best_route)
                exp_val, exp_dur, exp_feasible = self.evaluate_route(expanded)
                if exp_feasible:
                    if (
                        (exp_val > best_val)
                        or (exp_val == best_val and len(expanded) > len(best_route))
                        or (exp_val == best_val and len(expanded) == len(best_route) and exp_dur < best_dur - 1e-4)
                    ):
                        best_route = expanded
                        best_val = exp_val
                        best_dur = exp_dur
                        current_route = list(best_route)
                        current_val = best_val
                        current_dur = best_dur

            # Cool temperature
            temperature *= t_cooling

        # Reconstruct detailed OSM street-level node sequence
        full_path_nodes = []
        route_mapped_nodes = [self.mapped_nodes[p] for p in best_route]

        for i in range(len(route_mapped_nodes) - 1):
            u, v = route_mapped_nodes[i], route_mapped_nodes[i + 1]
            if u == v:
                continue
            try:
                path = nx.shortest_path(self.G, u, v, weight=self.weight)
                if full_path_nodes:
                    full_path_nodes.extend(path[1:])
                else:
                    full_path_nodes.extend(path)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

        # Safely convert to GeoDataFrame using the single-node / empty edge fix
        if len(full_path_nodes) >= 2 and len(set(full_path_nodes)) >= 2:
            route_edges_gdf = ox.routing.route_to_gdf(
                self.G, full_path_nodes, weight=self.weight
            )
        else:
            graph_crs = self.G.graph.get("crs", "EPSG:4326")
            route_edges_gdf = gpd.GeoDataFrame(geometry=[], crs=graph_crs)

        final_val, final_dur, _ = self.evaluate_route(best_route)

        # Unique visited points
        distinct_visited = list(dict.fromkeys(best_route))
        unvisited_indices = [p for p in self.all_indices if p not in set(best_route)]

        # Diagnostic: compute minimum detour needed to add any of the unvisited points
        min_detour_needed = float("inf")
        closest_unvisited = None
        for p in unvisited_indices:
            for pos in range(1, len(best_route)):
                temp = best_route[:pos] + [p] + best_route[pos:]
                _, dur, _ = self.evaluate_route(temp)
                detour = dur - final_dur
                if detour < min_detour_needed:
                    min_detour_needed = detour
                    closest_unvisited = p

        return {
            "alns_visited_indices": best_route,
            "distinct_visited_indices": distinct_visited,
            "distinct_visited_count": len(distinct_visited),
            "total_value": final_val,
            "total_cost_spent": final_dur,
            "max_budget": self.max_budget,
            "remaining_budget": self.max_budget - final_dur,
            "visited_points_gdf": self.points_gdf.loc[distinct_visited],
            "unvisited_indices": unvisited_indices,
            "closest_unvisited_point": closest_unvisited,
            "min_detour_needed": min_detour_needed,
            "full_route_nodes": full_path_nodes,
            "full_route_edges_gdf": route_edges_gdf,
        }


# ==========================================
# Execution Pipeline: Greedy -> ALNS Refinement
# ==========================================
if __name__ == "__main__":
    GPKG_FILE = sys.argv[1] or "sampled_points.gpkg"
    GRAPHML_FILE = sys.argv[2] or "vale.graphml"
    MAX_BUDGET = 3000.0

    # 1. Load Data
    G, points_gdf = load_and_preprocess(GPKG_FILE, GRAPHML_FILE)
    unique_nodes = list(points_gdf["mapped_node"].unique())
    cost_matrix = build_cost_matrix(G, unique_nodes, weight="length")
    end_idx = 0

    # 2. Run Initial Greedy Solution
    greedy_output = greedy_orienteering_solver(
        G=G,
        points_gdf=points_gdf,
        max_budget=MAX_BUDGET,
        start_idx=0,
        end_idx=end_idx,
        weight="length",
    )

    greedy_initial_route = list(greedy_output["visited_point_indices"])
    if greedy_initial_route[-1] != end_idx:
        greedy_initial_route.append(end_idx)

    greedy_distinct = len(set(greedy_initial_route))
    print(f"--- Initial Greedy Solution ---")
    print(f"Visited Points: {greedy_distinct} unique stops (route stops: {len(greedy_initial_route)})")
    print(f"Greedy Total Value: {greedy_output['total_value']:.2f}")
    print(f"Greedy Budget Used: {greedy_output['total_cost_spent']:.2f} / {MAX_BUDGET}\n")

    # 3. Instantiate and Run ALNS Refinement
    alns_solver = ALNSOrienteeringSolver(
        G=G,
        points_gdf=points_gdf,
        cost_matrix=cost_matrix,
        max_budget=MAX_BUDGET,
        start_idx=0,
        end_idx=end_idx,
        weight="length",
    )

    alns_output = alns_solver.solve(
        initial_route=greedy_initial_route,
        iterations=300,
        t_start=50.0,
        t_cooling=0.985,
    )

    # 4. Print Refinement Comparison
    alns_distinct = alns_output["distinct_visited_count"]
    print(f"--- ALNS Refined Solution ---")
    print(f"Visited Points: {alns_distinct} unique stops (route stops: {len(alns_output['alns_visited_indices'])})")
    print(f"ALNS Total Value: {alns_output['total_value']:.2f}")
    print(f"ALNS Budget Used: {alns_output['total_cost_spent']:.2f} / {MAX_BUDGET} (Remaining Slack: {alns_output['remaining_budget']:.2f})")
    print(f"Value Improvement: +{alns_output['total_value'] - greedy_output['total_value']:.2f}")
    print(f"Stops Improvement: +{alns_distinct - greedy_distinct}")

    # 5. Diagnostic on Unvisited Points
    if alns_output["unvisited_indices"]:
        print(f"\n--- Unvisited Points Diagnostic ---")
        print(f"Total dataset points: {len(points_gdf)} (Visited: {alns_distinct}, Unvisited: {len(alns_output['unvisited_indices'])})")
        if alns_output["closest_unvisited_point"] is not None:
            closest_idx = alns_output["closest_unvisited_point"]
            min_detour = alns_output["min_detour_needed"]
            print(f"Closest unvisited point is #{closest_idx}, which requires a detour of {min_detour:.2f} to visit and return.")
            if min_detour > alns_output["remaining_budget"]:
                needed_budget = alns_output["total_cost_spent"] + min_detour
                print(f"Cannot add point #{closest_idx}: detour ({min_detour:.2f}) > remaining budget ({alns_output['remaining_budget']:.2f}).")
                print(f"To reach additional points from this dataset, MAX_BUDGET needs to be at least {needed_budget:.1f}.")

    # 6. Export ALNS Results to GeoPackage
    alns_output["full_route_edges_gdf"].to_file("alns_optimized_route.gpkg", layer="route", driver="GPKG")
    alns_output["visited_points_gdf"].to_file("alns_optimized_route.gpkg", layer="visited_points", driver="GPKG")
