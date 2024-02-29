# -*- coding:utf-8 -*-
# pylint: disable=bare-except
try:
    from typing import List, Tuple, Dict, Any, Optional
except ImportError:
    pass

import Rhino.Geometry as geo  # type: ignore

from funcs._site import Site
from funcs._radial_mass import RadialMass
from funcs._radial_mass import RadialMass
from funcs._area_to_mass import AreaToMass
from funcs.base import MassResult
from copy import deepcopy


def points_from_bounding_box(bounding_rect, step):
    points = bounding_rect.corners
    curve = bounding_rect.crv
    origin_point = geo.Point3d(points[0])
    l1 = geo.Line(points[1], points[0]).Length
    l2 = geo.Line(points[3], points[0]).Length
    v1 = geo.Vector3d(points[1] - points[0])
    v1.Unitize()
    v2 = geo.Vector3d(points[3] - points[0])
    v2.Unitize()
    x_value = []
    y_value = []
    i = 0
    while i * step < l1:
        x_value.append(i * step)
        i += 1
    i = 0
    while i * step < l2:
        y_value.append(i * step)
        i += 1
    points = []
    for x_val in x_value:
        for y_val in y_value:
            points.append(origin_point + x_val * v1 + y_val * v2)
    return points


class RadialMassFinder:
    def __init__(self, site):
        # type: (Site) -> None
        self.site = site
        self.area_A1 = 404
        self.area_A2 = 542
        self.area_B = 94
        self.masses = [
            RadialMass(self.area_A1, "A1", site),
            RadialMass(self.area_A2, "A2", site),
            RadialMass(self.area_B, "B", site),
        ]  # type: List[RadialMass]

    def set_center_point(self, point_a, point_b):
        # B는 서쪽에 배치한다. 경사로와는 거리가 있고, 주차장과 거리가 멀다.
        # A1과 A2는 동쪽에 배치한다. 경사로와는 관계가 없다. boundary에서 적절한 지점을 찾는다.
        # A1과 A2는 같은 center를 사용한다.
        # 임시로 center를 부여하도록 한다.
        self.masses[0].set_center(point_a)
        self.masses[1].set_center(point_a)
        self.masses[2].set_center(point_b)

    def set_extend_condition(self, condition_a1, condition_a2, condition_b):
        self.masses[0].set_condition(condition_a1)
        self.masses[1].set_condition(condition_a2)
        self.masses[2].set_condition(condition_b)

    @property
    def geometry(self):
        shapes = []
        for mass in self.masses:
            shapes.append(mass.geom)
        return shapes

    def generate_masses(self):
        for mass in self.masses:
            mass.generate()

    def load_detail_area(self):
        """json 파일을 읽어서 각 mass에 면적을 부여한다."""
        import json
        import os

        path_folder = "C:\\Users\\User\\Documents\\computational_design\\narrative_architects\\funcs"

        with open(os.path.join(path_folder, "area_detail_a1.json"), "r") as f:
            self.area_option_a1 = json.load(f)
        with open(os.path.join(path_folder, "area_detail_a2.json"), "r") as f:
            self.area_option_a2 = json.load(f)
        with open(os.path.join(path_folder, "area_detail_b.json"), "r") as f:
            self.area_option_b = json.load(f)

        self.masses[0].set_target_area(self.area_option_a1)
        self.masses[1].set_target_area(self.area_option_a2)
        self.masses[2].set_target_area(self.area_option_b)

    def finalize(self, mass_index, center_radius):
        # type: (int, int)-> None
        """Mass 센터에 원형 외부공간을 만들고, Area를 Set시킨다."""
        # mass 선택
        # mass 0 은 a1
        # mass 1 은 a2
        # mass 2 은 b
        mass = self.masses[mass_index]
        # cluster선택은 첫번째 것만 사용한다.(시간상...)
        area_distribute_option = mass.area_distribute_options[0]

        target_area_distribution = deepcopy(area_distribute_option)

        # 중심을 비운다.
        mass.create_center(center_radius)

        area_to_mass = AreaToMass(mass, target_area_distribution)
        res, skipped_cluster = area_to_mass.process()
        outputs = []

        # horizontal expand
        # 수평으로 확장시도
        for area_groups in res:
            new_area_groups = []
            seed_area_groups = [
                area_group for area_group in area_groups if area_group.is_area_set
            ]

            for area_group in seed_area_groups:
                expanded_area_group = area_group.horizontal_expand()
                new_area_groups.append(expanded_area_group)

            outputs.append(MassResult(new_area_groups, skipped_cluster))
        return outputs
