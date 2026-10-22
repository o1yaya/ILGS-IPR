import argparse
import json
from pathlib import Path

import numpy as np


def read_ply_vertices(path):
    from plyfile import PlyData

    ply = PlyData.read(str(path))
    return ply, ply["vertex"].data


def write_ply_vertices(path, vertices, text=False):
    from plyfile import PlyData, PlyElement

    PlyData([PlyElement.describe(vertices, "vertex")], text=text).write(str(path))


def vertex_xyz(vertices):
    names = vertices.dtype.names or ()
    for key in ("x", "y", "z"):
        if key not in names:
            raise ValueError(f"PLY vertex data is missing '{key}'")
    return np.stack([vertices["x"], vertices["y"], vertices["z"]], axis=1).astype(np.float32)


def estimate_normals(points, k):
    from scipy.spatial import cKDTree

    if len(points) < 3:
        return np.zeros_like(points, dtype=np.float32)

    k = max(3, min(int(k), len(points)))
    tree = cKDTree(points)
    _, neighbors = tree.query(points, k=k)
    center = points.mean(axis=0)
    normals = np.zeros_like(points, dtype=np.float32)

    for idx, neighbor_ids in enumerate(neighbors):
        local = points[np.atleast_1d(neighbor_ids)]
        local = local - local.mean(axis=0, keepdims=True)
        cov = local.T @ local
        _, vecs = np.linalg.eigh(cov)
        normal = vecs[:, 0]
        outward = points[idx] - center
        if np.dot(normal, outward) < 0:
            normal = -normal
        normals[idx] = normal

    norm = np.linalg.norm(normals, axis=1, keepdims=True)
    return (normals / np.maximum(norm, 1e-8)).astype(np.float32)


def apply_normals_if_present(vertices, normals):
    names = vertices.dtype.names or ()
    if not {"nx", "ny", "nz"}.issubset(set(names)):
        return vertices

    clean = vertices.copy()
    clean["nx"] = normals[:, 0]
    clean["ny"] = normals[:, 1]
    clean["nz"] = normals[:, 2]
    return clean


def statistical_filter(points, neighbors, std_ratio):
    from scipy.spatial import cKDTree

    if len(points) <= 3 or neighbors <= 1:
        return np.ones(len(points), dtype=bool), {"enabled": False}

    k = min(int(neighbors) + 1, len(points))
    tree = cKDTree(points)
    dists, _ = tree.query(points, k=k)
    mean_dists = dists[:, 1:].mean(axis=1)
    threshold = float(mean_dists.mean() + float(std_ratio) * mean_dists.std())
    keep = mean_dists <= threshold

    return keep, {
        "enabled": True,
        "neighbors": int(k - 1),
        "std_ratio": float(std_ratio),
        "threshold": threshold,
        "kept": int(keep.sum()),
        "removed": int((~keep).sum()),
    }


class UnionFind:
    def __init__(self, size):
        self.parent = np.arange(size, dtype=np.int64)
        self.rank = np.zeros(size, dtype=np.int8)

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return int(x)

    def union(self, a, b):
        ra = self.find(int(a))
        rb = self.find(int(b))
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1


def largest_radius_component(points, eps, min_points):
    from scipy.spatial import cKDTree

    if len(points) == 0:
        return np.zeros(0, dtype=bool), {"enabled": False, "reason": "empty"}
    if len(points) < min_points:
        return np.ones(len(points), dtype=bool), {
            "enabled": False,
            "reason": "too_few_points",
            "points": int(len(points)),
        }

    tree = cKDTree(points)
    pairs = tree.query_pairs(float(eps), output_type="ndarray")
    uf = UnionFind(len(points))
    for a, b in pairs:
        uf.union(a, b)

    roots = np.array([uf.find(i) for i in range(len(points))], dtype=np.int64)
    unique, counts = np.unique(roots, return_counts=True)
    order = np.argsort(counts)[::-1]
    unique = unique[order]
    counts = counts[order]

    keep_root = int(unique[0])
    keep = roots == keep_root
    cluster_sizes = [int(v) for v in counts[:20]]

    return keep, {
        "enabled": True,
        "eps": float(eps),
        "neighbor_pairs": int(len(pairs)),
        "component_count": int(len(unique)),
        "largest_component_points": int(keep.sum()),
        "cluster_sizes_top20": cluster_sizes,
    }


def auto_eps(points, neighbor_k, scale, min_eps, max_eps):
    from scipy.spatial import cKDTree

    if len(points) < 3:
        return float(min_eps), {"mode": "fallback", "base_distance": None}

    k = max(2, min(int(neighbor_k), len(points)))
    tree = cKDTree(points)
    dists, _ = tree.query(points, k=k)
    base = float(np.median(dists[:, -1]))
    eps = max(float(min_eps), base * float(scale))
    if max_eps > 0:
        eps = min(eps, float(max_eps))
    return eps, {
        "mode": "auto",
        "neighbor_k": int(k),
        "base_distance": base,
        "scale": float(scale),
        "min_eps": float(min_eps),
        "max_eps": None if max_eps <= 0 else float(max_eps),
    }


def bbox_summary(points):
    if len(points) == 0:
        return {
            "bbox_min": None,
            "bbox_max": None,
            "bbox_center": None,
            "bbox_extent": None,
        }
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = 0.5 * (mins + maxs)
    extent = maxs - mins
    return {
        "bbox_min": mins.astype(float).tolist(),
        "bbox_max": maxs.astype(float).tolist(),
        "bbox_center": center.astype(float).tolist(),
        "bbox_extent": extent.astype(float).tolist(),
    }


