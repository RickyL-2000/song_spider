# %%
import difflib
import csv
import os
import json
import librosa
import pyworld as pw
import numpy as np
from dtw import *
import copy
import matplotlib.pylab as plt
import scipy.signal as signal


# %%
class LyricsMatch:
    """
    秒级别进行乐句对齐
    1. 遍历qrc歌词中的每一句，在lrc歌词中找到匹配段，通过 difflib
    2. 以300ms的阈值定位该句的pitch
    3. 通过lrc歌词中的时间戳来拉伸qrc歌词中的时间戳
       拉伸方法：定位要拉伸的句子之后，将该句子的大致时间段抽出，并用该时间段定位要拉伸的乐谱的乐句，然后同时拉伸。
                与此同时，要记录被修改过的pitch的日志，需要在最后遍历一遍把遗漏的未修改过的pitch进行平均拟合。
                因为note和歌词并不能对齐
    """

    class Matcher:
        def __init__(self, number, base_dir):
            self.number = number
            self.base_dir = base_dir
            self.lrc = []                   # 这是和audio相匹配的歌词
                                            # 元素格式：[时间，歌词字符串]
            self.raw_qrc = []               # 这是数据集里自带的歌词，与audio不一定匹配，按句分
                                            # 元素格式：[[总时间戳(开始，持续时间)], [时间戳序列(开始，持续时间)], 歌词字符串]
            self.raw_pitch = []             # 这是数据集里自带的乐谱
                                            # 元素格式：[开始时间，持续时间，音高]
            self.grouped_raw_pitch = []     # 经过按照qrc乐句分组之后的group
                                            # 元素格式：[按照乐句分组的一句pitch]
            self.qrc = []                   # 这是处理拉伸后的歌词，与audio匹配，格式与raw相同
            self.grouped_pitch = []         # 这是处理拉伸后的分组乐谱

            self.y = []                     # audio的时间序列
            self.sr = 0                     # audio的采样率

            self.f0 = []                    # 音频的基频曲线
            self.t = []                     # 音频的基频的时间序列
                                            # 默认 5ms 为间隔。如果要修改该间隔，需要修改：stretch

            self.tempo_ratio = 0.0          # == lrc_duration / qrc_duration，和节奏(或者速度)的定义应该是相反的
            self.__idx_qrc2lrc = []         # 一个index的映射，即__idx_qrc2lrc[idx] = position，idx是qrc索引，position是lrc索引

        def load_lrc(self):
            with open(self.base_dir + "/processed_data/lrc/{}.csv".format(self.number), 'r') as f:
                reader = csv.DictReader(f)
                for item in reader:
                    self.lrc.append([int(item['time']), item['value']])

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
                duration = sentence[start + 1:end].split(",")
                duration = [int(duration[0]), int(duration[1])]
                # 时间戳序列
                seq = []
                start = sentence.find("(")
                end = sentence.find(")")
                while start != -1:
                    node = sentence[start + 1:end].split(",")
                    node = [int(node[0]), int(node[1])]
                    seq.append(node)
                    start = sentence.find("(", start + 1)
                    end = sentence.find(")", end + 1)
                # 歌词
                phrase = ""
                start = sentence.find("(")
                while start != -1:
                    phrase = phrase + sentence[start - 1]
                    start = sentence.find("(", start + 1)
                self.raw_qrc.append([duration, seq, phrase])
            self.qrc = copy.deepcopy(self.raw_qrc)  # 先准备着

        def load_raw_pitch(self):
            with open(self.base_dir + "/raw_data/alldata/{}.json".format(self.number), 'r', encoding='utf-8') as f:
                data = f.readline()
                json_data = json.loads(data)
                raw_notes = json_data['note']

            notes_list = raw_notes.split()
            self.raw_pitch = []
            length = int(len(notes_list) / 3)
            for i in range(length):
                self.raw_pitch.append([int(notes_list[3 * i]), int(notes_list[3 * i + 1]), int(notes_list[3 * i + 2])])

        def pitch_grouping(self):
            # NOTE: 如果有不归属于任何乐句的音高，就归为前一句
            pre_end_idx = -1
            for i in range(len(self.raw_qrc)):
                start_time = self.raw_qrc[i][0][0]
                # end_time = self.raw_qrc[i][0][0] + self.raw_qrc[i][0][1]
                end_time = self.raw_qrc[i][1][-1][0]  # 是结束的字的开始时间！不是整句的结束时间！
                start_idx = pre_end_idx + 1
                end_idx = start_idx + 1
                # 应该不会遇到找不到的问题？
                # NOTE: 250ms阈值定位
                # NOTE: 不能只通过阈值来锁定目标Note的位置，必须要用temp找最近的，因为有时候可能最近的的距离也超过阈值
                min_dist = float('inf')
                while start_idx < len(self.raw_pitch) and abs(self.raw_pitch[start_idx][0] - start_time) > 250:
                    dist = abs(self.raw_pitch[start_idx][0] - start_time)
                    if dist < min_dist:
                        min_dist = dist
                        start_idx += 1
                    else:
                        start_idx -= 1
                        break
                min_dist = float('inf')
                while end_idx < len(self.raw_pitch) and abs(self.raw_pitch[end_idx][0] - end_time) > 250:  # 结束的字的开始时间
                    dist = abs(self.raw_pitch[end_idx][0] - end_time)
                    if dist < min_dist:
                        min_dist = dist
                        end_idx += 1
                    else:
                        end_idx -= 1
                        break
                # 处理落单start
                if pre_end_idx - start_idx > 1 and len(self.grouped_raw_pitch) > 0:
                    # 如果在当前句和前一句之间有落单的note
                    for idx in range(pre_end_idx + 1, start_idx):
                        self.grouped_raw_pitch[-1].append(self.raw_pitch[idx])
                elif pre_end_idx - start_idx > 1 and len(self.grouped_raw_pitch) == 0:
                    start_idx = 0
                # 处理落单end
                pre_end_idx = end_idx
                self.grouped_raw_pitch.append(
                    [self.raw_pitch[i] for i in range(start_idx, end_idx + 1)])  # FIXME: index 问题
            # 暂时希望如此，如果出错了再想办法
            assert len(self.qrc) == len(self.grouped_raw_pitch)
            self.grouped_pitch = copy.deepcopy(self.grouped_raw_pitch)

        def load_f0(self):
            self.read_wav()
            self.f0, self.t = self.extract_f0(self.y, self.sr)
            # 中值滤波：参数=3
            self.f0 = signal.medfilt(self.f0, 5)

        def read_wav(self):
            # 还是在test阶段
            self.y, self.sr = librosa.load(self.base_dir + r"/audios/separate/{}/vocals.wav".format(self.number),
                                           dtype=float, sr=None)

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

        def get_idx_qrc2lrc(self):
            assert len(self.raw_qrc) != 0
            assert len(self.lrc) != 0
            qrc_found = [False] * len(self.raw_qrc)
            lrc_visited = [False] * len(self.lrc)
            for idx in range(len(self.raw_qrc)):
                self.__idx_qrc2lrc.append(self.find_match_sentence(idx, qrc_found, lrc_visited))
            # TODO: 解决有qrc没有找到对应lrc位置的问题

        def get_tempo_ratio(self):
            """
            NOTE: 在调用这个函数之前，必须先调用load_raw_pitch和load_lrc！
                  换言之，self.lrc和self.grouped_raw_pitch不能为空！
            """
            assert len(self.grouped_raw_pitch) != 0
            assert len(self.raw_qrc) != 0
            ratio_list = []
            for idx in range(1, len(self.raw_qrc)):
                pos = self.__idx_qrc2lrc[idx]
                pre_pos = self.__idx_qrc2lrc[idx - 1]
                lrc_dur = self.lrc[pos][0] - self.lrc[pre_pos][0]
                qrc_dur = self.raw_qrc[idx][0][0] - self.raw_qrc[idx - 1][0][0]
                ratio_list.append(lrc_dur / qrc_dur)
            self.tempo_ratio = sum(ratio_list) / len(ratio_list)

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
                score.append(self.str_similarity(self.raw_qrc[idx][2], self.lrc[j][1]))
            # 找出最相近的
            pos = score.index(max(score))
            lrc_visited[pos] = True
            qrc_found[idx] = True
            return pos

        @staticmethod
        def get_distance(seq1, seq2):
            # 计算一段音频和一段数字频率序列的距离
            alignment = dtw(seq1, seq2)
            return alignment.normalizedDistance

        @staticmethod
        def plot_alignment(seq1, seq2):
            alignment = dtw(seq1, seq2, keep_internals=True)
            alignment.plot(type="threeway")
            alignment.plot(type="twoway", offset=-200)

        def score2freq(self, sentence, start):
            """
            把(raw_)grouped_pitch中的一句乐谱转换成5ms为间隔的频谱
            :param sentence: 需要转换的某乐句，需要是(raw_)grouped_pitch的元素
            :param start: 该句开始的时间
            :return: np.array(notes_list)  格式：[秒，频率]
            """
            notes_list = []  # 格式：[秒，频率]
            time_idx = start // 5 * 5  # 以5ms为单位
            note_idx = 0  # 在当前乐句的初始idx是0
            sentence_len = len(sentence)
            # cur_f = self.pitch2freq(self.grouped_raw_pitch[idx][0][2] - 12)     # 降八度
            while note_idx < sentence_len:
                cur_f = 0.0
                while time_idx < sentence[note_idx][0]:
                    notes_list.append([time_idx / 1000, cur_f])
                    time_idx += 5  # 以 5ms 为间隔
                cur_f = self.pitch2freq(sentence[note_idx][2] - 12)  # 降八度
                while time_idx < sentence[note_idx][0] + sentence[note_idx][1]:
                    notes_list.append([time_idx / 1000, cur_f])
                    time_idx += 5
                note_idx += 1
            return np.array(notes_list)  # 格式：[秒，频率]

        def stretch(self, idx, position):
            """
            将qrc中的歌词的时间戳线性变换以对齐audio的lrc，存放在self.qrc中。
            只处理用idx和position指明的一段歌词
            :param idx: qrc的索引
            :param position: lrc的索引
            :return: None
            """
            qrc_start = self.raw_qrc[idx][0][0]  # 开始时间，单位ms
            qrc_end = self.raw_qrc[idx][0][0] + self.raw_qrc[idx][0][1]
            lrc_start = self.lrc[position][0]
            if position == len(self.lrc) - 1:
                lrc_next_start = int(self.t[-1] * 1000)
            else:
                lrc_next_start = self.lrc[position + 1][0]

            # 制作频率乐谱
            # notes_list = []  # 格式：[秒，频率]
            # time_idx = qrc_start // 5 * 5  # 以5ms为单位
            # note_idx = 0  # 在当前乐句的初始idx是0
            # sentence_len = len(self.grouped_raw_pitch[idx])
            # # cur_f = self.pitch2freq(self.grouped_raw_pitch[idx][0][2] - 12)     # 降八度
            # while note_idx < sentence_len:
            #     cur_f = 0.0
            #     while time_idx < self.grouped_raw_pitch[idx][note_idx][0]:
            #         notes_list.append([time_idx / 1000, cur_f])
            #         time_idx += 5  # 以 5ms 为间隔
            #     cur_f = self.pitch2freq(self.grouped_raw_pitch[idx][note_idx][2] - 12)  # 降八度
            #     while time_idx < self.grouped_raw_pitch[idx][note_idx][0] + self.grouped_raw_pitch[idx][note_idx][1]:
            #         notes_list.append([time_idx / 1000, cur_f])
            #         time_idx += 5
            #     note_idx += 1
            # notes_list = np.array(notes_list)  # 格式：[秒，频率]
            notes_list = self.score2freq(self.grouped_raw_pitch[idx], qrc_start)

            # 开始扫描，通过音频确定lrc一段歌词的结尾
            min_distance = float('inf')
            min_pos = lrc_next_start
            cursor = lrc_next_start  # cursor 位置不包含，左闭右开

            # 扫描前plot
            '''
            plt.plot(self.t[lrc_start // 5: cursor // 5], self.f0[lrc_start // 5: cursor // 5], label='f0')
            plt.plot(notes_list[:, 0], notes_list[:, 1], label='score')
            plt.title("raw data before optimizing (with lowering an octave and medfilt = 5)")
            plt.legend()
            plt.show()
            '''

            # 添加一个向左扫描的极限
            left_most = lrc_start + int(self.raw_qrc[idx][0][1] * self.tempo_ratio * 0.85)  # qrc的该段的时长 * 0.85的余量
            while cursor > left_most:  # TODO: 这个循环可以优化
                # 截取 f0 audio
                candidate = self.f0[lrc_start // 5: cursor // 5]

                # plot短时过零率
                crossing_r = librosa.feature.zero_crossing_rate(self.y[int(lrc_start / 5 / len(self.f0) * len(self.y)):
                                                                       int(cursor / 5 / len(self.f0) * len(self.y))])[0]
                x = np.linspace(lrc_start / 1000, cursor / 1000, len(crossing_r))
                plt.plot(x, crossing_r * 100, label='crossing rate')
                plt.plot(self.t[lrc_start // 5: cursor // 5], self.f0[lrc_start // 5: cursor // 5], label='f0')
                plt.legend()
                plt.show()

                distance = self.get_distance(notes_list[:, 1], candidate)
                if distance < min_distance:
                    min_distance = distance
                    min_pos = cursor // 5 * 5 - 5  # cursor 位置不包含
                cursor -= 100
            lrc_end = min_pos  # lrc结束时间，单位ms

            # 画出最短距离的dtw矩阵
            self.plot_alignment(notes_list[:, 1], self.f0[lrc_start // 5: min_pos // 5])

            # 开始拉伸歌词
            stretch_rate = (lrc_end - lrc_start) / (qrc_end - qrc_start)
            # 拉伸总时间戳
            self.qrc[idx][0][0] = lrc_start
            self.qrc[idx][0][1] = lrc_end - lrc_start
            # 拉伸每个字的时间戳
            for i in range(len(self.qrc[idx][1])):
                if i == 0:
                    self.qrc[idx][1][i][0] = lrc_start
                    self.qrc[idx][1][i][1] = int(stretch_rate * self.qrc[idx][1][i][1])
                else:
                    self.qrc[idx][1][i][0] = self.qrc[idx][1][i - 1][0] \
                                             + int((self.raw_qrc[idx][1][i][0] - self.raw_qrc[idx][1][i - 1][0])
                                                   * stretch_rate)
                    self.qrc[idx][1][i][1] = int(stretch_rate * self.qrc[idx][1][i][1])

            # 开始拉伸乐谱
            stretch_rate = (lrc_end - lrc_start) / \
                           (self.grouped_raw_pitch[idx][-1][0] + self.grouped_raw_pitch[idx][-1][1] -
                            self.grouped_raw_pitch[idx][0][0])
            for i in range(len(self.grouped_pitch[idx])):
                if i == 0:
                    self.grouped_pitch[idx][i][0] = lrc_start
                    self.grouped_pitch[idx][i][1] = int(stretch_rate * self.grouped_pitch[idx][i][1])
                else:
                    self.grouped_pitch[idx][i][0] = self.grouped_pitch[idx][i - 1][0] \
                                                    + int((self.grouped_raw_pitch[idx][i][0]
                                                           - self.grouped_raw_pitch[idx][i - 1][0]) * stretch_rate)
                    self.grouped_pitch[idx][i][1] = int(stretch_rate * self.grouped_pitch[idx][i][1])

            # 拉伸后plot
            '''
            notes_list_stretched = self.score2freq(self.grouped_pitch[idx], self.qrc[idx][0][0])
            plt.plot(self.t[lrc_start // 5: cursor // 5], self.f0[lrc_start // 5: cursor // 5], label='f0')
            plt.plot(notes_list_stretched[:, 0], notes_list_stretched[:, 1], label='score_stretched')
            plt.title("data after stretching (lower 1 octave and medfilt = 5)")
            plt.legend()
            plt.show()
            '''

        def save_qrc(self):
            """
            写入文件格式：一行为一句话，每句话开头总时间戳[开始，持续时间]，
                       然后跟上若干(开始，持续时间)为每个字的时间戳
            """
            with open(self.base_dir + "/processed_data/qrc/{}.txt".format(self.number), 'w', encoding='utf-8') as f:
                for sentence in self.qrc:
                    f.write("[{},{}]".format(sentence[0][0], sentence[0][1]))
                    for i in range(len(sentence[1])):
                        f.write("{}({},{})".format(sentence[2][i], sentence[1][i][0], sentence[1][i][1]))
                    f.write("\n")

        def save_pitch(self):
            """
            写入文件格式：一行为一句话，每句话中的每个音符为(开始，持续时间，音高)，
                       每两个音符之间用空格分割，行末没有空格
            """
            with open(self.base_dir + "/processed_data/pitch/{}.txt".format(self.number), 'w', encoding='utf-8') as f:
                for sentence in self.grouped_pitch:
                    for i in range(len(sentence)):
                        if i != 0:
                            f.write(" ")
                        f.write("({},{},{})".format(sentence[i][0], sentence[i][1], sentence[i][2]))
                    f.write("\n")

        def main(self):
            for idx in range(len(self.raw_qrc)):
                print(idx)
                position = self.__idx_qrc2lrc[idx]
                # 拉伸
                self.stretch(idx, position)
            self.save_qrc()
            self.save_pitch()
            print("{} --- Process Successfully".format(self.number))

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
            self.log = [0] * (72898 + 1)

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
        matcher.get_idx_qrc2lrc()
        matcher.pitch_grouping()
        matcher.get_tempo_ratio()
        matcher.load_f0()
        matcher.main()


# %%
if __name__ == "__main__":
    process = LyricsMatch(r"E:/song_spider")
    process.test()
