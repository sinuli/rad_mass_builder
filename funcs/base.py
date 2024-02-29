# -*- coding:utf-8 -*-
# pylint: disable=bare-except
try:
    from typing import List, Tuple, Dict, Any, Optional
except ImportError:
    pass
import Rhino.Geometry as geo
from funcs._radial_mass import RadialAreaGroup


class MassResults:
    def __init__(self, radius, point, mass_name, outputs):
        # type: (int, geo.Point3d, str, List[MassResult]) -> None
        """MassResult의 리스트이다. 어디서 만들어졌고, 어떤 radius인지 기억하기 위해서
        다른 property들도 함께 갖고 있다."""
        self.radius = radius
        self.point = point
        self.mass_name = mass_name
        self.outputs = outputs


class MassResult:
    def __init__(self, area_groups, skipped_cluster):
        # type: (List[RadialAreaGroup], List) -> None
        """AreaToMass의 결과물 Area가 set 된 RadialAreaGroup의 List이다.
        크기가 너무 작아서 skip된 area_cluster를 함께 리턴한다."""
        self.area_groups = area_groups
        self.skipped_cluster = skipped_cluster