def clean_export(args):
    export_dir = Path(args.export_dir).expanduser().resolve()
    input_ply = Path(args.input_ply).expanduser().resolve() if args.input_ply else export_dir / "target_points.ply"
    output_ply = (
        Path(args.output_ply).expanduser().resolve()
        if args.output_ply
        else export_dir / "target_points_clean.ply"
    )

    if not input_ply.exists():
        raise FileNotFoundError(f"Input PLY not found: {input_ply}")

    ply, vertices = read_ply_vertices(input_ply)
    points = vertex_xyz(vertices)
    finite = np.isfinite(points).all(axis=1)
    vertices = vertices[finite]
    points = points[finite]

    stat_keep, stat_report = statistical_filter(points, args.stat_neighbors, args.stat_std_ratio)
    vertices_stat = vertices[stat_keep]
    points_stat = points[stat_keep]

    if args.cluster_eps > 0:
        eps = float(args.cluster_eps)
        eps_report = {"mode": "manual", "eps": eps}
    else:
        eps, eps_report = auto_eps(
            points_stat,
            args.eps_neighbor_k,
            args.eps_scale,
            args.min_eps,
            args.max_eps,
        )

    if args.skip_cluster:
        cluster_keep = np.ones(len(points_stat), dtype=bool)
        cluster_report = {"enabled": False, "reason": "disabled"}
    else:
        cluster_keep, cluster_report = largest_radius_component(points_stat, eps, args.min_cluster_points)

    vertices_clean = vertices_stat[cluster_keep]
    points_clean = points_stat[cluster_keep]

    normals = None
    if not args.skip_normals:
        normals = estimate_normals(points_clean, args.normal_k)
        vertices_clean = apply_normals_if_present(vertices_clean, normals)

    output_ply.parent.mkdir(parents=True, exist_ok=True)
    write_ply_vertices(output_ply, vertices_clean, text=ply.text)
    np.save(export_dir / "target_points_clean.npy", points_clean)
    if normals is not None:
        np.save(export_dir / "target_normals_clean.npy", normals)

    full_input = export_dir / "target_gaussians_full.ply"
    full_output = export_dir / "target_gaussians_full_clean.ply"
    full_report = {"enabled": False}
    if args.clean_full and full_input.exists():
        full_ply, full_vertices = read_ply_vertices(full_input)
        if len(full_vertices) == len(finite):
            full_vertices = full_vertices[finite][stat_keep][cluster_keep]
            if normals is not None:
                full_vertices = apply_normals_if_present(full_vertices, normals)
            write_ply_vertices(full_output, full_vertices, text=full_ply.text)
            full_report = {
                "enabled": True,
                "input": str(full_input),
                "output": str(full_output),
                "points": int(len(full_vertices)),
            }
        else:
            full_report = {
                "enabled": False,
                "reason": "point_count_mismatch",
                "target_points": int(len(finite)),
                "full_points": int(len(full_vertices)),
            }

    report = {
        "export_dir": str(export_dir),
        "input_ply": str(input_ply),
        "output_ply": str(output_ply),
        "input_points": int(len(finite)),
        "finite_points": int(finite.sum()),
        "clean_points": int(len(points_clean)),
        "removed_points": int(len(finite) - len(points_clean)),
        "statistical_filter": stat_report,
        "eps_selection": eps_report,
        "cluster_filter": cluster_report,
        "clean_full_gaussians": full_report,
        "normal_estimation": None
        if args.skip_normals
        else {"method": "knn_pca", "k": int(args.normal_k), "orientation": "outward_from_centroid"},
    }
    report.update(bbox_summary(points_clean))

    report_path = export_dir / "clean_report.json"
    bbox_path = export_dir / "target_bbox_clean.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with bbox_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "source": str(output_ply),
                "points": int(len(points_clean)),
                **bbox_summary(points_clean),
            },
            f,
            indent=2,
        )

    return report


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Clean an exported ILGS query point cloud by removing sparse outliers "
            "and keeping the largest radius-connected component."
        )
    )
    parser.add_argument("--export_dir", required=True, help="Directory produced by export_query_gaussians.py")
    parser.add_argument("--input_ply", default="", help="Defaults to <export_dir>/target_points.ply")
    parser.add_argument("--output_ply", default="", help="Defaults to <export_dir>/target_points_clean.ply")
    parser.add_argument("--stat_neighbors", type=int, default=30)
    parser.add_argument("--stat_std_ratio", type=float, default=1.5)
    parser.add_argument("--cluster_eps", type=float, default=0.0, help="Manual clustering radius; 0 means auto")
    parser.add_argument("--eps_neighbor_k", type=int, default=8)
    parser.add_argument("--eps_scale", type=float, default=4.0)
    parser.add_argument("--min_eps", type=float, default=1e-4)
    parser.add_argument("--max_eps", type=float, default=0.0, help="0 disables max clamp")
    parser.add_argument("--min_cluster_points", type=int, default=20)
    parser.add_argument("--skip_cluster", action="store_true")
    parser.add_argument("--skip_normals", action="store_true")
    parser.add_argument("--normal_k", type=int, default=20)
    parser.add_argument("--clean_full", action="store_true", default=True)
    parser.add_argument("--no_clean_full", dest="clean_full", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    result = clean_export(parse_args())
    print(json.dumps(result, indent=2))
