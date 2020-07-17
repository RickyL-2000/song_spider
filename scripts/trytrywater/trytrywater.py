# %%
# 插值
import numpy as np

f0[f0 == 0] = np.interp(np.where(f0 == 0)[0], np.where(f0 > 0)[0], f0[f0 > 0])