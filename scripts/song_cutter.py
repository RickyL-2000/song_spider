# %%
import os
import json
from pydub import AudioSegment

base_dir = os.getcwd()

# %%
def load_qrc():
    """
    获取所有歌曲的歌词数据
    :return: all_qrc 元素格式：all_qrc[i] = song_qrc
                             song_qrc[i] = [duration, seq, phrase]
                             duration = [start, end]
                             seq[i] = [start, end]
                             phrase = 歌词
    """
    with open(base_dir + '/alldata.json', 'r', encoding='utf-8') as f:
        all_qrc = [[]]
        for line in f.readlines():
            json_line = json.loads(line)
            raw_qrc = json_line['qrc']
            start = raw_qrc.find("[offset:")
            start = raw_qrc.find("[", start + 1)
            end = raw_qrc.find("/>", start) - 2
            raw_qrc_list = raw_qrc[start: end].split("\n")

            # 每一首歌的
            song_qrc = []
            for sentence in raw_qrc_list:
                # 总时间戳
                start = sentence.find("[")
                end = sentence.find("]")
                duration = sentence[start + 1: end].split(",")
                duration = [int(duration[0].strip()), int(duration[1].strip())]

                # 时间戳序列
                seq = []
                start = sentence.find("(")
                end = sentence.find(")")
                while start != -1:
                    node = sentence[start+1: end].split(",")
                    node = [int(node[0].strip()), int(node[1].strip())]
                    seq.append(node)
                    start = sentence.find("(", start + 1)
                    end = sentence.find(")", end + 1)

                # 歌词
                phrase = ""
                start = sentence.find("(")
                while start != -1:
                    phrase = phrase + sentence[start - 1]
                    start = sentence.find("(", start + 1)

                song_qrc.append([duration, seq, phrase])

            all_qrc.append(song_qrc)

    return all_qrc

# %%
def get_phrases(song_id):
    """
    返回以[句开始时间，句结束时间]为元素的list
    :param song_id:
    :return:
    """
    pass

# %%
def song_cut():
    start_point = 0
    all_data_num = 72898
    for i in range(start_point, all_data_num):
        for j in range(3):
            file_name = r"{}({}).mp3".format(i, j)
            if os.path.getsize(base_dir + "/audios/raw_audios/" + file_name):
                input_song = AudioSegment.from_mp3(base_dir + "/audios/raw_audios/" + file_name)
                output_song = input_song[:]
                output_song.export(base_dir + '/audios/phrases/')
