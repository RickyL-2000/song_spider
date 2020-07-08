# %%
if __name__ == "__main__":
    pass

import json
import xmltodict
import codecs
from lxml import etree

# %%
datapath = r"E:\song_spider"


# %%
# extract song titles and singers
def extract_titles_and_singers(datapath):
    title_list = []
    singer_list = []
    with open(datapath + r"\alldata.json", 'r', encoding='UTF-8-sig') as dataset:
        for line in dataset.readlines():
            if line[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
                line = line[codecs.BOM_UTF8:]
            json_song = json.loads(line)
            lyrics = json_song["qrc"]

            start = lyrics.find(r"[ti:")
            end = lyrics.find("]", start)
            title = lyrics[start+4:end]
            title_list.append(title)

            start = lyrics.find(r"[ar:")
            end = lyrics.find("]", start)
            singer = lyrics[start+4:end]
            singer_list.append(singer)

    with open(datapath + r"\raw_data\raw_titles.txt", 'w', encoding='UTF-8') as titles:
        for title in title_list:
            titles.write(title + '\n')

    with open(datapath + r"\raw_data\raw_singers.txt", 'w', encoding='UTF-8') as singers:
        for singer in singer_list:
            singers.write(singer + '\n')


# %%
# extract lyrics
def extract_lyrics(datapath):
    lyrics_list = []
    # cnt = 0
    with open(datapath + r"\alldata.json", 'r', encoding='UTF-8-sig') as dataset:
        for line in dataset.readlines():
            # cnt += 1
            # print(cnt)
            # if line[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
            #     line = line[codecs.BOM_UTF8:]
            # json_song = json.loads(line)

            lyrics_content = line[line.find("qrc"):]

            idx = lyrics_content.find(r"[offset:")
            idx = lyrics_content.find(r"]", idx+1)
            end = lyrics_content.find(r"\n", idx)
            sentence = ""
            while 0 < idx < len(lyrics_content):
                idx = lyrics_content.find(r"]", end)
                if idx < 0:
                    break
                if lyrics_content[idx+1] == "\\":
                    idx = lyrics_content.find(r"]", idx+1)
                end = lyrics_content.find(r"\n", idx + 1) - 4
                while 0 < idx < end:
                    sentence = sentence + lyrics_content[idx+1]
                    idx = lyrics_content.find(")", idx + 1)
                sentence = sentence + ' '
            lyrics_list.append(sentence)

    # print("done")

    with open(datapath + r"\raw_data\raw_lyrics.txt", 'w', encoding='UTF-8') as lyrics:
        for lyric in lyrics_list:
            lyrics.write(lyric + '\n')


# %%
# 查看有哪些歌曲的没有title的，即title是一串数字
def check_title_is_digits(datapath):
    digits_titles = []
    line_number = 0
    with open(datapath + r"\raw_data\raw_titles.txt", 'r', encoding='UTF-8-sig') as titles:
        for title in titles.readlines():
            line_number += 1
            if title[0].isdigit():
                digits_titles.append(line_number)

    with open(datapath + r"\helpers\digits_titles.txt", 'w', encoding='UTF-8-sig') as digits:
        for title in digits_titles:
            digits.write(str(title) + '\n')


# check_title_is_digits(datapath)

"""
在raw_titles.txt中，有5341首歌曲没有title，而是一串数字。对于70k的数据集来说这点暂时不管了。
"""


# %%
# 将alldata的每一行分成一个文件放在raw_data中
import codecs

with open('E:/song_spider/alldata.json', 'r', encoding='utf-8') as alldata:
    cnt = 0
    for line in alldata.readlines():
        if line[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
            line = line[codecs.BOM_UTF8:]
        cnt += 1
        with open('E:/song_spider/raw_data/alldata/{}.json'.format(cnt), 'w', encoding='utf-8') as f:
            f.write(line)
