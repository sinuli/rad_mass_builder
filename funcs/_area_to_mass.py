# -*- coding:utf-8 -*-
# pylint: disable=bare-except
try:
    from typing import List, Tuple, Dict, Any, Optional
except ImportError:
    pass

from copy import deepcopy
from itertools import product
import scriptcontext as sc

from funcs._radial_mass import RadialAreaGroup, RadialMass
from funcs._utils import get_ag_interaval, check_area_group_intersection, check_interval_intersection
import math

FIRST_POS_TOL = 0.6
TOO_SMALL_AREA = 20

class SeedExtensionScenarioCombination:
    def __init__(self):
        self.scenario_combination = []

    def add_scenario(self, scenario):
        self.scenario_combination.append(scenario)

    def check_scenario_intersection(self, scenario1, scenario2):
        for ag1 in scenario1.all_area_groups:
            for ag2 in scenario2.all_area_groups:
                intervals_1 = get_ag_interaval(ag1)
                intervals_2 = get_ag_interaval(ag2)
                if check_interval_intersection(intervals_1, intervals_2):
                    return True
        return False
    
    @property
    def is_valid(self):
        for scenario1 in self.scenario_combination:
            for scenario2 in self.scenario_combination:
                if scenario1 == scenario2:
                    pass
                else:
                    if self.check_scenario_intersection(scenario1, scenario2):
                        return False
        return True
                
class SeedExtensionScenario:
    def __init__(self, seed, prev_area_groups, next_area_groups, prev_area_data , next_area_data):
        self.seed = seed
        self.prev_area_groups = prev_area_groups
        self.next_area_groups = next_area_groups
        self.prev_area_data = prev_area_data
        self.next_area_data = next_area_data
        self._geom_list = None
        
    @property
    def all_area_groups(self):
        all_groups = [self.seed.area_groups[0]]
        all_groups.extend(self.prev_area_groups)
        all_groups.extend(self.next_area_groups)
        return all_groups
    
    @property
    def geom_list(self):
        if self._geom_list is None:
            _geom_list = [self.seed.area_groups[0].geom]
            _geom_list.extend([ag.geom for ag in self.prev_area_groups])
            _geom_list.extend([ag.geom for ag in self.next_area_groups])
            self._geom_list = _geom_list
        return self._geom_list
    
class Seed:
    def __init__(self, area_group, area_cluster):
        # type: (RadialAreaGroup, Tuple) -> None
        
        self.area_groups = [area_group]
        self.area_cluster = area_cluster
        self.next_area_groups = []
        self.prev_area_groups = []
        self.extend_scenarios = []

    @property
    def area_left(self):

        return sum( self.area_left_data.values())
        
    @property
    def area_left_data(self):
        '''처리되지 않은 area들'''
        area_processed_keys = []
        for area_group in self.area_groups:
            if area_group.is_area_set:
                keys = [i[1] for i in area_group.area_data]
                area_processed_keys.extend(keys)

        not_processed_area_data = {}
        for k, v in self.area_cluster.items():
            if k not in area_processed_keys:
                not_processed_area_data[k] = v
        return not_processed_area_data
    
    def get_extendable_groups(self):

        seed_area_group = self.area_groups[0]
        next_area_group = seed_area_group.next
        prev_area_group = seed_area_group.prev
        count = 0

        while not next_area_group.is_area_set and not seed_area_group == next_area_group:
            self.next_area_groups.append(next_area_group)
            next_area_group = next_area_group.next
            count +=1
            if count ==100:
                break
        count = 0

        while not prev_area_group.is_area_set and not seed_area_group == prev_area_group:
            self.prev_area_groups.append(prev_area_group)
            prev_area_group = prev_area_group.prev
            count +=1
            if count ==100:
                break

    def check_extendable(self):
        
        extendable_area  = sum([area_group.area for area_group in self.prev_area_groups])\
        +sum([area_group.area for area_group in self.next_area_groups])

        return  extendable_area >= self.area_left
    
    def find_extend_scenarios(self):
        
        def get_possible_division():
            target_list = []
            for k,v in zip(self.area_left_data.keys(), self.area_left_data.values()):
                target_list.append((v,k))

            l1 = []
            l2 = []

            for pattern in product([True,False],repeat=len(target_list)):
                l1.append([x[1] for x in zip(pattern,target_list) if x[0]])
                l2.append([x[1] for x in zip(pattern,target_list) if not x[0]])

            return zip(l1,l2)
        
        possible_division = get_possible_division()

        prev_area_left = sum([area_group.area for area_group in self.prev_area_groups])
        next_area_left = sum([area_group.area for area_group in self.next_area_groups])
        
        extendable_division = []
        for division in possible_division:
            area_data_1, area_data_2 = division
            if sum([x[0] for x in area_data_1]) < prev_area_left and sum([x[0] for x in area_data_2])< next_area_left:
                extendable_division.append(division)

        extend_scenarios = []

        for division in extendable_division:
            prev_area_data , next_area_data = division
            prev_area_total = sum([x[0]for x in prev_area_data])
            next_area_total = sum([x[0]for x in next_area_data])
            prev_area_groups = self._get_area_groups_matching_area(prev_area_total, self.prev_area_groups)
            next_area_groups = self._get_area_groups_matching_area(next_area_total, self.next_area_groups)
            extend_scenarios.append(SeedExtensionScenario(self, prev_area_groups, next_area_groups, prev_area_data , next_area_data))
        self.extend_scenarios = extend_scenarios
        
        return extend_scenarios

    def _get_area_groups_matching_area(self, area, area_groups):
        res_area_groups = [] # type: List[RadialAreaGroup]
        i = 0 
        while sum([area_group.area for area_group in res_area_groups])<area:
            res_area_groups.append(area_groups[i])
            i+=1
            if i ==100:
                return []
        return res_area_groups
    
    def expand_by(self, extension_scenario):
        # type: (SeedExtensionScenario) -> List[RadialAreaGroup]
        
        area_groups_res = [area_group.duplicate() for area_group in self.area_groups]
        if not len(extension_scenario.next_area_groups) == 0 :
            if len(extension_scenario.next_area_data) <= 3:
                area_group = extension_scenario.next_area_groups[0] # type: RadialAreaGroup
                for i in range(len(extension_scenario.next_area_groups)-1):
                    area_group += extension_scenario.next_area_groups[i+1]
                area_group.set_area_data(extension_scenario.next_area_data)
                area_groups_res.append(area_group)
            else:
                print("I HAVE NO IDEA")
        if not len(extension_scenario.prev_area_groups) == 0 :
            if len(extension_scenario.prev_area_data) <= 3:
                area_group = extension_scenario.prev_area_groups[0]
                for i in range(len(extension_scenario.prev_area_groups)-1):
                    area_group += extension_scenario.prev_area_groups[i+1]
                area_group.set_area_data(extension_scenario.prev_area_data)
                area_groups_res.append(area_group)
            else:
                print("I HAVE NO IDEA")
      
        return area_groups_res
    
