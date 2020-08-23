# %%
import os
import json
import codecs
import time
from pydub import AudioSegment

# %%
def load_pitch():
    """
    载入所有歌曲的乐谱（音高）数据
    :return: all_pitch 元素格式：all_pitch[i] = song_pitch
                               song_pitch[i] = [start_time, last_time, pitch]
    """
    with open(base_dir + '/alldata.json', 'r', encoding='utf-8-sig') as f:
        all_pitch = [[]]    # index从1开始
        print("loading pitch...")
        _ = 0
        for line in f.readlines():
            _ += 1
            if _ % 100 == 0:
                print(_)
            if line[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
                line = line[codecs.BOM_UTF8:]

            json_line = json.loads(line)
            raw_notes = json_line['note']

            song_pitch = []
            try:
                notes_list = raw_notes.split()
                length = len(notes_list) // 3
                for i in range(length):
                    song_pitch.append([int(notes_list[3 * i]), int(notes_list[3 * i + 1]), int(notes_list[3 * i + 2])])
            except:
                song_pitch = None
            all_pitch.append(song_pitch)

    return all_pitch

# %%
def pitch_grouping(all_pitch, all_qrc, all_data_num, threshold=250):
    """
    将所有属于一句歌词的音符group起来
    :param all_pitch: 未group过的音符list
    :param all_qrc: 所有的歌词数据
    :param all_data_num: 总的歌曲数量(72898)
    :param threshold: 用于定位的阈值，默认250ms
    :return: all_grouped_pitch 元素格式：all_grouped_pitch[i] = song_grouped_pitch
                                       song_grouped_pitch[i] = group  # 一个group就是一句乐句
                                       group[i] = [start_time, last_time, pitch]
    """
    # NOTE: 如果有不归属于任何乐句的音高，就归为前一句
    all_grouped_pitch = [[]]
    _ = 0
    print("grouping pitch...")
    for k in range(1, all_data_num):
        _ += 1
        if _ % 100 == 0:
            print(_)
        song_qrc = all_qrc[k]
        song_pitch = all_pitch[k]
        if song_qrc is None or song_pitch is None:
            all_grouped_pitch.append(None)
            continue

        song_grouped_pitch = []
        try:
            pre_end_idx = -1
            for i in range(len(song_qrc)):
                start_time = song_qrc[i][0][0]
                end_time = song_qrc[i][1][-1][0]    # 结束字符的开始时间
                start_idx = pre_end_idx + 1
                end_idx = start_idx + 1

                min_dist = float('inf')
                while start_idx < len(song_pitch) and abs(song_pitch[start_idx][0] - start_time) > threshold:
                    dist = abs(song_pitch[start_idx][0] - start_time)
                    if dist < min_dist:
                        min_dist = dist
                        start_idx += 1
                    else:
                        start_idx -= 1
                        break
                min_dist = float('inf')
                while end_idx < len(song_pitch) and abs(song_pitch[end_idx][0] - end_time) > threshold:
                    dist = abs(song_pitch[end_idx][0] - end_time)
                    if dist < min_dist:
                        min_dist = dist
                        end_idx += 1
                    else:
                        end_idx -= 1
                        break

                # 处理落单start
                if pre_end_idx - start_idx > 1 and len(song_grouped_pitch) > 0:
                    # 如果在当前句和前一句之间有落单的note
                    for idx in range(pre_end_idx + 1, start_idx):
                        song_grouped_pitch[-1].append(song_pitch[idx])
                elif pre_end_idx - start_idx > 1 and len(song_grouped_pitch) == 0:
                    start_idx = 0
                # 处理落单end
                pre_end_idx = end_idx
                song_grouped_pitch.append(
                    [song_pitch[i] for i in range(start_idx, end_idx + 1)]  # FIXME: index问题
                )

            assert len(song_qrc) == len(song_grouped_pitch)
        except:
            song_grouped_pitch = None

        all_grouped_pitch.append(song_grouped_pitch)

    return all_grouped_pitch


# %%
def load_qrc():
    """
    载入所有歌曲的歌词数据
    :return: all_qrc 元素格式：all_qrc[i] = song_qrc
                             song_qrc[i] = [duration, seq, phrase]
                                    duration = [start_time, end_time]   # NOTE: end_time为结束字的结束时间
                                    seq[i] = [start_time, last_time]
                                    phrase = 歌词
    """
    with open(base_dir + '/alldata.json', 'r', encoding='utf-8-sig') as f:
        all_qrc = [None]  # index从1开始
        _ = 0
        print("loading qrc...")
        for line in f.readlines():
            _ += 1
            if _ % 100 == 0:
                print(_)
            if line[:len(codecs.BOM_UTF8)] == codecs.BOM_UTF8:
                line = line[codecs.BOM_UTF8:]

            json_line = json.loads(line)
            raw_qrc = json_line['qrc']
            start = raw_qrc.find("[offset:")
            start = raw_qrc.find("[", start + 1)
            end = raw_qrc.find("/>", start) - 2
            raw_qrc_list = raw_qrc[start: end].split("\n")

            # 每一首歌的
            song_qrc = []
            try:
                for sentence in raw_qrc_list:
                    sentence = sentence.strip()
                    # 总时间戳
                    start = sentence.find("[")
                    end = sentence.find("]")
                    duration = sentence[start + 1: end].split(",")
                    duration = [int(duration[0].strip("[")), int(duration[0].strip("[")) + int(duration[1].strip("]"))]

                    # 时间戳序列
                    seq = []
                    start = sentence.find("(")
                    end = sentence.find(")")
                    while start != -1:
                        node = sentence[start+1: end].split(",")
                        node = [int(node[0].strip("(")), int(node[1].strip(")"))]
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
            except:
                song_qrc = None
            all_qrc.append(song_qrc)

    return all_qrc

# %%
def mkdir(path):
    folder = os.path.exists(path)
    if not folder:
        os.makedirs(path)
    return path

# %%
def song_cut(song_idx, all_qrc, all_grouped_pitch, base_dir, threshold=500):
    song_qrc = all_qrc[song_idx]
    song_pitch = all_grouped_pitch[song_idx]
    if song_qrc is None or song_pitch is None:
        print("{}.mp3 --- loading failed".format(song_idx), end='  ')
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        return
    for i in range(1, 3):
        file_name = r"{}({}).mp3".format(song_idx, i)
        if os.path.exists(base_dir + "/audios/raw_audios/" + file_name):
            # try:
            input_song = AudioSegment.from_mp3(base_dir + "/audios/raw_audios/" + file_name)

            # 创建新目录
            mkdir(base_dir + '/audios/phrases/{}({})'.format(song_idx, i))

            for j in range(len(song_qrc)):
                duration = song_qrc[j][0]
                output_segment = \
                    input_song[max(duration[0] - threshold, 0): min(duration[1] + threshold, len(input_song))]

                # 存音频
                output_segment.export(base_dir + '/audios/phrases/{}({})/{}.mp3'.format(song_idx, i, j), format="mp3")

                # 存歌词和音符
                content = {
                    'duration': [max(duration[0] - threshold, 0), min(duration[1] + threshold, len(input_song))],
                    'qrc': {
                        'seq': song_qrc[j][1],
                        'phrase': song_qrc[j][2]
                    },
                    'pitch': song_pitch[j]
                }
                with open(base_dir + '/audios/phrases/{}({})/{}.json'.format(song_idx, i, j),
                          'w', encoding='utf-8') as f:
                    json.dump(content, f)

            print("{}({}).mp3 --- successfully processed".format(song_idx, i), end='  ')
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            # except:
            #     print("{}({}).mp3 --- processing failed".format(song_idx, i), end='  ')
            #     print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

# %%
def main(all_data_num, start_point=0):
    for song_idx in range(start_point, all_data_num):
        song_cut(song_idx, all_qrc, all_grouped_pitch, base_dir, threshold=500)

# %%
def test():
    song_idx = 2
    song_cut(song_idx, all_qrc, all_grouped_pitch, base_dir, threshold=500)

# %%
base_dir = os.getcwd()
all_data_num = 72898
all_qrc = load_qrc()
all_pitch = load_pitch()
all_grouped_pitch = pitch_grouping(all_pitch, all_qrc, all_data_num, threshold=250)

# %%
test()
# main(all_data_num, start_point=0)
