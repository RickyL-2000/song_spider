# coding=utf-8

# if __name__ == "__main__":
#     pass

# %%
"""
爬取全民K歌
此版本适用于在mi2机器上爬取链接，不适用于爬取音频
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
import time

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

        self.url_log = []   # 0为未下载，大于零则为获得的链接的数量，从1开始，最后多一个数据，为上次下载断掉时的位置
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
        if os.path.getsize(self.base_dir + "/helpers/crawler_qqkg_url_log.txt"):
            with open(self.base_dir + "/helpers/crawler_qqkg_url_log.txt", 'r') as log:
                self.url_log = [0]  # NOTE: 从1开始，第零个只是placeholder
                for status in log.readlines():
                    self.url_log.append(int(status.strip()))
        else:
            self.url_log = [0] * (72898 + 2)    # 从1开始，最后多一个中断信号
        return self.url_log.pop()

    def write_url_log(self, break_point):
        with open(self.base_dir + "/helpers/crawler_qqkg_url_log.txt", 'w') as log:
            for i in range(1, len(self.url_log)):
                log.write(str(self.url_log[i]) + '\n')
            log.write(str(break_point) + '\n')

    def load_url_list(self):
        if os.path.getsize(self.base_dir + "/raw_data/url_list.txt"):
            self.url_list = [None]
            with open(self.base_dir + "/raw_data/url_list.txt", 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    self.url_list.append(line.strip().split())

    def write_url_list(self):
        with open(self.base_dir + "/raw_data/url_list.txt", 'w', encoding='utf-8') as f:
            for i in range(1, len(self.url_list)):
                if self.url_list[i] is not None and len(self.url_list[i]) > 0:
                    for url in self.url_list[i]:
                        f.write(url + ' ')
                f.write('\n')

    def query(self, idx):
        """
        利用poco模拟屏幕点击，在全民K歌上爬取歌曲的分享链接
        :param idx: 歌曲的索引
        """
        try:
            # poco(name="com.tencent.karaoke:id/gvd").click()  # 点击搜索框 NOTE: 该操作移至该函数外完成，节省时间
            poco(name="com.tencent.karaoke:id/g02").set_text(self.titles[idx][1])  # 输入歌名
            poco(name="com.tencent.karaoke:id/gwa").click()  # 点击“搜索”
            candidate_list = poco(name="com.tencent.karaoke:id/cvx")  # 获取推荐
        # except:
            # return  # 以防止出现各种奇怪的无法预料的问题

        # try:
            singer_list = []
            for candidate in candidate_list:
                singer = candidate.offspring(name="com.tencent.karaoke:id/cw6").get_text()
                if singer[-3:] == " · ":
                    singer = singer[:-3]
                # print(singer)
                singer_list.append(singer)

            i = singer_list.index(self.singers[idx][1].strip())
            poco(name="com.tencent.karaoke:id/cvx")[i].click()
        except:
            # poco(name="com.tencent.karaoke:id/cvx")[0].click()
            return  # 没有该歌手 （没有该歌曲）

        poco(name="总榜").click()  # 点击总榜

        cnt = 0  # 要3首歌
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

            try:    # 我佛了，为什么之前的检查过了这里会不过？
                for work in work_list:
                    cur_usr_name = work.get_text()
                    if cur_usr_name in visited or cur_usr_name[-1] == ' ':  # 用户名
                        continue
                    visited.append(cur_usr_name)
                    work.click()  # 进入该用户的歌曲页面

                    # 进入页面
                    try:
                        poco(name="com.tencent.karaoke:id/u1").click()  # 点击分享
                        swipe((700, 1555), (300, 1555))
                    except:
                        continue

                    # 该用户可能已经不存在
                    try:
                        # poco.swipe([500, 1000], [300, 1000])
                        poco(name="com.tencent.karaoke:id/eou").poco(name="com.tencent.karaoke:id/hjk")[-1].click()  # 点复制链接

                        url = self.readURLCmd(self.execCmd(r"adb shell am broadcast -a clipper.get"))   # 通过clipper服务获取剪贴板内容

                        if len(ret) > 0:
                            assert url != ret[-1]    # 防止各种奇奇怪怪的问题
                    except:
                        keyevent("KEYCODE_BACK")
                        continue

                    ret.append(url)
                    cnt += 1

                    # poco(name="返回").click()
                    keyevent("KEYCODE_BACK")

                    time.sleep(0.1)

                    if cnt >= maxNum:
                        break
            except:
                break

            if cnt < maxNum:
                swipe((432, 1455), (432, 700))
                time.sleep(0.1)
                flag += 1

        if len(ret) > 0:
            self.url_list[idx] = ret
            self.url_log[idx] = len(ret)

        # 返回
        # poco(name="返回").click()
        keyevent("KEYCODE_BACK")

        time.sleep(0.1)

    @staticmethod
    def execCmd(cmd):
        r = os.popen(cmd)
        text = r.read()
        r.close()
        return text

    @staticmethod
    def readURLCmd(result):
        start = result.find('"') + 1
        end = result.find('"', start+2)
        return result[start: end]

    def get_url(self, batch_size, resume=True):
        # 初始化clipper广播服务
        self.execCmd(r"adb shell am startservice ca.zgrs.clipper/.ClipboardService")

        begin = 1
        if resume:
            begin = self.load_url_log() + batch_size
        for i in range(begin, self.all_data_num + 1, batch_size):
            self.load_url_log()
            self.load_url_list()
            try:
                poco(name="com.tencent.karaoke:id/gw4").click()  # 点击搜索框
            except:
                pass
            for j in range(i, min(i + batch_size, self.all_data_num + 1)):
                try:
                    if self.titles[j][1][0].isdigit():
                        continue
                except IndexError:
                    print("There is a index error, j = ", j)
                    continue
                if self.url_log[j]:     # have downloaded
                    continue
                print(j)
                self.query(j)
            self.write_url_list()
            self.write_url_log(i)   # 该breakpoint是该批次的开始位置

    def load_audio_log(self):
        if os.path.getsize(self.base_dir + "/helpers/crawler_qqkg_audio_log.txt"):
            with open(self.base_dir + "/helpers/crawler_qqkg_audio_log.txt", 'r') as log:
                self.audio_log = [0]  # NOTE: 从1开始，第零个只是placeholder
                for status in log.readlines():
                    self.audio_log.append(int(status.strip()))
        else:
            self.audio_log = [0] * (72898 + 1)

    def write_audio_log(self):
        with open(self.base_dir + "/helpers/crawler_qqkg_audio_log.txt", 'w') as log:
            for i in range(1, len(self.audio_log)):
                log.write(str(self.audio_log[i]) + '\n')

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
        self.load_url_log()


# %%
if __name__ == "__main__":
    crawler = CrawlerQQkg(r"E:/song_spider")
    crawler.get_url(10)
    # crawler.test()
