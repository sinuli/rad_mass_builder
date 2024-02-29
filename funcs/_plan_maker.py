# -*- coding:utf-8 -*-
# pylint: disable=bare-except
try:
    from typing import List, Tuple, Dict, Any, Optional
except ImportError:
    pass

import math
import scriptcontext as sc
from copy import deepcopy
from funcs._radial_mass import RadialAreaGroup, RadialArea
from funcs.base import MassResult
import Rhino.Geometry as geo  # type: ignore

from _utils import get_joined_curve, move_curve


class Room:
    """
    Room 은 RadialAreaGroup의 조합으로 geometry가 정의되고,
    target면적과, program을 갖는다.
    """

    def __init__(self, radial_areas, name, target_area):
        # type: (List[RadialArea], str, float) -> None
        self.radial_areas = radial_areas
        self.name = name
        self.target_area = target_area

    @property
    def point(self):

        g_max = max(self.radial_areas, key=lambda k: k.area)
        c = g_max.c
        r = (g_max.r2 + g_max.r1) / 2
        angle = (g_max.a2 + g_max.a1) / 2
        v = geo.Vector3d(math.cos(angle), math.sin(angle), 0)
        return c + r * v

    def get_radial_area_geom(self, radial_area):
        # type: (RadialArea) ->geo.Curve
        a1 = radial_area.a1
        a2 = radial_area.a2
        r1 = radial_area.r1
        r2 = radial_area.r2
        c = radial_area.c
        v1 = geo.Vector3d(math.cos(a1), math.sin(a1), 0)
        v2 = geo.Vector3d(math.cos(a2), math.sin(a2), 0)

        crv1 = geo.Polyline([c + r1 * v1, c + r2 * v1]).ToNurbsCurve()
        crv2 = geo.Polyline([c + r1 * v2, c + r2 * v2]).ToNurbsCurve()
        crv3 = geo.ArcCurve(geo.Arc(geo.Circle(c, r2), geo.Interval(a1, a2)))

        if r1 != 0:
            crv4 = geo.ArcCurve(geo.Arc(geo.Circle(c, r1), geo.Interval(a1, a2)))
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
    def geom(self):
        res = []
        for radial_area in self.radial_areas:
            res.append(self.get_radial_area_geom(radial_area))
        return res

    @property
    def area(self):
        area = 0
        for radial_area in self.radial_areas:
            area += radial_area.area

        return area


