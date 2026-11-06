#!/usr/bin/env python3
"""Convert OpenVSP exports into the aircraft viewer's model.

Usage: python3 tri_to_viewer_model.py <plane_full.tri> <plane_full.tkey> <plane_degen.csv> <output stem>

Writes <stem>.bin (quantized positions, normals, triangle and outline indices)
and <stem>.json (layout of the .bin plus the surface index ranges).
Uses only the standard library. Run export_aircraft.vspscript in OpenVSP first.

OpenVSP tags whole triangles, so a control surface that crosses the mesh
diagonally gets a sawtooth edge. The degenerate-geometry export holds the true
boundary of each control surface, so the mesh is cut along those lines here and
the tags are replaced by which boundary each piece falls inside.
"""
import array
import collections
import json
import math
import sys

CREASE_DEG = 40.0   # surfaces meeting more sharply than this keep a hard edge
OUTLINE_DEG = 35.0  # edges at least this sharp are drawn as outline lines

CUT_TOLERANCE = 5e-4   # ft: a vertex this close to a cut line counts as on it
SIMPLIFY_TOLERANCE = 0.02  # ft: allowed deviation when thinning a boundary

# Surfaces the viewer can highlight. Everything else is airframe.
HIGHLIGHTED = ["stab", "teFlaps", "leFlaps"]

# Control-surface name in the degenerate-geometry export, the base surface it
# sits on, and the region it becomes. Ailerons and rudders are cut too so their
# outlines stay clean, though they are not highlighted.
CONTROL_SURFACES = {
    "Flaps": ("wing", "teFlaps"),
    "Leading_Edge_Flaps": ("wing", "leFlaps"),
    "Ailerons": ("wing", "aileron"),
    "Vertical_Stab": ("fin", "rudder"),
}


def read_tri(path):
    tok = open(path).read().split()
    nv, nt = int(tok[0]), int(tok[1])
    p = 2
    verts = [tuple(map(float, tok[p + 3 * i: p + 3 * i + 3])) for i in range(nv)]
    p += 3 * nv
    tris = [tuple(int(x) - 1 for x in tok[p + 3 * i: p + 3 * i + 3]) for i in range(nt)]
    p += 3 * nt
    tags = [int(x) for x in tok[p: p + nt]]
    if len(tags) != nt:
        sys.exit("tag count does not match triangle count")
    return verts, tris, tags


def read_tkey(path):
    names = {}
    for line in open(path):
        parts = line.strip().split(",")
        if len(parts) >= 2 and parts[0].isdigit():
            names[int(parts[0])] = parts[1:]
    return names


