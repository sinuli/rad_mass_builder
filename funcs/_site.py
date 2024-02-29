# -*- coding:utf-8 -*-
# pylint: disable=bare-except
try:
    from typing import List, Tuple, Dict, Any, Optional
except ImportError:
    pass

from funcs._utils import (
    is_pt_inside,
    get_difference_regions,
    get_intersection_regions,
    get_points_in_boundary,
)


class SitePoint:
    def __init__(self, point):
        self.point = point
        self.is_close_street = False
        self.is_close_park = False
        self.is_on_slope = False
        self.is_on_forest_entrance = False

    def evaluate(self, param_geom):
        for key, geom in param_geom.items():
            if key == "close_street" and is_pt_inside(self.point, geom):
                self.is_close_street = True
            if key == "close_park" and is_pt_inside(self.point, geom):
                self.is_close_park = True
            if key == "on_slope" and is_pt_inside(self.point, geom):
                self.is_on_slope = True
            if key == "on_forest_entrance" and is_pt_inside(self.point, geom):
                self.is_on_forest_entrance = True


class Site:
    def __init__(self, boundary, point_dist, param_geoms):
        self.boundary = boundary
        self.points = []
        self.point_dist = point_dist
        self.param_geoms = param_geoms
        self.street_geom = param_geoms["close_street"]
        self.park_geom = param_geoms["close_park"]
        self.slope_geom = param_geoms["on_slope"]
        self.forest_entrance_geom = param_geoms["on_forest_entrance"]
        self.conditions = None
        self._generate_points()
        # self._evaluate_points()

    def get_conditioned_area(self, conditions, offset):
        output = [self.boundary]
        for condition in conditions:
            if condition == "all":
                pass
            if condition == "close_street":
                output = get_intersection_regions(output, self.street_geom)
            if condition == "close_park":
                output = get_intersection_regions(output, self.park_geom)
            if condition == "on_slope":
                output = get_intersection_regions(output, self.slope_geom)
            if condition == "on_forest_entrance":
                output = get_intersection_regions(output, self.forest_entrance_geom)
            if "!" in condition:
                if condition == "!close_street":
                    output = get_difference_regions(output, self.street_geom)
                if condition == "!close_park":
                    output = get_difference_regions(output, self.park_geom)
                if condition == "!on_slope":
                    output = get_difference_regions(output, self.slope_geom)
                if condition == "!on_forest_entrance":
                    output = get_difference_regions(output, self.forest_entrance_geom)
        return output

    def _evaluate_points(self):
        evaluated_points = []
        for point in self.points:
            site_point = SitePoint(point)
            site_point.evaluate(self.param_geoms)
            evaluated_points.append(site_point)
        self.points = evaluated_points

    def _generate_points(self):
        self.points = get_points_in_boundary(self.boundary, self.point_dist)

    def filter_by_condition(self, conditions):
        res = []
        for condition in conditions:
            if condition == "all":
                res.extend(self.points)
                res = list(set(res))
            if condition == "close_street":
                res.extend([point for point in self.points if point.is_close_street])
                res = list(set(res))  # 중복삭제
            if condition == "close_park":
                res.extend([point for point in self.points if point.is_close_park])
                res = list(set(res))  # 중복삭제
            if condition == "on_slope":
                res.extend([point for point in self.points if point.is_on_slope])
                res = list(set(res))  # 중복삭제
            if condition == "on_forest_entrance":
                res.extend(
                    [point for point in self.points if point.is_on_forest_entrance]
                )
                res = list(set(res))  # 중복삭제
            if "!" in condition:
                if condition == "!close_street":
                    res = [point for point in res if not point.is_close_street]
                if condition == "!close_park":
                    res = [point for point in res if not point.is_close_park]
                if condition == "!on_slope":
                    res = [point for point in res if not point.is_on_slope]
                if condition == "!on_forest_entrance":
                    res = [point for point in res if not point.is_on_forest_entrance]

        return res
