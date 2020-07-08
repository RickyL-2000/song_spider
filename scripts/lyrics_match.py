# %%
import difflib
import csv
import os
import json


# %%
# difflib trytrywater
def get_equal_rate_1(str1, str2):
    return difflib.SequenceMatcher(None, str1, str2).quick_ratio()


# %%
class LyricsMatch:
    """
    秒级别进行乐句对齐
    1. 遍历lrc歌词中的每一句，在qrc歌词中找到匹配段，通过 difflib
    2. 以200ms的阈值定位该句的pitch
    3. 通过lrc歌词中的时间戳来拉伸qrc歌词中的时间戳
        拉伸方法：定位要拉伸的句子之后，将该句子的大致时间段抽出，并用该时间段定位要拉伸的乐谱的乐句，然后同时拉伸。
                与此同时，要记录被修改过的pitch的日志，需要在最后遍历一遍把遗漏的未修改过的pitch进行平均拟合。
                因为note和歌词并不能对齐
    """
    class Matcher:
        def __init__(self, number, base_dir):
            self.number = number
            self.base_dir = base_dir
            self.lrc = []       # 这是和audio相匹配的歌词
            self.raw_qrc = []   # 这是数据集里自带的歌词，与audio不一定匹配
                                # 元素格式：[[总时间戳], [时间戳序列], 歌词字符串]
            self.raw_pitch = [] # 这是数据集里自带的乐谱
            self.qrc = []       # 这是处理拉伸后的歌词，与audio匹配
            self.pitch = []     # 这是处理拉伸后的乐谱

        def load_lrc(self):
            with open(self.base_dir + "/processed_data/lrc/{}.csv".format(self.number), 'r') as f:
                reader = csv.DictReader(f)
                for item in reader:
                    self.lrc.append([item['time'], item['value']])

        def load_raw_qrc(self):
            raw_qrc = []
            with open(self.base_dir + "/raw_data/alldata/{}.json".format(self.number), 'r') as f:
                data = f.readline()
                json_data = json.loads(data)
                raw_qrc = json_data['qrc']
            start = raw_qrc.find("[offset:")
            start = raw_qrc.find("[", start + 1)
            end = raw_qrc.find("/>", start) - 2
            raw_qrc_list = raw_qrc[start:end].split("\n")
            # 解析每一句
            for sentence in raw_qrc_list:
                sentence = sentence.strip()
                # 总时间戳
                start = sentence.find("[")
                end = sentence.find("]")
                duration = sentence[start+1:end].split(",")
                duration = [int(duration[0]), int(duration[1])]
                # 时间戳序列
                seq = []
                start = sentence.find("(")
                end = sentence.find(")")
                while start != -1:
                    node = sentence[start+1:end].split(",")
                    node = [int(node[0]), int(node[1])]
                    seq.append(node)
                    start = sentence.find("(", start+1)
                    end = sentence.find(")", end+1)
                # 歌词
                phrase = ""
                start = sentence.find("(")
                while start != -1:
                    phrase = phrase + sentence[start-1]
                    start = sentence.find("(", start+1)
                self.raw_qrc.append([duration, seq, phrase])

        def load_raw_pitch(self):
            with open(self.base_dir + "/raw_data/alldata/{}.json".format(self.number), 'r') as f:
                data = f.readline()
                json_data = json.loads(data)
                raw_notes = json_data['note']

            notes_list = raw_notes.split("\n")
            self.raw_pitch = []
            length = int(len(notes_list) / 3)
            for i in range(length):
                self.raw_pitch.append([int(notes_list[3*i]), int(notes_list[3*i+1]), int(notes_list[3*i+2])])



    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.log = []
        self.batch_size = 100
        self.all_data_num = 72898

    def init_log(self):
        if os.path.getsize(self.base_dir + "/helpers/match_log.csv"):
            with open(self.base_dir + "helpers/match_log.csv", 'r') as log:
                reader = csv.reader(log)
                self.log = [0]  # NOTE: 从1开始，第零个只是placeholder
                for status in reader:
                    self.log.append(status)
        else:
            self.log = [0] * (72898+1)

    def write_log(self):
        with open(self.base_dir + "helpers/match_log.csv", 'w') as log:
            writer = csv.writer(log)
            # for status in self.log:
            #     writer.writerow(status)
            for i in range(1, len(self.log)):
                writer.writerow(self.log[i])

    def main(self):
        for i in range(1, self.all_data_num, self.batch_size):
            self.init_log()
            for number in range(i, min(i + self.batch_size, self.all_data_num + 1)):
                matcher = self.Matcher(number, base_dir)
                pass
