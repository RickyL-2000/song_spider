# %%
# coding=utf-8

# %%
# 并发爬虫
# 此版本用于在服务器上进行高并发爬取音频


# %%
import requests
import os
from bs4 import  BeautifulSoup as bs4
import time
from typing import List
import threading

# %%
def load_url_list(base_dir):
    if os.path.getsize(base_dir + "/raw_data/url_list.txt"):
        url_list.append([])
        with open(base_dir + "/raw_data/url_list.txt", 'r', encoding='utf-8') as f:
            for line in f.readlines():
                url_list.append(line.strip().split())

def make_queue(startpoint=0):
    for i in range(len(url_list)-1, startpoint-1, -1):
        if url_list[i] is None or len(url_list[i]) == 0:
            continue
        for j in range(len(url_list[i])):
            url_queue.append(url_list[i][j])
            filename_queue.append("{}({}).mp3".format(i, j+1))

# %%
def threaded_crawler(url_queue: List, filename_queue: List, headers, base_dir, max_threads=10):

    def process_queue():
        while True:
            try:
                url = url_queue.pop()
                filename = filename_queue.pop()
            except IndexError:
                # queue is empty
                break

            try:
                html = requests.get(url, headers=headers).text
                start = html.find('playurl') + 10
                end = html.find('"', start+1)
                src_url = html[start:end]
                response = requests.get(src_url, headers=headers, stream=True)
                with open(base_dir + "/audios/raw_audios/" + filename, "wb") as song_file:
                    for chunk in response.iter_content(chunk_size=512):
                        song_file.write(chunk)
                print(filename + " --- successfully downloaded", end='  ')
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                time.sleep(1)
            except:
                print(filename + " --- downloading failed", end='  ')
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    threads = []
    while threads or url_queue:
        # the crawler is still active
        for thread in threads:
            if not thread.is_alive():
                threads.remove(thread)
        while len(threads) < max_threads and url_queue:
            # can start some more threads
            thread = threading.Thread(target=process_queue)
            thread.setDaemon(True)  # 这样的话主线程可以在Ctrl+C的时候退出
            thread.start()
            threads.append(thread)
        time.sleep(1)

# %%
if __name__ == "__main__":
    base_dir = r"/home1/renyi/ry/lrq"
    all_data_num = 72898
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101 Firefox/61.0"}
    url_list = []
    url_queue = []
    filename_queue = []

    load_url_list(base_dir)
    make_queue()
    threaded_crawler(url_queue, filename_queue, headers, base_dir, max_threads=20)
