# %%
import json

# %%
content = {
    'emm': [1, 2, 3, 4]
}

with open(r"E:\song_spider\scripts\trytrywater\temp.json", 'w') as f:
    json.dump(content, f)

# %%
with open(r"E:\song_spider\scripts\trytrywater\temp.json", 'r') as f:
    load_f = json.load(f)

print(type(load_f['emm']))
# 所以list格式读取后还是list！！！