class PositionScenario:
    def __init__(self):
        self.area_cluster_list = []
        self.init_area_group_list = [] # type: List[RadialAreaGroup]
        self.area_group_list = [] # type: List[RadialAreaGroup]
        self.first_area_data_list = []
        self.seeds = []  #type: List[Seed]

    def add(self, area_cluster, area_group, first_area_data):
        self.area_cluster_list.append(area_cluster)
        self.init_area_group_list.append(area_group)
        self.first_area_data_list.append(first_area_data)

    def is_valid(self):
        for area_group_1 in self.init_area_group_list:
            for area_group_2 in self.init_area_group_list:
                if area_group_1 == area_group_2:
                    pass
                else:
                    if check_area_group_intersection(area_group_1, area_group_2):
                        return False
        
        return True
    
    def create_seeds(self):
        self.init_area_group_list =[area_group.duplicate() for area_group in self.init_area_group_list]
        for area_group, first_area_data, area_cluster in zip(self.init_area_group_list, self.first_area_data_list, self.area_cluster_list):
            area_group.set_area_data(first_area_data)
            seed = Seed(area_group, area_cluster)
            self.seeds.append(seed)

    def filter_invalid_radius(self):
        for area_group in self.area_group_list:
            if (area_group.radial_area.r2 - area_group.radial_area.r1) < 3:
                area_group.set_area_data(("invalid", 0))

    

    def process(self):
        # 3m 미만의 area_group은 막아둠.
        self.filter_invalid_radius()

        # 각 seed 들이 성장할 수 있는지 확인
        for seed in self.seeds:
            seed.get_extendable_groups()
        
        # 모든 seed가 성장가능 하다면 각각의 성장 scenario를 생성
        if all([seed.check_extendable() for seed in self.seeds]):
            for seed in self.seeds:
                seed.find_extend_scenarios()
        else:
            print("EXTEND NOT POSSIBLE")
            return []
        
        # 모든 성장 scenario의 combination을 만들고 validation 함
        res_scenarios = [] # type: List[SeedExtensionScenarioCombination]
        
        for seed in self.seeds:
            if len(res_scenarios) == 0:
                for scenario in seed.extend_scenarios:
                    comb = SeedExtensionScenarioCombination()
                    comb.add_scenario(scenario)
                    res_scenarios.append(comb)
            else:
                next_scnearios = []
                for res_scenario in res_scenarios:
                    for scenario in seed.extend_scenarios:
                        scenario_new = deepcopy(res_scenario)
                        scenario_new.add_scenario(scenario)
                        if scenario_new.is_valid:
                            next_scnearios.append(scenario_new)
                        else:
                            print("INVALID SCENARIO COMBINATION")

                res_scenarios = next_scnearios
        print("extension scenario count : {}".format(len(res_scenarios)))
        res_scenarios_filtered = [] 
        for scenario in res_scenarios:
            if len(scenario.scenario_combination) == len(self.seeds):
                res_scenarios_filtered.append(scenario)

        print("extension scenario filtered count : {}".format(len(res_scenarios_filtered)))
        output = []
        
        for scenario in res_scenarios_filtered:
            seeds = deepcopy(self.seeds)
            res_area_groups = []
            for seed, extension_scenario in zip(seeds, scenario.scenario_combination):
                res_area_groups.extend(seed.expand_by(extension_scenario))
            # output.append(Result(res_area_groups, self.area_group_list))
            output.append(res_area_groups)
        return output


