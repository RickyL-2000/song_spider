# coding=utf-8

# if __name__ == "__main__":
#     pass

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
import codecs
import csv
from bs4 import BeautifulSoup as bs4
import os
import requests
from typing import List

poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)


# %%
class CrawlerQQkg:
    """
    1. 将raw_titles中的所有非数字的歌曲进入模拟器中查询，提取出链接，批量进行，存入raw_urls，并记录log
    2. 对所有url进行爬取
    """
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.all_data_num = 72898
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101 Firefox/61.0"}

        self.titles = []    # 元素格式：[idx, 歌名]
        self.singers = []   # 元素格式：[idx, 歌手名称]
        self.url_list: List[List] = [None] * (self.all_data_num + 1)    # NOTE: 从1开始; 元素格式为该歌曲不同用户投稿的List

        self.url_log = []   # 0为未下载，大于零则为获得的链接的数量
        self.audio_log = []

        # init methods
        self.load_titles()
        self.load_singers()

    def load_titles(self):
        with open(self.base_dir + "/raw_data/raw_titles.txt", 'r', encoding='utf-8') as titles:
            cnt = 0
            self.titles.append(None)    # NOTE
            for title in titles.readlines():
                if title[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
                    title = title[codecs.BOM_UTF8:]
                cnt += 1
                self.titles.append([cnt, title.strip()])    # 从1开始

    def load_singers(self):
        with open(self.base_dir + "/raw_data/raw_singers.txt", 'r', encoding='utf-8') as singers:
            cnt = 0
            self.singers.append(None)   # NOTE
            for singer in singers.readlines():
                if singer[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
                    singer = singer[codecs.BOM_UTF8:]
                cnt += 1
                self.singers.append([cnt, singer])

    def load_url_log(self):
        if os.path.getsize(self.base_dir + "/helpers/crawler_qqkg_url_log.csv"):
            with open(self.base_dir + "/helpers/crawler_qqkg_url_log.csv", 'r') as log:
                reader = csv.reader(log)
                self.url_log = [0]  # NOTE: 从1开始，第零个只是placeholder
                for status in reader:
                    self.url_log.append(status)
        else:
            self.url_log = [0] * (72898 + 1)

    def write_url_log(self):
        with open(self.base_dir + "/helpers/crawler_qqkg_url_log.csv", 'w') as log:
            writer = csv.writer(log)
            # for status in self.log:
            #     writer.writerow(status)
            for i in range(1, len(self.url_log)):
                writer.writerow(self.url_log[i])

    def load_url_list(self):
        idx = 1
        if os.path.getsize(self.base_dir + "/raw_data/url_list.txt"):
            with open(self.base_dir + "/raw_data/url_list.txt", 'r') as f:
                for line in f.readlines():
                    self.url_list[idx] = line.strip().split()
                    idx += 1

    def write_url_list(self):
        with open(self.base_dir + "/raw_data/url_list.txt", 'w') as f:
            for song in self.url_list:
                if song is not None and len(song) > 0:
                    for url in song:
                        f.write(url + ' ')
                f.write('\n')

    def query(self, idx):
        """
        利用poco模拟屏幕点击，在全民K歌上爬取歌曲的分享链接
        :param idx: 歌曲的索引
        """
        # poco(name="com.tencent.karaoke:id/gvd").click()  # 点击搜索框 NOTE: 该操作移至该函数外完成，节省时间
        poco(name="com.tencent.karaoke:id/g02").set_text(self.titles[idx][1])  # 输入歌名
        poco(name="com.tencent.karaoke:id/gvk").click()  # 点击“搜索”
        candidate_list = poco(name="com.tencent.karaoke:id/cvx")  # 获取推荐
        singer_list = []
        for candidate in candidate_list:
            singer = candidate.offspring(name="com.tencent.karaoke:id/cw6").get_text()
            if singer[-3:] == " · ":
                singer = singer[:-3]
            # print(singer)
            singer_list.append(singer)

        i = singer_list.index(self.singers[idx][1].strip())

        if i >= 0:
            poco(name="com.tencent.karaoke:id/cvx")[i].click()
        else:
            poco(name="com.tencent.karaoke:id/cvx")[0].click()

        poco(name="总榜").click()  # 点击总榜

        cnt = 0  # 要5首歌
        flag = 0    # 用于检测一个页面滑动的最大次数。假设最多滑动3次，超过自动放弃
        visited = []  # 已经下载了的作品的用户名
        ret = []    # 该首歌的url资源
        parent = poco(name="com.tencent.karaoke:id/fr")
        maxNum = 3
        while cnt < maxNum:
            # swipe((432, 1455), (432, 1000))
            try:
                work_list = parent.poco(name="com.tencent.karaoke:id/f4")  # 当前页面的推荐作品
            except:
                break   # 如果该歌曲没有人唱过

            if flag >= 3:   # 可能出现了意想不到的情况导致cnt不满足要求但是陷入死循环，此时放弃
                break

            for work in work_list:
                cur_usr_name = work.get_text()
                if cur_usr_name in visited or cur_usr_name[-1] == ' ':  # 用户名
                    continue
                visited.append(cur_usr_name)
                work.click()  # 进入该用户的歌曲页面

                # 进入页面
                try:
                    poco(name="com.tencent.karaoke:id/u1").click()  # 点击分享
                except:
                    continue

                # 该用户可能已经不存在
                try:
                    # poco.swipe([500, 1000], [300, 1000])
                    poco(name="com.tencent.karaoke:id/eou").poco(name="com.tencent.karaoke:id/hh3")[-1].click()  # 点复制链接
                    if len(ret) > 0:
                        assert pyperclip.paste() != ret[-1]    # 防止各种奇奇怪怪的问题
                except:
                    keyevent("KEYCODE_BACK")
                    continue

                ret.append(pyperclip.paste())
                cnt += 1

                # poco(name="返回").click()
                keyevent("KEYCODE_BACK")

                if cnt >= maxNum:
                    break

            if cnt < maxNum:
                swipe((432, 1455), (432, 700))
                flag += 1

        if len(ret) > 0:
            self.url_list[idx] = ret
            self.url_log[idx] = len(ret)

        # 返回
        # poco(name="返回").click()
        keyevent("KEYCODE_BACK")

    def get_url(self, batch_size):
        for i in range(1, self.all_data_num + 1, batch_size):
            self.load_url_log()
            self.load_url_list()
            poco(name="com.tencent.karaoke:id/gvd").click()  # 点击搜索框
            for j in range(i, min(i + batch_size, self.all_data_num + 1)):
                if self.titles[j][1][0].isdigit():
                    continue
                if self.url_log[j]:     # have downloaded
                    continue
                self.query(j)
            self.write_url_log()
            self.write_url_list()

    def load_audio_log(self):
        if os.path.getsize(self.base_dir + "/helpers/crawler_qqkg_audio_log.csv"):
            with open(self.base_dir + "/helpers/crawler_qqkg_audio_log.csv", 'r') as log:
                reader = csv.reader(log)
                self.audio_log = [0]  # NOTE: 从1开始，第零个只是placeholder
                for status in reader:
                    self.audio_log.append(status)
        else:
            self.audio_log = [0] * (72898 + 1)

    def write_audio_log(self):
        with open(self.base_dir + "/helpers/crawler_qqkg_audio_log.csv", 'w') as log:
            writer = csv.writer(log)
            # for status in self.log:
            #     writer.writerow(status)
            for i in range(1, len(self.audio_log)):
                writer.writerow(self.audio_log[i])

    def download(self, url, idx, j):
        """
        爬取响应的音频数据
        :param url: 该歌曲资源的链接
        :param idx: 该歌曲的索引，从1开始
        :param j: 是该歌曲的第几首歌，从1开始
        """
        html = requests.get(url, headers=self.headers).text
        soup = bs4(html, 'html.parser')
        target = soup.find('audio', id="player")
        src_url = target['src']
        try:
            response = requests.get(src_url, headers=self.headers, stream=True)
            with open(self.base_dir + "/audios/raw_audios/{}({}).mp3".format(idx, j), 'wb') as song_file:
                for chunk in response.iter_content(chunk_size=512):
                    song_file.write(chunk)
            self.audio_log[idx] += 1    # NOTE: 从1开始
            print("{}({}) --- successfully downloaded".format(idx, j))
        except:
            # self.log[title[0]] = 0
            print("{}({}) --- downloading failed".format(idx, j))

    def get_audio(self, batch_size):
        self.load_url_list()
        for i in range(1, self.all_data_num + 1, batch_size):
            self.load_audio_log()
            for idx in range(i, min(i + batch_size, self.all_data_num + 1)):
                if self.audio_log[i] > 0:   # had downloaded
                    continue
                if self.url_list[idx] is not None and len(self.url_list) > 0:
                    for j in range(len(self.url_list[idx])):    # 对所有与该歌曲同名的歌曲进行爬取
                        self.download(self.url_list[idx][j], idx, j+1)  # j从1开始
            self.write_audio_log()

    def test(self):
        self.load_url_log()
        self.write_url_log()


# %%
if __name__ == "__main__":
    crawler = CrawlerQQkg("E:/song_spider")
    # crawler.get_url(5)
    crawler.test()
