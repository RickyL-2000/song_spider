# %%
import difflib
import csv
import os
import json
import librosa
import pyworld as pw
import numpy as np


# %%
class LyricsMatch:
    """
    秒级别进行乐句对齐
    1. 遍历qrc歌词中的每一句，在lrc歌词中找到匹配段，通过 difflib
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
            self.lrc = []           # 这是和audio相匹配的歌词
                                    # 元素格式：[时间，歌词字符串]
            self.raw_qrc = []       # 这是数据集里自带的歌词，与audio不一定匹配，按句分
                                    # 元素格式：[[总时间戳(开始，持续时间)], [时间戳序列], 歌词字符串]
            self.raw_pitch = []     # 这是数据集里自带的乐谱
                                    # 元素格式：[开始时间，持续时间，音高]
            self.grouped_pitch = []   # 经过按照qrc乐句分组之后的group
                                    # 元素格式：[按照乐句分组的一句pitch]
            self.qrc = []           # 这是处理拉伸后的歌词，与audio匹配
            self.pitch = []         # 这是处理拉伸后的乐谱

        def load_lrc(self):
            with open(self.base_dir + "/processed_data/lrc/{}.csv".format(self.number), 'r') as f:
                reader = csv.DictReader(f)
                for item in reader:
                    self.lrc.append([item['time'], item['value']])

        def load_raw_qrc(self):
            with open(self.base_dir + "/raw_data/alldata/{}.json".format(self.number), 'r', encoding='utf-8') as f:
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
            with open(self.base_dir + "/raw_data/alldata/{}.json".format(self.number), 'r', encoding='utf-8') as f:
                data = f.readline()
                json_data = json.loads(data)
                raw_notes = json_data['note']

            notes_list = raw_notes.split()
            self.raw_pitch = []
            length = int(len(notes_list) / 3)
            for i in range(length):
                self.raw_pitch.append([int(notes_list[3*i]), int(notes_list[3*i+1]), int(notes_list[3*i+2])])

        def pitch_grouping(self):
            # NOTE: 如果有不归属于任何乐句的音高，就归为前一句
            pre_end_idx = -1
            for i in range(len(self.raw_qrc)):
                start_time, end_time = self.raw_qrc[i][0][0], self.raw_qrc[i][0][0] + self.raw_qrc[i][0][1]
                start_idx = end_idx = pre_end_idx + 1
                # 应该不会遇到找不到的问题？
                # NOTE: 200ms阈值定位
                while start_idx < len(self.raw_pitch) and abs(self.raw_pitch[start_idx][0] - start_time) > 200:
                    start_idx += 1
                while end_idx < len(self.raw_pitch) and \
                        abs(self.raw_pitch[end_time][0] + self.raw_pitch[end_time][1] - end_time) > 200:
                    end_idx += 1
                # 处理落单start
                if pre_end_idx - start_idx > 1 and len(self.grouped_pitch) > 0:
                    # 如果在当前句和前一句之间有落单的note
                    for idx in range(pre_end_idx + 1, start_idx):
                        self.grouped_pitch[-1].append(self.raw_pitch[idx])
                elif pre_end_idx - start_idx > 1 and len(self.grouped_pitch) == 0:
                    start_idx = 0
                # 处理落单end
                pre_end_idx = end_idx
                self.grouped_pitch.append([self.raw_pitch[i] for i in range(start_idx, end_idx + 1)])
            # 暂时希望如此，如果出错了再想办法
            assert len(self.qrc) == len(self.grouped_pitch)

        def read_wav(self):
            # 还是在test阶段
            y, fs = librosa.load(self.base_dir + r"/audios/separate/18291/vocals.wav", dtype=float)
            return y, fs

        @staticmethod
        def extract_f0(y, fs):
            f0, t = pw.dio(y, fs)
            return f0, t

        @staticmethod
        def pitch2freq(pitch):
            return 440 * 2 ** ((pitch - 69) / 12)

        @staticmethod
        def str_similarity(str1, str2):
            return difflib.SequenceMatcher(None, str1, str2).quick_ratio()

        def find_match_sentence(self, idx, qrc_found, lrc_visited) -> int:
            """
            输入一句qrc歌词，在lrc歌词中找到匹配的一段，返回匹配段的位置(索引)
            :param idx: 输入的qrc歌词的索引
            :param qrc_found: helper
            :param lrc_visited: helper
            :return: 对应的
            """
            score = []
            for j in range(len(self.lrc)):
                if lrc_visited[j]:
                    score.append(0.0)
                    continue
                score.append(self.str_similarity(self.raw_qrc[idx][2], self.lrc[idx][1]))
            # 找出最相近的
            pos = score.index(max(score))
            lrc_visited[pos] = True
            qrc_found[idx] = True
            return pos

        def distance(self):
            # 计算一段音频和一段数字频率序列的距离
            pass

        def stretch(self, idx, position):
            """
            将qrc中的歌词的时间戳线性变换以对齐audio的lrc，存放在self.qrc中
            :param idx: qrc的索引
            :param position: lrc的索引
            :return: None
            """
            qrc_duration = self.raw_qrc[idx][0][1]  # qrc中该句的持续时间
            lrc_duration = self.lrc

        def save_qrc(self):
            pass

        def save_pitch(self):
            pass

        def main(self):
            qrc_found = [False] * len(self.raw_qrc)
            lrc_visited = [False] * len(self.lrc)
            for idx in range(len(self.raw_qrc)):
                position = self.find_match_sentence(idx, qrc_found, lrc_visited)
                matched_lrc = self.lrc[position]
                pitch_group = self.grouped_pitch[idx]
                # TODO: 接下来是第三步
                # 拉伸
                self.stretch(idx, position)

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
                matcher = self.Matcher(number, self.base_dir)
                pass

    def test(self):
        matcher = self.Matcher(18291, self.base_dir)
        matcher.load_lrc()
        matcher.load_raw_qrc()
        matcher.load_raw_pitch()
        pass


# %%
if __name__ == "__main__":
    process = LyricsMatch(r"E:/song_spider")
    process.test()