class AreaToMass:
    """ 
    여기서 Main Class 는 AreaToMass Class이다.

    RadialMass에서 찾은 Mass에 Area를 앉히는 것을 목적으로 한다.
    AreaToMass Class에서는 AreaCluster를 앉힐 수 있는 첫번째 포지션 조합을 찾고
    Seed 객체를 만든다.

    그리고 각 Seed가 확장될 수 있는 Scenario를 찾아서 Expand시키고 프로세스를 종료한다.

    주의할점 : TOO SMALL AREA 보다 작은 areacluster는 찾지 않는다.

    """
    def __init__(self, mass, area_distribute_option):
        # type: (RadialMass, List)->None
        self.mass = mass
        self.area_distribute_option = area_distribute_option
        self.scenarios = []
        self.skipped_area_cluster = []

    def area_is_similar(self, area_target, area):
        """
        5/20 테스트 출력 결과 면적이 작으면 
        추후에 RoomMaker 단계에서 대지 선을 벗어나는 문제가 생긴다.
        여기서 면적이 더 작은 것은 보지 않도록 수정함
        """
        if area_target > 200:
            return (area<=area_target and area*(1+FIRST_POS_TOL)>=area_target)
        else:
            return (area*(1-FIRST_POS_TOL/2)<=area_target and area*(1+FIRST_POS_TOL)>=area_target)

    def check_too_small(self, room_tuples):
        area_total = sum([x[0] for x in room_tuples])
        if area_total < TOO_SMALL_AREA:
            return True
        else:
            return False
        
    def get_combined_area_groups(self,_radial_area_groups, count):
        # type: (List[RadialAreaGroup], int) -> List[RadialAreaGroup]
        """
        area_group을 근접성 기준으로 통합한다.
        """
        radial_groups_binded = []
        
        for radial_area_group in _radial_area_groups:
            area_group_combined = radial_area_group
            for _ in range(count):
                print( area_group_combined , area_group_combined.next)
                area_group_combined = area_group_combined + area_group_combined.next
            radial_groups_binded.append(area_group_combined)
        return radial_groups_binded
    
    def find_matching_area_groups(self, _radial_area_groups, room_tuples, combine_level):
        # type: (List[RadialAreaGroup], Tuple, int) -> List[RadialAreaGroup]
        """Room Tuple과 매치되는 Area Group을 찾는다."""
        matching_area_groups = [] 
        area_total = sum([x[0] for x in room_tuples])
        
        area_diff = []
        if _radial_area_groups[0].radial_area.a2 - _radial_area_groups[0].radial_area.a1 > math.pi *1.2:
            # 너무 통합되어서 커진 경우
            return [] 
        for area_group in _radial_area_groups:
            area_diff.append(area_total - area_group.area)
            if self.area_is_similar(area_total, area_group.area):
                matching_area_groups.append(area_group)

        if all([a > 0 for a in area_diff]): 
            combine_level += 1
            _radial_area_groups = self.get_combined_area_groups(_radial_area_groups, combine_level)
            return self.find_matching_area_groups(_radial_area_groups, room_tuples, combine_level)
        
        return matching_area_groups

    def create_seeds_in_scenarios(self):
        for scenario in self.scenarios:
            if len(scenario.seeds) == 0:
                scenario.create_seeds()

    def connect_all_area_groups(self, area_group_list):
        for i in range(len(area_group_list)):
            ag = area_group_list[i]
            ag.prev = area_group_list[i-1]
            ag.next = area_group_list[(i+1)%len(area_group_list)]
        return area_group_list
    
    def process(self):
        first_positions = self._get_first_init_position()
        # 첫번째 배치되는 시나리오 찾기
        if len(first_positions) == 0:
            return [], self.skipped_area_cluster
        print(first_positions)
        sc.sticky["pos"] = first_positions
        first_position_scenraios = self._get_first_position_scenario(first_positions) # type: List[PositionScenario]
        # 시나리오 별로 area_group이 첫번째 배치되는 area_group만 있으므로 mass의 원본을 찾아서 이어준다.
        if len(first_position_scenraios) == 0:
            return [], self.skipped_area_cluster
        
        for scenario in first_position_scenraios:
            full_area_groups = self._fill_vacant_area_group(scenario.init_area_group_list)
            full_area_groups = self.connect_all_area_groups(full_area_groups)
            scenario.area_group_list = full_area_groups

        self.scenarios = first_position_scenraios

        print("first_position_scenario_counts : {}".format(len(first_position_scenraios)))
        self.create_seeds_in_scenarios()
        
        res = []
        for i, scenario in enumerate(first_position_scenraios):
            print("{} scenario process working".format(i))
            res.extend(scenario.process())
            

        res_filled = []
        for res_area_groups in res:
            full_area_groups = self._fill_vacant_area_group(res_area_groups)
            full_area_groups = self.connect_all_area_groups(full_area_groups)
            res_filled.append(full_area_groups)

        return res_filled, self.skipped_area_cluster
        
    def _fill_vacant_area_group(self, area_groups):
        # type: (List[RadialAreaGroup]) -> None
        original_area_groups = [area_group.duplicate() for area_group in self.mass.radial_area_groups]
        
        def get_intersect_area_group(check_area_group, area_groups):
            """area_group, area_groups. 
            area_groups 중에서 area_group과 겹치는 area_group을 반환한다."""
            for area_group in area_groups:
                if check_area_group_intersection(area_group, check_area_group):
                    return area_group
                else:
                    pass
            return None
        
        full_area_groups = []
        for area_group in original_area_groups:
            interesect_area_group = get_intersect_area_group(area_group, area_groups)
            if interesect_area_group:
                if interesect_area_group in full_area_groups:
                    pass
                else:
                    full_area_groups.append(interesect_area_group)
            else:
                full_area_groups.append(deepcopy(area_group))

        return full_area_groups
            
            
    def _get_first_position_scenario(self, first_positions):
        '''첫번째 진입가능한 position을 찾는다.'''
        
        scenarios = [] # type: List[PositionScenario]
        for area_cluster, area_group_cands, first_area_data in first_positions:
            if len(scenarios) == 0:
                for area_group in area_group_cands:
                    position_scenario = PositionScenario()
                    position_scenario.add(area_cluster, area_group, first_area_data)
                    scenarios.append(position_scenario)
            else:
                next_scnearios = []
                for scenario in scenarios:
                    for area_group in area_group_cands:
                        scenario_new = deepcopy(scenario)
                        scenario_new.add(area_cluster, area_group, first_area_data)
                        if scenario_new.is_valid():
                            next_scnearios.append(scenario_new)
                        else:
                            pass
                print("NEXT")
                for scenario in next_scnearios:
                    print(scenario.init_area_group_list)
                if len(next_scnearios) == 0 :
                    return []
                scenarios = next_scnearios
       
        # res = [] 
        # for scenario in scenarios:
        #     if scenario.is_valid():
        #         res.append(scenario)
        # print(len(res))
        return scenarios

    def _get_first_init_position(self):

        mass = self.mass
        area_distribute_option = self.area_distribute_option

        # sort area_distribute_option
        total_areas = [] 

        for area_cluster in area_distribute_option:
            total_areas.append(area_cluster.pop('total'))
            
        sorted_list = sorted(zip(total_areas, area_distribute_option))
        sorted_list.reverse()
        sorted_area_cluster = [x[1] for x in sorted_list]
        first_positions = [] 
        for area_cluster in sorted_area_cluster:
            radial_area_groups = [area_group.duplicate() for area_group in mass.radial_area_groups]
            
            # sort area_cluster:
            room_names = area_cluster.keys()
            areas = area_cluster.values()
            sorted_rooms = sorted(zip(areas, room_names))
            sorted_rooms.reverse()
            if self.check_too_small(sorted_rooms):
                print("TOO SMALL")
                self.skipped_area_cluster.append(area_cluster)
                continue
            matching_area_groups = []
            print(sorted_rooms)
            for i in range(len(sorted_rooms)):
                rooms = sorted_rooms[:i+1]
                if sum([room[0] for room in rooms]) > 230:
                    break
                combine_level = 0
                matching_area_groups_from_rooms = self.find_matching_area_groups(radial_area_groups, rooms, combine_level)
                
                matching_area_groups.extend(matching_area_groups_from_rooms)
                
                if len(matching_area_groups) == 0:
                    print("NOMATCH")
                    return []
            print(len(matching_area_groups))
            first_positions.append((area_cluster, matching_area_groups, rooms))
        
        return first_positions