class RoomMaker:
    def __init__(self, area_group):
        # type: (RadialAreaGroup) -> None
        self.area_group = area_group
        self.area_data = area_group.area_data
        self.radial_area = deepcopy(area_group.radial_area)
        self.plan_type = None

    def process(self):
        # match area
        self._match_area()
        # set strategy
        self.get_plan_type()
        # create room for each
        rooms = self.create_rooms_by_plan_type()  # type: List[Room]
        return rooms

    def get_plan_type(self):
        areas = [a[0] for a in self.area_data]
        if any([area > 100 for area in areas]):
            self.plan_type = "room_in_room"
        else:
            self.plan_type = "simple"

    def _match_area(self):
        total_area = sum([a[0] for a in self.area_data])

        angle = self.radial_area.a2 - self.radial_area.a1
        total_area / angle
        new_r2 = math.sqrt(
            (total_area + angle * (self.radial_area.r1**2) / 2) * 2 / angle
        )
        new_r2 = round(new_r2)
        self.radial_area.r2 = new_r2

    def create_radial_mass(self, radial_areas):
        # type: (List[RadialArea]) -> None
        origin = radial_areas[0].c
        a1 = radial_areas[0].a1
        a2 = radial_areas[-1].a2
        r1 = max([radial_area.r1 for radial_area in radial_areas])
        r2 = min([radial_area.r2 for radial_area in radial_areas])
        if a2 < a1:
            a1 = a1 - 2 * math.pi
        self.radial_area = RadialArea(origin, a1, a2, r1, r2)

    def divide_by_radius(self, radius, _radial_area):
        # type: (float, RadialArea) -> Tuple[RadialArea]
        # radius로 나눠서 리턴한다.
        # inner_geom, outer_geom 순서
        radial_area1 = _radial_area.duplicate()
        radial_area2 = _radial_area.duplicate()
        radial_area1.r2 = radius
        radial_area2.r1 = radius
        return radial_area1, radial_area2

    def divide_by_angle(self, angle, _radial_area):
        # type: (float, RadialArea) -> Tuple[RadialArea]
        # angle로 나눠서 리턴한다.
        # 시계 반대방향 순으로
        radial_area1 = _radial_area.duplicate()
        radial_area2 = _radial_area.duplicate()
        radial_area1.a2 = radial_area1.a1 + angle
        radial_area2.a1 = radial_area2.a1 + angle

        return radial_area1, radial_area2

    def divide_by_areas(self, areas, _radial_area):
        # type: (float, RadialArea) -> List[RadialArea]
        res = []
        rest = _radial_area
        for area in areas:
            if area == areas[-1]:
                # 마지막 area는 남은 면적을 넣어준다.
                res.append(rest)
                break
            angle = 2 * area / (self.radial_area.r2**2 - self.radial_area.r1**2)
            # make it multiple of 1/18pi
            angle = math.pi / 36 * (angle // (math.pi / 36))
            cut_radial_area, rest = self.divide_by_angle(angle, rest)
            res.append(cut_radial_area)
        return res

    def create_simple_rooms(self):
        # 면적에 따라서 Radial 방향으로 divide한다.
        # 나머지 영역

        # 면적으로 sort
        room_names = [a[1] for a in self.area_data]
        areas = [a[0] for a in self.area_data]

        sorted_room_tuple = sorted(zip(areas, room_names))
        sorted_room_tuple.reverse()

        areas = [item[0] for item in sorted_room_tuple]
        names = [item[1] for item in sorted_room_tuple]

        radial_area = self.radial_area.duplicate()
        # 남은 면적들을 area로 나눠서 내보낸다.
        radial_area_divided = self.divide_by_areas(areas, radial_area)
        res_rooms = []

        for room_name, radial_area, target_area in zip(
            names, radial_area_divided, areas
        ):
            res_rooms.append(Room([radial_area], room_name, target_area))

        return res_rooms

    def create_room_in_room_rooms(self):
        # radial area group을 수평 분할 하고
        # 큰 면적 할당, 진입로 확정 후
        # 나머지 영역을 나눈다.

        # 면적으로 sort

        room_names = [a[1] for a in self.area_data]
        areas = [a[0] for a in self.area_data]

        sorted_room_tuple = sorted(zip(areas, room_names))
        sorted_room_tuple.reverse()

        # room in room type에선 무조건 하나의 큰 Room이 있다.
        big_area, big_room_name = sorted_room_tuple.pop(0)

        # TODO min corridor angle은 반지름을 보고 자동으로 조절하도록 변경하면 좋겠다.
        min_width = 2
        min_corridor_angle = ((min_width / self.radial_area.r1) // (math.pi / 18)) * (
            math.pi / 18
        )
        min_corridor_angle = math.pi / 9
        angle = self.radial_area.a2 - self.radial_area.a1
        r2 = self.radial_area.r2
        r1 = self.radial_area.r1

        # 커팅할 radius를 구하고 정수화한다.
        cutting_r = math.sqrt(
            (2 * big_area - angle * (r2**2) + (min_corridor_angle) * (r1**2))
            / (min_corridor_angle - angle)
        )
        cutting_r = math.floor(cutting_r)

        # 회전방향 분할
        inner_area, outer_area = self.divide_by_radius(cutting_r, self.radial_area)

        # 방사형 분할
        entrance_area, other_area = self.divide_by_angle(min_corridor_angle, inner_area)

        # 진입로,외측 면적 더해서 방을 만든다.
        big_room = Room([entrance_area, outer_area], big_room_name, big_area)
        res_rooms = [big_room]

        # 나머지 영역
        # 나눌 때는 작은면적부터 형성하기 위해서 순서를 바꿈
        sorted_room_tuple.reverse()
        rest_areas = [item[0] for item in sorted_room_tuple]
        rest_names = [item[1] for item in sorted_room_tuple]
        # 남은 면적들을 area로 나눠서 내보낸다.
        area_group_divided = self.divide_by_areas(rest_areas, other_area)

        for room_name, area_group, target_area in zip(
            rest_names, area_group_divided, rest_areas
        ):
            res_rooms.append(Room([area_group], room_name, target_area))

        return res_rooms

    def create_rooms_by_plan_type(self):
        if self.plan_type == "simple":
            return self.create_simple_rooms()

        if self.plan_type == "room_in_room":
            return self.create_room_in_room_rooms()

        if self.plan_type == "corridor":
            raise NotImplementedError

    def create_rooms(self):

        return self.create_rooms_by_plan_type(self.plan_type)


class PlanMaker:

    def __init__(self, mass_result):
        self.mass_result = mass_result  # type: MassResult
        self.room_makers = []  # type: List[RoomMaker]
        self.parse()
        self.rooms = []  # type: List[Room]

    def parse(self):
        area_groups = self.mass_result.area_groups
        for area_group in area_groups:
            self.room_makers.append(RoomMaker(area_group))

    def process(self):
        outputs = []  # type: List[Room]
        for room_maker in self.room_makers:
            outputs.extend(room_maker.process())
        self.rooms = outputs

    def filter(self, min_width=1.5):
        check_room_name = [
            "office",
            "meeting_room",
            "community_corridor",
            "exhibit_experience",
            "experience2",
            "discuss_room",
            "program1",
            "program2",
            "exhibit_planning_room",
            "unman_cafe",
            "kitchen",
        ]
        for room in self.rooms:
            if room.name not in check_room_name:
                continue
            check_radial_area = max(room.radial_areas, key=lambda k: k.area)
            min_inner_width = check_radial_area.r1 * (
                check_radial_area.a2 - check_radial_area.a1
            )

            if min_inner_width < min_width:
                return False
        return True

    def get_2d(self):
        res = []
        texts = []
        points = []
        for room in self.rooms:
            res.append(room.geom)
            texts.append(room.name)
            points.append(room.point)
        return res, texts, points

    def get_3d(self, start_height, height):
        room_crvs_group, _, _ = self.get_2d()
        crvs = []
        for room_crvs in room_crvs_group:
            crvs.extend(room_crvs)

        crvs = [move_curve(crv, geo.Vector3d.ZAxis * start_height) for crv in crvs]

        def extrude_crv(_crv, _height):
            _, plane = _crv.TryGetPlane()
            ANGLE_TOL = math.pi / 180
            if not geo.Vector3d.ZAxis.EpsilonEquals(plane.Normal, ANGLE_TOL):
                _height = -_height
            extrusion = geo.Extrusion.Create(_crv, _height, True)
            if extrusion is None:
                sc.sticky["error"] = _crv
                return None
            else:
                return extrusion.ToBrep()

        return [extrude_crv(crv, height) for crv in crvs]
