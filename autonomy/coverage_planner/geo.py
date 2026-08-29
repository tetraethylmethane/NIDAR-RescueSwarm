"""Local metric frame for mission geometry.

Everything in the coverage planner works in metres, not degrees. A degree of
longitude is 111 km at the equator and 0 km at the pole, so doing geometry
directly in lat/lon silently stretches every shape and every area — and at 13°N
(Chennai) the error is 2.6 %, which is enough to hand one drone a measurably
bigger strip than another.

Equirectangular projection about the polygon centroid. Over a 10 ha area — a few
hundred metres — the distortion is well under a centimetre, far below anything
that matters here.

Convention: **(lat, lon) everywhere in this package**, never (lon, lat). KML is
lon-first and is converted at the boundary by the parser, not here.
"""
from __future__ import annotations

import math

R_EARTH = 6_371_000.0


class Frame:
    """Converts between (lat, lon) degrees and local (x, y) metres.

    x is east, y is north, origin at the reference point.
    """

    def __init__(self, lat0: float, lon0: float) -> None:
        self.lat0 = lat0
        self.lon0 = lon0
        self._m_per_deg_lat = math.pi * R_EARTH / 180.0
        self._m_per_deg_lon = self._m_per_deg_lat * math.cos(math.radians(lat0))

    @classmethod
    def from_points(cls, pts: list[tuple[float, float]]) -> "Frame":
        """Frame centred on the centroid of the given (lat, lon) points."""
        if not pts:
            raise ValueError("no points")
        return cls(sum(p[0] for p in pts) / len(pts),
                   sum(p[1] for p in pts) / len(pts))

    def to_xy(self, lat: float, lon: float) -> tuple[float, float]:
        return ((lon - self.lon0) * self._m_per_deg_lon,
                (lat - self.lat0) * self._m_per_deg_lat)

    def to_latlon(self, x: float, y: float) -> tuple[float, float]:
        return (self.lat0 + y / self._m_per_deg_lat,
                self.lon0 + x / self._m_per_deg_lon)

    def poly_to_xy(self, poly):
        return [self.to_xy(a, b) for a, b in poly]

    def poly_to_latlon(self, poly):
        return [self.to_latlon(x, y) for x, y in poly]


def area(poly: list[tuple[float, float]]) -> float:
    """Shoelace area in square metres. Sign-independent."""
    if len(poly) < 3:
        return 0.0
    s = 0.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def centroid(poly: list[tuple[float, float]]) -> tuple[float, float]:
    """Area centroid, not the vertex mean — they differ for irregular shapes."""
    a = 0.0
    cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(a) < 1e-12:                       # degenerate: fall back to the mean
        n = len(poly)
        return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a))


def principal_axis(poly: list[tuple[float, float]]) -> float:
    """Angle in radians of the polygon's long axis, from +x.

    PCA on the vertices. For a rectangle this returns the direction of the long
    side, which is what the sweep planner wants: transects run ALONG the long
    axis so there are fewer turns, and the region is divided ACROSS it.
    """
    cx, cy = centroid(poly)
    sxx = syy = sxy = 0.0
    for x, y in poly:
        dx, dy = x - cx, y - cy
        sxx += dx * dx
        syy += dy * dy
        sxy += dx * dy
    # Principal eigenvector angle of [[sxx,sxy],[sxy,syy]].
    return 0.5 * math.atan2(2 * sxy, sxx - syy)


def rotate(poly, theta: float):
    c, s = math.cos(theta), math.sin(theta)
    return [(x * c - y * s, x * s + y * c) for x, y in poly]


def clip_halfplane(poly, axis: tuple[float, float], offset: float, keep_below=True):
    """Sutherland–Hodgman clip of `poly` against `axis·p <= offset`.

    Exact for convex polygons, which is what a competition boundary is in every
    case we have seen. On a concave polygon this can bridge across a notch;
    `partition.split` detects concavity and warns rather than silently
    producing a wrong region.
    """
    ax, ay = axis

    def inside(p):
        v = ax * p[0] + ay * p[1]
        return v <= offset if keep_below else v >= offset

    def intersect(p, q):
        pv = ax * p[0] + ay * p[1]
        qv = ax * q[0] + ay * q[1]
        d = qv - pv
        if abs(d) < 1e-12:
            return q
        t = (offset - pv) / d
        return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))

    out = []
    if not poly:
        return out
    for cur, nxt in zip(poly, poly[1:] + poly[:1]):
        ci, ni = inside(cur), inside(nxt)
        if ci:
            out.append(cur)
            if not ni:
                out.append(intersect(cur, nxt))
        elif ni:
            out.append(intersect(cur, nxt))
    return out


