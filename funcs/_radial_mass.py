# -*- coding:utf-8 -*-
# pylint: disable=bare-except
try:
    from typing import List, Tuple, Dict, Any, Optional
except ImportError:
    pass

import math
import Rhino.Geometry as geo  # type: ignore

# from funcs._site import Site
from funcs._utils import get_joined_curve, check_intersection

MIN_RADIUS = 7
FIRST_MATCHING_AREA_RATIO = 1.6
MASS_DIVISION_COUNT = 12


class RadialArea:
    """
    RadialArea는 Mass를 만들기 위한 가장 첫번째 geometry이다.
    c 중심
    a1 시작 각도
    a2 종료 각도
    r1 시작 반지름
    r2 종료 반지름
    위 다섯개의 parameter로 정의되어 있고
    r1 == 0 인 경우에는 피자
    r1 != 0 인 경우에는 한입 먹은 피자처럼 생겼다.
    """

    def __init__(self, c, a1, a2, r1, r2):
        # type: (geo.Point3d, float, float, float, float) -> None
        self.c = c
        self.a1 = a1
        self.a2 = a2
        self.r1 = r1
        self.r2 = r2
        self.v1 = geo.Vector3d(math.cos(a1), math.sin(a1), 0)
        self.v2 = geo.Vector3d(math.cos(a2), math.sin(a2), 0)

    def duplicate(self):
        return RadialArea(self.c, self.a1, self.a2, self.r1, self.r2)

    @property
    def geom(self):

        crv1 = geo.Polyline(
            [self.c + self.r1 * self.v1, self.c + self.r2 * self.v1]
        ).ToNurbsCurve()

        crv2 = geo.Polyline(
            [self.c + self.r1 * self.v2, self.c + self.r2 * self.v2]
        ).ToNurbsCurve()
        crv3 = geo.ArcCurve(
            geo.Arc(geo.Circle(self.c, self.r2), geo.Interval(self.a1, self.a2))
        )

        if self.r1 != 0:  # 중간에 비어 있으면
            crv4 = geo.ArcCurve(
                geo.Arc(geo.Circle(self.c, self.r1), geo.Interval(self.a1, self.a2))
            )
            try:
                curve_joined = get_joined_curve([crv1, crv2, crv3, crv4])
                return curve_joined
            except:
                print("ERROR")
                return None
        else:
            try:
                curve_joined = get_joined_curve([crv1, crv2, crv3])
                return curve_joined
            except:
                print("ERROR")
                return None

    @property
    def area(self):
        return (self.a2 - self.a1) * ((self.r2**2) - (self.r1**2))


def try_add_area_group(area_group_1, area_group_2):
    # type: (RadialAreaGroup, RadialAreaGroup) -> RadialAreaGroup
    """RadialAreaGroup의 __add__의 경우는 더하면서
    앞 뒤 RadialAreaGroup의 관계를 만들어버린다.
    더해 보고, 겹쳐지면 폐기해야 되는 경우에 이걸 사용한다."""
    rad_1 = area_group_1.radial_area.duplicate()
    rad_2 = area_group_2.radial_area.duplicate()
    new_radial_area_group = RadialAreaGroup([rad_1, rad_2])
    new_radial_area_group.prev = area_group_1.prev
    new_radial_area_group.next = area_group_2.next
    return new_radial_area_group


