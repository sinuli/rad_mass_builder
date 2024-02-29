import os

folder_name = "first_res_m2"
print(os.getcwd()) # 현재 폴더(root)위치 파일들 출력

os.chdir(folder_name) # folder_name으로 위치 이동
print(os.listdir()) # folder_name 내부 파일들 이름 출력

file_names = os.listdir() # 내가 바꾸고 싶은 파일들의 이름 리스트

for file_name in file_names:
    new_name = file_name.replace("mass1", "mass2")
    os.rename(file_name,new_name) # 이름 바꾸기