def is_convex(poly, tol: float = 1e-9) -> bool:
    """True if every cross product has the same sign."""
    n = len(poly)
    if n < 4:
        return True
    sign = 0
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        cx, cy = poly[(i + 2) % n]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) < tol:
            continue
        s = 1 if cross > 0 else -1
        if sign == 0:
            sign = s
        elif s != sign:
            return False
    return True


def point_in_poly(poly, pt, tol: float = 1e-9) -> bool:
    """Even-odd test, counting a point ON an edge as inside.

    The tolerance is not decoration. Transect ends land exactly on the boundary
    and float rounding puts them a couple of centimetres past it; a knife-edge
    test then reports most of a perfectly good rectangle sweep as out of area.
    """
    x, y = pt
    for i in range(len(poly)):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % len(poly)]
        # on this edge?
        cross = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        if abs(cross) <= tol * max(1.0, abs(bx - ax) + abs(by - ay)):
            if min(ax, bx) - tol <= x <= max(ax, bx) + tol and \
               min(ay, by) - tol <= y <= max(ay, by) + tol:
                return True
    c = False
    for i in range(len(poly)):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % len(poly)]
        if ((ay > y) != (by > y)) and \
           (x < (bx - ax) * (y - ay) / (by - ay + 1e-18) + ax):
            c = not c
    return c


def _segments_properly_cross(p1, p2, p3, p4) -> bool:
    """True only if the two segments cross at an interior point of both."""
    def o(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    d1, d2 = o(p3, p4, p1), o(p3, p4, p2)
    d3, d4 = o(p1, p2, p3), o(p1, p2, p4)
    return d1 * d2 < 0 and d3 * d4 < 0


def segment_inside(poly, a, b, samples: int = 24) -> bool:
    """Does the straight segment a-b stay within `poly`?

    Rejects a segment that properly crosses any edge, then samples the interior
    to catch the case where both ends sit on the boundary but the middle spans
    a notch -- exactly what the cell-to-cell hop does.
    """
    for i in range(len(poly)):
        c = poly[i]
        d = poly[(i + 1) % len(poly)]
        if _segments_properly_cross(a, b, c, d):
            return False
    for j in range(1, samples):
        t = j / samples
        if not point_in_poly(poly, (a[0] + (b[0] - a[0]) * t,
                                    a[1] + (b[1] - a[1]) * t)):
            return False
    return True


def shortest_path_inside(poly, a, b):
    """Waypoints strictly between a and b keeping the path inside `poly`.

    Returns [] when a straight line already works, which is always the case on
    a convex boundary. Otherwise a visibility graph over the polygon vertices,
    nudged a hair inward so a vertex is reachable, and Dijkstra across it.
    Returns None if no interior route exists.
    """
    if segment_inside(poly, a, b):
        return []

    # Use the vertices as they are. An earlier version nudged each one toward
    # the vertex average to make it "reachable", which is wrong on a concave
    # polygon: for a slotted boundary that average lands INSIDE the excluded
    # slot, so the nudge pushed the very corners we need to route around out of
    # the polygon, and the search detoured all the way round the outside.
    # point_in_poly counts a point on an edge as inside, so no nudge is needed.
    nodes = [a, b] + list(poly)

    n = len(nodes)
    adj = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if segment_inside(poly, nodes[i], nodes[j]):
                d = math.dist(nodes[i], nodes[j])
                adj[i].append((j, d))
                adj[j].append((i, d))

    import heapq
    dist = [float("inf")] * n
    prev = [None] * n
    dist[0] = 0.0
    pq = [(0.0, 0)]
    while pq:
        du, u = heapq.heappop(pq)
        if du > dist[u]:
            continue
        if u == 1:
            break
        for v, w in adj[u]:
            if du + w < dist[v]:
                dist[v] = du + w
                prev[v] = u
                heapq.heappush(pq, (dist[v], v))
    if dist[1] == float("inf"):
        return None

    path, cur = [], 1
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return [nodes[i] for i in path[1:-1]]