class RadialAreaGroup:
    """
    RadialAreaGroup은 RadialArea의 조합이다.
    RadialAreaGroup은 RadialArea의 크기 조절에 대해서 유연한
    인터페이스로서 작동한다.
    AreaCluster를 대응시키거나, 그 일부를 대응시켜 면적을 set 시킨다.

    prev, next로 자신 앞 뒤의 RadialAreaGroup과 관계를 갖는다는 점을 명심하자
    """

    def __init__(self, radial_areas):
        # type: (List[RadialArea]) -> None

        self.radial_areas = radial_areas  # TODO 지울 것
        self.radial_area = None  # type: RadialArea

        self.prev = None  # type: Optional[RadialAreaGroup]
        self.next = None  # type: Optional[RadialAreaGroup]

        self.area_data = None
        self.divide_options = []

        self.is_expandable = True
        self.create_radial_mass(radial_areas)

    def __add__(self, other):
        # type: (RadialAreaGroup) -> RadialAreaGroup
        """add는 항상 앞쪽의 area_group이 먼저 나와야 한다."""
        rad_1 = self.radial_area.duplicate()
        rad_2 = other.radial_area.duplicate()
        new_radial_area_group = RadialAreaGroup([rad_1, rad_2])
        new_radial_area_group.prev = self.prev
        new_radial_area_group.next = other.next

        new_radial_area_group.next.prev = new_radial_area_group
        new_radial_area_group.prev.next = new_radial_area_group

        return new_radial_area_group

    def duplicate(self):
        return RadialAreaGroup(
            [radial_area.duplicate() for radial_area in self.radial_areas]
        )

    def create_radial_mass(self, radial_areas):
        # type: (List[RadialArea]) -> None
        """initialize하는 과정 속에서
        RadialArea를 하나로 합치는 과정이다.
        r1은 RadialArea들 중 큰 것
        r2는 RadialArea들 중 작은 것이다.
        """
        origin = radial_areas[0].c
        a1 = radial_areas[0].a1
        a2 = radial_areas[-1].a2
        r1 = max([radial_area.r1 for radial_area in radial_areas])
        r2 = min([radial_area.r2 for radial_area in radial_areas])
        if a2 < a1:
            a1 = a1 - 2 * math.pi
        self.radial_area = RadialArea(origin, a1, a2, r1, r2)

    def set_area_data(self, area_data):
        self.area_data = area_data

    @property
    def target_area(self):
        if self.area_data is None:
            raise Exception("area_data not set")
        return sum([data[0] for data in self.area_data])

    def horizontal_expand(self):
        # 양쪽 중 확장 가능한 곳 찾아봄.
        # 양쪽 모두 확인해보고, 확장 가능한 쪽으로 확장함.
        # 이 함수를 여러번 콜하면 주변의 area group으로 확장한다.

        def _try_expand(expanded_area_group, is_next):
            # type: (RadialAreaGroup, bool) -> RadialAreaGroup
            """확장을 시도해본다.
            is_next는 next로 확장해볼지 prev로 확장해볼지에 대한 flag
            앞뒤의 관계는 바뀌지 않고, RadialAreaGroup 새로운 객체가 나온다.
            면적 검토 후 모자라면 다음으로 넘어간다.
            """
            if is_next and not expanded_area_group.next.is_area_set:
                expanded_area_group = try_add_area_group(
                    expanded_area_group, expanded_area_group.next
                )  # type: RadialAreaGroup
            if not is_next and not expanded_area_group.prev.is_area_set:
                expanded_area_group = try_add_area_group(
                    expanded_area_group.prev, expanded_area_group
                )  # type: RadialAreaGroup
            return expanded_area_group

        def _fix_expand(area_group):
            # type: (RadialAreaGroup) -> None
            """만들어본 area group의 앞뒤 관계를 설정하는 단계이다."""
            area_group.prev.next = area_group
            area_group.next.prev = area_group

        _area_group = self

        # 현재 상태가 괜찮으면 그대로 리턴한다.
        if _area_group.shape_ok and _area_group.area > self.target_area:
            return _area_group

        is_next = True
        # while문이 맞는데, 이따금 무한 루프로 돌기 때문에
        # for 문을 걸어두었다. range안의 숫자는 전체 쪼갠 숫자 -2 정도여야 한다.
        for _ in range(10):
            if _area_group.next.is_area_set and _area_group.prev.is_area_set:
                break

            # 번갈아 가면서 좌우 탐색
            _area_group = _try_expand(_area_group, is_next)
            is_next = not is_next

            if _area_group.shape_ok and _area_group.area > self.target_area:
                _fix_expand(_area_group)
                _area_group.set_area_data(self.area_data)
                return _area_group
        return self

    @property
    def shape_ok(self):
        # 형태가 괜찮은지 확인한다.
        r1 = self.radial_area.r1
        r2 = self.radial_area.r2
        a1 = self.radial_area.a1
        a2 = self.radial_area.a2
        LENGTH_DEPTH_RATIO = 0.8
        return r1 * (a2 - a1) / (r2 - r1) > LENGTH_DEPTH_RATIO

    @property
    def is_area_set(self):
        if self.area_data:
            return True
        else:
            return False

    @property
    def area(self):
        return self.radial_area.area

    @property
    def geom(self):
        return self.radial_area.geom


