import pandas as pd
import json
import math

name_dict = {
'사무실' :'office',
'회의실' :'meeting_room',
'장비실' :'tool_room',
'창고(수장)' :'storage',
'커뮤니티홀, 복도' :'community_corridor',
'화장실' :'toilet',
'계단실' :'stair',
'기계전기실' :'mech_room',
'전시/체험실' : 'exhibit_experience',
'체험실2' : 'experience2',
'토론방' : 'discuss_room',
'프로그램실1' : 'program1',
'프로그램실2'  : 'program2',
'전시준비실'  : 'exhibit_planning_room',
'무인카페' : 'unman_cafe',
'주방' : 'kitchen',
'주방창고' : 'kitchen_storage',
'안내휴게실' : 'reception',
'숙사1' : 'dorm1',
'숙사2' : 'dorm2',
'당직실' : 'night_work_room',
'탈의실/샤워실' : 'shower and change',
}

def is_nan(x):
    return type(x) == float and math.isnan(x)

def df_to_area_options(dataframe):
    options = []
    option_group = [] 
    area_dict = {} 
    for i, row in dataframe.iterrows():
        if is_nan(row[0]) and not is_nan(row[1]): # 면적 그룹 구분선
            area_dict["total"] = row[1]
            option_group.append(area_dict)
            area_dict = {}

        elif is_nan(row[0]) and is_nan(row[1]): # 옵션 구분선
            options.append(option_group)
            area_dict = {}
            option_group = []

        else:
            name_englist = name_dict[row[0]]
            area_dict[name_englist] = row[1]
    
    return options
    
def load_detail_area(file_name):
    df = pd.read_csv(f"{file_name}.csv", encoding = "cp949")
    area_options = df_to_area_options(df)
    

    with open (f"{file_name}.json", "w", encoding='utf-8') as f:
       json.dump(area_options, f, indent=4, ensure_ascii=False)

file_name_list = ["area_detail_a1", "area_detail_a2", "area_detail_b"] 
for file_name in file_name_list:
    load_detail_area(file_name)