def read_boundaries(path):
    """Return {control surface full name: [boundary loop, ...]} in x, y, z."""
    loops = collections.defaultdict(list)
    lines = open(path).read().splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("SUBSURF,"):
            full_name = lines[i].split(",")[4].strip()
            while not lines[i].startswith("SUBSURF_BNDY"):
                i += 1
            count = int(lines[i].split(",")[1])
            rows = lines[i + 2: i + 2 + count]  # one comment line, then u,w,x,y,z
            loops[full_name].append([tuple(float(x) for x in r.split(",")[2:5]) for r in rows])
            i += 2 + count
        else:
            i += 1
    return loops


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    n = norm(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n else (0.0, 0.0, 0.0)


def base_region(tag, tag_names, top_of_tag):
    """Name the surface a tag belongs to: wing, fin, stab, or one body per tag."""
    if tag_names[0].startswith("Fuselage"):
        return f"body{tag}"
    if "Stab" in tag_names[1:]:
        return "stab"
    if "Vertical Stab" in tag_names[1:] or top_of_tag > 5.0:
        return "fin"
    return "wing"


def newell_normal(loop):
    total = (0.0, 0.0, 0.0)
    for a, b in zip(loop, loop[1:] + loop[:1]):
        total = (
            total[0] + (a[1] - b[1]) * (a[2] + b[2]),
            total[1] + (a[2] - b[2]) * (a[0] + b[0]),
            total[2] + (a[0] - b[0]) * (a[1] + b[1]),
        )
    return unit(total)


def simplify(points, tolerance):
    """Ramer-Douglas-Peucker on an open 2D polyline."""
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    worst, worst_i = 0.0, 0
    for i in range(1, len(points) - 1):
        d = abs((points[i][0] - a[0]) * dy - (points[i][1] - a[1]) * dx) / length
        if d > worst:
            worst, worst_i = d, i
    if worst <= tolerance:
        return [a, b]
    return simplify(points[: worst_i + 1], tolerance)[:-1] + simplify(points[worst_i:], tolerance)


def simplify_loop(points, tolerance):
    """Thin a closed loop, whose first and last points may coincide."""
    start = points[0]
    far = max(range(len(points)), key=lambda i: math.dist(start, points[i]))
    half = simplify(points[: far + 1], tolerance)[:-1] + simplify(points[far:], tolerance)
    if math.dist(half[0], half[-1]) < 1e-6:
        half = half[:-1]
    return half


def inside(point, polygon):
    x, y = point
    hit = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


class Boundary:
    """One side of a control surface, flattened into the plane of its surface."""

    def __init__(self, loop, region, base, normal, sheet):
        self.region, self.base, self.normal, self.sheet = region, base, normal, sheet
        helper = (1.0, 0.0, 0.0) if abs(normal[0]) < 0.7 else (0.0, 1.0, 0.0)
        self.e1 = unit(cross(normal, helper))
        self.e2 = cross(normal, self.e1)
        flat = [self.flatten(p) for p in loop]
        self.polygon = simplify_loop(flat, SIMPLIFY_TOLERANCE)
        self.lo = [min(p[a] for p in loop) - 0.5 for a in range(3)]
        self.hi = [max(p[a] for p in loop) + 0.5 for a in range(3)]

    def flatten(self, p):
        return (dot(p, self.e1), dot(p, self.e2))

    def near(self, points):
        return all(
            max(p[a] for p in points) >= self.lo[a] and min(p[a] for p in points) <= self.hi[a]
            for a in range(3)
        )


class Cutter:
    """Splits triangles along lines, keeping neighbouring triangles conforming."""

    def __init__(self, verts):
        self.verts = verts
        self.midpoints = {}

    def edge_point(self, u, v, t):
        a, b = self.verts[u], self.verts[v]
        self.verts.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
        m = len(self.verts) - 1
        self.midpoints[(min(u, v), max(u, v))] = m
        return m

    def refine(self, tri):
        """Apply splits already made on this triangle's edges by its neighbours."""
        stack, done = [tri], []
        while stack:
            a, b, c = stack.pop()
            for u, v, w in ((a, b, c), (b, c, a), (c, a, b)):
                m = self.midpoints.get((min(u, v), max(u, v)))
                if m is not None:
                    stack += [(u, m, w), (m, v, w)]
                    break
            else:
                done.append((a, b, c))
        return done

    def cut(self, tri, boundary, a, b):
        """Split tri along the line through flat points a, b if segment a-b touches it."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return [tri]
        nx, ny = -dy / length, dx / length
        flat = [boundary.flatten(self.verts[i]) for i in tri]
        dist = [(p[0] - a[0]) * nx + (p[1] - a[1]) * ny for p in flat]
        side = [0 if abs(d) <= CUT_TOLERANCE else (1 if d > 0 else -1) for d in dist]
        if 1 not in side or -1 not in side:
            return [tri]

        along = []
        for i in range(3):
            j = (i + 1) % 3
            if side[i] * side[j] < 0:
                t = dist[i] / (dist[i] - dist[j])
                px = flat[i][0] + (flat[j][0] - flat[i][0]) * t
                py = flat[i][1] + (flat[j][1] - flat[i][1]) * t
                along.append(((px - a[0]) * dx + (py - a[1]) * dy) / length)
            elif side[i] == 0:
                along.append(((flat[i][0] - a[0]) * dx + (flat[i][1] - a[1]) * dy) / length)
        if max(along) < 0 or min(along) > length:
            return [tri]

        positive, negative = [], []
        for i in range(3):
            j = (i + 1) % 3
            if side[i] >= 0:
                positive.append(tri[i])
            if side[i] <= 0:
                negative.append(tri[i])
            if side[i] * side[j] < 0:
                m = self.edge_point(tri[i], tri[j], dist[i] / (dist[i] - dist[j]))
                positive.append(m)
                negative.append(m)
        pieces = []
        for loop in (positive, negative):
            pieces += [(loop[0], loop[k], loop[k + 1]) for k in range(1, len(loop) - 1)]
        return pieces


def cut_control_surfaces(verts, tris, regions, loops):
    boundaries = []
    for full_name, sides in loops.items():
        for short_name, (base, region) in CONTROL_SURFACES.items():
            if full_name.endswith("_" + short_name):
                if short_name == "Flaps" and "Leading_Edge" in full_name:
                    continue
                normal = newell_normal(sides[0])
                if len(sides) == 2:
                    # The sheet with the larger offset along the normal is its positive side.
                    means = [sum(dot(p, normal) for p in s) / len(s) for s in sides]
                    order = (1, -1) if means[0] >= means[1] else (-1, 1)
                else:
                    order = (0,) * len(sides)
                for loop, sheet in zip(sides, order):
                    boundaries.append(Boundary(loop, region, base, normal, sheet))

    def on_sheet(tri, boundary):
        a, b, c = (verts[i] for i in tri)
        facing = dot(cross(sub(b, a), sub(c, a)), boundary.normal)
        return boundary.sheet == 0 or facing * boundary.sheet >= 0

    cutter = Cutter(verts)
    pieces = list(zip(tris, regions))
    for boundary in boundaries:
        polygon = boundary.polygon
        edges = list(zip(polygon, polygon[1:] + polygon[:1]))
        next_pieces = []
        for tri, region in pieces:
            current = cutter.refine(tri)
            if region == boundary.base:
                for a, b in edges:
                    updated = []
                    for t in current:
                        if boundary.near([verts[i] for i in t]) and on_sheet(t, boundary):
                            updated += cutter.cut(t, boundary, a, b)
                        else:
                            updated.append(t)
                    current = updated
            next_pieces += [(t, region) for t in current]
        pieces = next_pieces

    result = []
    for tri, region in pieces:
        for t in cutter.refine(tri):
            label = region
            centroid = tuple(sum(verts[i][k] for i in t) / 3.0 for k in range(3))
            for boundary in boundaries:
                if (
                    region == boundary.base
                    and boundary.near([centroid])
                    and on_sheet(t, boundary)
                    and inside(boundary.flatten(centroid), boundary.polygon)
                ):
                    label = boundary.region
                    break
            result.append((t, label))
    return result, [(b.region, b.sheet, len(b.polygon)) for b in boundaries]


def corner_angle(p, q, r):
    u, v = unit(sub(q, p)), unit(sub(r, p))
    return math.acos(max(-1.0, min(1.0, dot(u, v))))


def main(tri_path, tkey_path, degen_path, stem):
    verts, tris, tags = read_tri(tri_path)
    names = read_tkey(tkey_path)
    source_counts = (len(verts), len(tris))

    top = collections.defaultdict(lambda: -1e9)
    for t, tag in zip(tris, tags):
        top[tag] = max(top[tag], *(verts[i][2] for i in t))
    regions = [base_region(tag, names[tag], top[tag]) for tag in tags]
    pieces, used = cut_control_surfaces(verts, tris, regions, read_boundaries(degen_path))
    tris = [p[0] for p in pieces]
    tags = [p[1] for p in pieces]

    faces = []  # (i, j, k, unit normal, tag)
    dropped = 0
    volume = 0.0
    for t, tag in zip(tris, tags):
        a, b, c = (verts[i] for i in t)
        n = cross(sub(b, a), sub(c, a))
        if norm(n) < 1e-10:
            dropped += 1
            continue
        volume += dot(a, cross(b, c)) / 6.0
        faces.append((t[0], t[1], t[2], unit(n), tag))

    incident = collections.defaultdict(list)
    edge_faces = collections.defaultdict(list)
    for f, (i, j, k, _, _) in enumerate(faces):
        for v in (i, j, k):
            incident[v].append(f)
        for a, b in ((i, j), (j, k), (k, i)):
            edge_faces[(min(a, b), max(a, b))].append(f)

    # Split each vertex into smoothing fans: faces around it are joined only
    # across shared edges flatter than the crease angle.
    cos_crease = math.cos(math.radians(CREASE_DEG))
    out_pos, out_nrm = [], []
    corner_index = {}
    for v, fs in incident.items():
        parent = {f: f for f in fs}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        by_other = collections.defaultdict(list)
        for f in fs:
            for u in faces[f][:3]:
                if u != v:
                    by_other[u].append(f)
        for shared in by_other.values():
            for x in range(len(shared) - 1):
                for y in range(x + 1, len(shared)):
                    if dot(faces[shared[x]][3], faces[shared[y]][3]) >= cos_crease:
                        parent[find(shared[x])] = find(shared[y])
        fans = collections.defaultdict(list)
        for f in fs:
            fans[find(f)].append(f)
        for fan in fans.values():
            total = (0.0, 0.0, 0.0)
            for f in fan:
                ids = faces[f][:3]
                m = ids.index(v)
                angle = corner_angle(verts[v], verts[ids[(m + 1) % 3]], verts[ids[(m + 2) % 3]])
                n = faces[f][3]
                total = (total[0] + n[0] * angle, total[1] + n[1] * angle, total[2] + n[2] * angle)
            index = len(out_pos)
            out_pos.append(verts[v])
            out_nrm.append(unit(total))
            for f in fan:
                corner_index[(f, v)] = index

    # Triangle indices, grouped so each surface is one contiguous range.
    grouped = collections.OrderedDict((k, []) for k in ["airframe", *HIGHLIGHTED])
    for f, (i, j, k, _, tag) in enumerate(faces):
        key = tag if tag in HIGHLIGHTED else "airframe"
        grouped[key].append((corner_index[(f, i)], corner_index[(f, j)], corner_index[(f, k)]))

    indices = array.array("H")
    surfaces = {}
    for key, tl in grouped.items():
        surfaces[key] = {"start": len(indices), "count": 3 * len(tl)}
        for t in tl:
            indices.extend(t)

    # Outline: sharp edges, plus every boundary between differently tagged surfaces.
    cos_outline = math.cos(math.radians(OUTLINE_DEG))
    lines = array.array("H")
    for (a, b), fs in edge_faces.items():
        if len(fs) >= 2:
            sharp = dot(faces[fs[0]][3], faces[fs[1]][3]) < cos_outline
            border = len({faces[f][4] for f in fs}) > 1
            if not (sharp or border):
                continue
        lines.extend((corner_index[(fs[0], a)], corner_index[(fs[0], b)]))

    if len(out_pos) > 65535:
        sys.exit("too many vertices for 16-bit indices")

    lo = [min(p[a] for p in out_pos) for a in range(3)]
    hi = [max(p[a] for p in out_pos) for a in range(3)]
    span = max(hi[a] - lo[a] for a in range(3))
    positions = array.array("H")
    for p in out_pos:
        positions.extend(round((p[a] - lo[a]) / span * 65535) for a in range(3))
    normals = array.array("h")
    for n in out_nrm:
        normals.extend(round(x * 32767) for x in n)

    if sys.byteorder != "little":
        for buf in (positions, normals, indices, lines):
            buf.byteswap()

    with open(stem + ".bin", "wb") as out:
        for buf in (positions, normals, indices, lines):
            buf.tofile(out)

    meta = {
        "units": "ft",
        "axes": "OpenVSP: +X aft, +Y right wing, +Z up",
        "bounds": {"min": lo, "max": hi},
        "quantizationSpan": span,
        "vertexCount": len(out_pos),
        "indexCount": len(indices),
        "lineIndexCount": len(lines),
        "surfaces": surfaces,
    }
    with open(stem + ".json", "w") as out:
        json.dump(meta, out, indent=2)

    print(f"source: {source_counts[0]} vertices, {source_counts[1]} triangles")
    print(f"after cutting: {len(verts)} vertices, {len(tris)} triangles ({dropped} degenerate dropped)")
    print("boundaries (region, sheet, polygon points):", used)
    print(f"output: {len(out_pos)} vertices, {len(indices) // 3} triangles, {len(lines) // 2} outline edges")
    print(f"signed volume {volume:.1f} ft^3 (positive means outward-facing triangles)")
    print("bounds", [round(x, 3) for x in lo], [round(x, 3) for x in hi])
    print({k: v["count"] // 3 for k, v in surfaces.items()})


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