class RadialMass:
    def __init__(self, area, name, site):
        # type: (float, str, Site) -> None
        """주변 대지 상태만을 체크한 Raw 한 상태의 Mass"""
        self.name = name
        self.site = site
        self.center = None
        self.target_area = area

        self.radial_vectors = []
        self.radial_angles = []
        self.radial_areas = []
        self.condition = {}
        self.angle_division = MASS_DIVISION_COUNT

        # site setting
        self.lot_boundary = site.boundary
        self.park_geom = site.park_geom
        self.forest_entrance_geom = site.forest_entrance_geom
        self.slope_geom = site.slope_geom

        # result
        self.radial_area_groups = []  # type: List[RadialAreaGroup]
        self.area_distribute_options = {}

    def generate(self):
        """Main Process"""
        self.radial_vectors = self._get_radial_vectors()
        self.radial_areas = self._get_radial_areas()  # type: List[RadialArea]
        self._cut_radius()
        self._create_radial_area_group()
        self._match_area()

    def duplicate_area_groups(self):
        return [area_group.duplicate() for area_group in self.radial_area_groups]

    def create_center(self, radius):
        # type: (int)-> None
        """중심에 비어있는 원형공간을 만든다."""
        for radial_area_group in self.radial_area_groups:
            radial_area_group.radial_area.r1 = radius
        center_radial_area = RadialArea(self.center, 0, math.pi * 2, 0, radius)
        self.center_area_group = RadialAreaGroup([center_radial_area])

    def _create_radial_area_group(self):
        self.radial_area_groups = [
            RadialAreaGroup([radial_area]) for radial_area in self.radial_areas
        ]
        # connect
        for i in range(len(self.radial_area_groups)):
            cur = self.radial_area_groups[i]
            next = self.radial_area_groups[(i + 1) % len(self.radial_area_groups)]
            prev = self.radial_area_groups[i - 1]
            cur.next = next
            cur.prev = prev

    def set_center(self, center):
        self.center = center

    def set_condition(self, condition):
        self.condition = condition

    def _match_area(self):
        """면적을 Mass Area에 맞춰서 줄이는 함수"""
        index = 0
        counter = 0
        shrinking_groups = [
            area_group
            for area_group in self.radial_area_groups
            if area_group.radial_area.r2 > self.min_radius + 4
        ]

        while self.area > self.target_area * FIRST_MATCHING_AREA_RATIO:
            shrinking_group = shrinking_groups[
                index % len(shrinking_groups)
            ]  # type: RadialAreaGroup
            if (
                shrinking_group.radial_area.r2 <= MIN_RADIUS
            ):  # 7m 보다 작은 area는 축소시키지 않는다.
                if counter == len(shrinking_groups):
                    # 더 이상 줄일 수 있는 Radial Area Group 이 없을 때
                    break
                index += 1
                counter += 1
                continue
            else:
                shrinking_group.radial_area.r2 = shrinking_group.radial_area.r2 - 0.5
                counter = 0
                index += 1

    def _cut_radius(self):  # cut too long radius
        """
        최고로 긴 area의 out
        반지름이 3미터 이상 차이가 나면 2등 반지름과 맞춰준다.
        """
        out_rad_list = [radial_area.r2 for radial_area in self.radial_areas]
        sorted_radial_area = sorted(
            self.radial_areas, key=lambda radial_area: radial_area.r2
        )

        if sorted_radial_area[-1].r2 - sorted_radial_area[-2].r2 > 3:
            sorted_radial_area[-1].r2 = sorted_radial_area[-2].r2

    def _get_radial_vectors(self):
        # Center로부터 360 /12 각도마다 radial vector를 구한다.
        angle_step = math.pi * 2 / self.angle_division
        vectors = []
        for i in range(self.angle_division + 1):
            angle = angle_step * i
            self.radial_angles.append(angle)
            x = math.cos(angle)
            y = math.sin(angle)
            vectors.append(geo.Vector3d(x, y, 0))
        return vectors

    def _get_radial_areas(self):
        # vector를 두개씩 체크한다. 기준에 맞는 지점에서 뻗을 수 있는 최대한의 피자조각을 찾는다.
        # vec_1, vec_2, max_radius 이렇게 세가지로 정의된다.
        # 현재는 lot_boundary
        # park_geom
        # slope_geom
        # forest_entrance_geom체크한다.
        radial_areas = []
        for i in range(len(self.radial_angles) - 1):
            angle1 = self.radial_angles[i]
            angle2 = self.radial_angles[i + 1]
            radius = 3  # minimum radius == 3
            for _ in range(30):
                radial_area = RadialArea(self.center, angle1, angle2, 0, radius)
                radial_area_geom = radial_area.geom

                if radial_area_geom is None:  # ERROR
                    radius -= 1
                    radial_area = RadialArea(self.center, angle1, angle2, 0, radius)
                    radial_areas.append(radial_area)
                    break

                elif (
                    check_intersection(radial_area_geom, self.lot_boundary)
                    or check_intersection(radial_area_geom, self.park_geom)
                    or check_intersection(radial_area_geom, self.slope_geom)
                    or check_intersection(radial_area_geom, self.forest_entrance_geom)
                ):
                    radius -= 1
                    radial_area = RadialArea(self.center, angle1, angle2, 0, radius)
                    radial_areas.append(radial_area)
                    break
                else:
                    radius += 1
        return radial_areas

    def set_target_area(self, area_distribute_options):
        self.area_distribute_options = area_distribute_options

    @property
    def area(self):
        if len(self.radial_area_groups) == 0:
            return sum([radial_area.area for radial_area in self.radial_areas])
        else:
            return sum(
                [
                    radial_area_group.area
                    for radial_area_group in self.radial_area_groups
                ]
            )

    @property
    def geom(self):
        if len(self.radial_area_groups) == 0:
            return [radial_area.geom for radial_area in self.radial_areas]
        else:
            return [
                radial_area_group.radial_area.geom
                for radial_area_group in self.radial_area_groups
            ]

    @property
    def max_radius(self):
        return max(area_group.radial_area.r2 for area_group in self.radial_area_groups)

    @property
    def min_radius(self):
        return min(area_group.radial_area.r2 for area_group in self.radial_area_groups)
