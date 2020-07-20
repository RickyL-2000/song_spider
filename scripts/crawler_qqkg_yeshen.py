# coding=utf-8

if __name__ == "__main__":
    pass

# %%
"""
爬取全民K歌

设备：夜神模拟器 安卓5.0

1. 先通过search request获取该歌曲的列表，用rfind方法找到该歌手的isongmid
2.
"""

# %%
# import requests
# from bs4 import BeautifulSoup as bs4
# import urllib3
from airtest.core.api import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
import pyperclip

poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)

# %%
poco(name="com.tencent.karaoke:id/gvd").click() # 点击搜索框
poco(name="com.tencent.karaoke:id/g02").set_text("青春路上")    # 输入歌名
poco(name="com.tencent.karaoke:id/gvk").click() # 点击“搜索”
# candidate_list = poco(name="com.tencent.karaoke:id/cvx")    # 获取推荐
# singer_list = []
# for candidate in candidate_list:
#     singer = candidate.offspring(name="com.tencent.karaoke:id/cw6").get_text()
#     if singer[-3:] == " · ":
#         singer = singer[:-3]
#     print(singer)
#     singer_list.append(singer)

candidate = poco(name="com.tencent.karaoke:id/cvx")[0]
candidate.poco(name="com.tencent.karaoke:id/cw1").click()   # 点击目标项，进入该歌曲主页

cnt = 0     # 要5首歌
visited = []    # 已经下载了的作品的用户名
url_list = []
parent = poco(name="com.tencent.karaoke:id/fyn")
while cnt <= 5:
    work_list = parent.poco(name="android.widget.RelativeLayout")  # 当前页面的推荐作品
    for work in work_list:
        cur_usr_name = work.poco(name="com.tencent.karaoke:id/dfv").get_text()
        if cur_usr_name in visited:  # 用户名
            continue
        visited.append(cur_usr_name)
        work.poco(name="com.tencent.karaoke:id/b2n").click()    # 进入该用户的歌曲页面

        # 进入页面
        poco(name="com.tencent.karaoke:id/u1").click()  # 点击分享
        # poco.swipe([500, 1000], [300, 1000])
        poco(name="com.tencent.karaoke:id/eou").poco(name="com.tencent.karaoke:id/hh3")[-1].click()     # 点复制链接

        url_list.append(pyperclip.paste())

        cnt += 1

        poco(name="返回").click()

    swipe((432, 1455), (432, 300))

# %%
swipe((432, 1455), (432, 300))

# %%
parent = poco(name="com.tencent.karaoke:id/fyn")
work_list = poco("android.widget.LinearLayout").offspring("android:id/content").offspring("com.tencent.karaoke:id/gpt").offspring("com.tencent.karaoke:id/fyq").offspring("com.tencent.karaoke:id/fyo").child("android.widget.RelativeLayout")  # 当前页面的推荐作品
temp = [work.poco(name="com.tencent.karaoke:id/dfv").get_text() for work in work_list]
