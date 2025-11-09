def clamp(x, lo, hi):
    return lo if x < lo else hi if hi < x else x
    