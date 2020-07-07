# %%
import difflib
import csv
import os


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
    """
    class Matcher:
        def __init__(self, number):
            pass

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
        pass
