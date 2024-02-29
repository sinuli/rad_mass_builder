# -*- coding:utf-8 -*-
# pylint: disable=bare-except
import Rhino.Geometry as geo

# from _radial_mass import RadialAreaGroup
import math

try:
    from typing import List, Tuple, Dict, Any, Optional
except ImportError:
    pass

TOL = 0.001


def check_intersection(curve1: geo.Curve, curve2: geo.Curve) -> bool:
    # Rhino의 Curve 객체로 변환
    rhino_curve1 = curve1.ToNurbsCurve()
    rhino_curve2 = curve2.ToNurbsCurve()

    # 교차점 계산
    intersection_events = geo.Intersect.Intersection.CurveCurve(
        rhino_curve1, rhino_curve2, 0.001, 0.001
    )

    # 교차점이 있는지 여부 확인
    if intersection_events:
        return True
    else:
        return False


def get_points_in_boundary(lot: geo.Curve, step: float) -> List[geo.Point3d]:
    bbox = lot.GetBoundingBox(geo.Plane.WorldXY)

    width = bbox.Max.X - bbox.Min.X
    height = bbox.Max.Y - bbox.Min.Y
    pts = []
    for i in range(math.ceil(width / step)):
        for j in range(math.ceil(height / step)):
            vec_x = geo.Vector3d(step, 0, 0) * i
            vec_y = geo.Vector3d(0, step, 0) * j
            pt = bbox.Min + vec_x + vec_y
            if is_pt_inside(pt, lot):
                pts.append(pt)
    return pts


def extract_points_from_polyline(
    polyline_curve: geo.PolylineCurve,
) -> List[geo.Point3d]:
    if not isinstance(polyline_curve, geo.PolylineCurve):
        print("Input is not a PolylineCurve.")
        return None
    points = []
    for i in range(polyline_curve.PointCount):
        points.append(polyline_curve.Point(i))

    return points


def get_center(crv: geo.PolylineCurve) -> geo.Point3d:
    points = extract_points_from_polyline(crv)
    x_sum = 0
    y_sum = 0
    for point in points:
        x_sum += point.X
        y_sum += point.Y
    center = geo.Point3d(x_sum / len(points), y_sum / len(points), 0)
    return center


def offset_from_lots(crv, distance):
    pass


def offset_extrude(b, height):
    pass


def get_ag_interaval(area_group):
    # type: (RadialAreaGroup) -> List[geo.Interval]
    """area_group의 angle interval을 구한다. RadialArea구하는 방식을 보면
    0보다 작은 부분은 음수처리 되어 있다. 그러므로 음수인 인터벌은 두개로 나눠서
    양수인 부분 + 음수인 부분 +2pi 로 처리할 것"""
    start = area_group.radial_area.a1
    end = area_group.radial_area.a2
    if start < 0:
        start += math.pi * 2
        return [geo.Interval(0, end), geo.Interval(start, math.pi * 2)]
    else:
        return [geo.Interval(start, end)]


def check_interval_intersection(intervals_1, intervals_2):

    for interval_part_1 in intervals_1:
        for interval_part_2 in intervals_2:

            intersection = geo.Interval.FromIntersection(
                interval_part_1, interval_part_2
            )

            if intersection.Length > 0.2:
                return True
    return False


def check_area_group_intersection(area_group_1, area_group_2):
    intervals_1 = get_ag_interaval(area_group_1)
    intervals_2 = get_ag_interaval(area_group_2)
    return check_interval_intersection(intervals_1, intervals_2)


def get_joined_curve(crvs):
    joined = list(geo.Curve.JoinCurves(crvs, TOL))
    if len(joined) == 1:
        return joined[0]
    else:
        raise Exception("check this curve")


def move_curve(crv_to_move, vec):
    # type: (geo.Curve, geo.Vector3d) -> geo.Curve
    crv_moved = crv_to_move.DuplicateCurve()
    crv_moved.Translate(vec)
    return crv_moved


def is_pt_inside(pt, curve):
    point_containment = curve.Contains(pt, geo.Plane.WorldXY, TOL)

    return point_containment in [
        geo.PointContainment.Inside,
        geo.PointContainment.Coincident,
    ]


def get_intersection_regions(curve1, curve2):
    return geo.Curve.CreateBooleanIntersection(curve1, curve2, TOL)


def get_difference_regions(curve1, curve2):
    return geo.Curve.CreateBooleanDifference(curve1, curve2, TOL)


# def _polyline_boolean(
#         self, crvs0, crvs1, boolean_type=None, plane=None, tol=TOL
#     ):
#         # type: (List[geo.Curve], List[geo.Curve], int, geo.Plane, float) -> List[geo.Curve]
#         if not crvs0 or not crvs1:
#             raise ValueError("Check input values")
#         return ghcomp.ClipperComponents.PolylineBoolean(
#             crvs0, crvs1, boolean_type, plane, tol
#         )

# def polyline_boolean_intersection(self, crvs0, crvs1, plane=None, tol=TOL):
#     # type: (Union[geo.Curve, List[geo.Curve]], Union[geo.Curve, List[geo.Curve]], geo.Plane, float) -> List[geo.Curve]
#     return self._polyline_boolean(crvs0, crvs1, 0, plane, tol)

# def polyline_boolean_union(self, crvs0, crvs1, plane=None, tol=TOL):
#     # type: (Union[geo.Curve, List[geo.Curve]], Union[geo.Curve, List[geo.Curve]], geo.Plane, float) -> List[geo.Curve]
#     return self._polyline_boolean(crvs0, crvs1, 1, plane, tol)

# def polyline_boolean_difference(self, crvs0, crvs1, plane=None, tol=TOL):
#     # type: (Union[geo.Curve, List[geo.Curve]], Union[geo.Curve, List[geo.Curve]], geo.Plane, float) -> List[geo.Curve]
#     return self._polyline_boolean(crvs0, crvs1, 2, plane, tol)

# def polyline_boolean_xor(self, crvs0, crvs1, plane=None, tol=TOL):
#     # type: (Union[geo.Curve, List[geo.Curve]], List[geo.Curve], geo.Plane, float) -> List[geo.Curve]
#     return self._polyline_boolean(crvs0, crvs1, 3, plane, tol)
