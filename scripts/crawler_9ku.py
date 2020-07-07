# coding=utf-8

# %%
# 爬取九酷音乐
# 搜索request: http://m.9ku.com/search/七里香/
# /html/head/script[2]/text()

# %%
import requests
from bs4 import BeautifulSoup as bs4
from bs4 import element
import os
import csv
import codecs


# %%
class Crawler_9ku:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.base_url = r"http://m.9ku.com"
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101 Firefox/61.0"}
        self.titles = []    # 元素是[标号, title]的list. NOTE: 第0个元素是None，标号从1开始！
        self.singers = []   # NOTE: 第0个元素是None，标号从1开始！
        self.log = []
        self.all_data_num = 72898
        self.batch_size = 10

        self.get_titles()
        self.get_singers()

    def get_titles(self):
        with open(self.base_dir + "/raw_data/raw_titles.txt", 'r', encoding='utf-8') as titles:
            cnt = 0
            self.titles.append(None)    # NOTE
            for title in titles.readlines():
                if title[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
                    title = title[codecs.BOM_UTF8:]
                cnt += 1
                self.titles.append([cnt, title.strip()])    # 从1开始

    def get_singers(self):
        with open(self.base_dir + "/raw_data/raw_singers.txt", 'r', encoding='utf-8') as singers:
            cnt = 0
            self.singers.append(None)   # NOTE
            for singer in singers.readlines():
                if singer[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
                    singer = singer[codecs.BOM_UTF8:]
                cnt += 1
                self.singers.append([cnt, singer])

    def get_html(self, url):
        page = requests.get(url, headers=self.headers)
        return page.text

    def query(self, title, target='audio'):
        """
        查询并调用get_song来下载音乐
        :param title: a tuple with [number, title], number starts from 1
        :param target: the target to query, audio or lyrics
        :return: None
        """
        # NOTE: title is not digits
        # url = self.base_url + "/" + title + "/"
        url = self.base_url + "/search/{}/".format(title[1])
        html = self.get_html(url)           # FIXME: 解决如果查不到音乐的问题。想法：检查musicList的状态，然后直接返回，失败不需要修改log
        soup = bs4(html, 'html.parser')
        musicList = soup.find('ul', class_="musicList")
        match_singer = False
        for music in musicList.contents:    # FIXME
            if type(music) != element.Tag:
                continue
            if music['class'] == "xinxiliu":
                continue
            singer = music.find('a', class_="t-singer").string
            if singer in self.singers[title[0]][1]:
                match_singer = True
                song = music.find('a', class_="t-song")
                break
        if not match_singer:
            # 只取第一个
            song = musicList.find('a', class_="t-song")
        url = self.base_url + song['href']
        html = self.get_html(url)
        if target == 'audio':
            self.get_audio(html, title)
        elif target == 'lyrics':
            self.get_lyrics(html, title)

    def get_audio(self, html, title):
        """
        Download the target audio
        :return: True if success, False if failed
        """
        soup = bs4(html, 'html.parser')
        player = soup.find('div', id="ku-player")   # FIXME: 这个id为什么找不到？
        audio = player.find('audio')
        src_url = audio['src']
        try:
            response = requests.get(src_url, headers=self.headers, stream=True)
            with open(self.base_dir + "/audios/raw_audios/{}.mp3".format(title[0]), 'wb') as song_file:
                for chunk in response.iter_content(chunk_size=512):
                    song_file.write(chunk)
            self.log[title[0]] = 1    # NOTE: 从1开始
            print("{} --- successfully downloaded".format(title[0]))
        except:
            # self.log[title[0]] = 0
            print("{} --- downloading failed".format(title[0]))

    def get_lyrics(self, html, title):
        """
        Download the qrc or lrc lyrics with time stamps.
        One song a file separately.
        """
        pass

    def init_log(self):
        if os.path.getsize(self.base_dir + "/helpers/crawler_log.csv"):
            with open(self.base_dir + "helpers/crawler_log.csv", 'r') as log:
                reader = csv.reader(log)
                self.log = [0]  # NOTE: 从1开始，第零个只是placeholder
                for status in reader:
                    self.log.append(status)
        else:
            self.log = [0] * (72898+1)

    def write_log(self, ):
        with open(self.base_dir + "helpers/crawler_log.csv", 'w') as log:
            writer = csv.writer(log)
            # for status in self.log:
            #     writer.writerow(status)
            for i in range(1, len(self.log)):
                writer.writerow(self.log[i])

    def main_audio(self):
        """
        The main function for searching the audio files
        :return:
        """
        for i in range(1, self.all_data_num + 1, self.batch_size):  # NOTE: 从1开始
            self.init_log()
            for j in range(i, min(i + self.batch_size, self.all_data_num + 1)):
                if self.titles[j][1][0].isdigit():
                    continue
                if self.log[j]:     # have downloaded
                    continue
                self.query(self.titles[j], target='audio')
            self.write_log()

    def main_lyrics(self):
        """
        The main function for searching the qrc or lrc lyrics
        :return:
        """
        pass


# %%
if __name__ == "__main__":
    base_dir = r"E:/song_spider"
    crawler = Crawler_9ku(base_dir)
    crawler.main_audio()
