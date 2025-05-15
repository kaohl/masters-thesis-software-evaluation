import math

def significand_and_exponent(n, precision):
    e = int(math.log(math.fabs(n), 10))
    s = n / math.pow(10, e)
    if math.fabs(s) >= 1:
        s = round(s, precision)
    else:
        s = round(s*10, precision)
        e = e - 1
    if math.fabs(s) >= 10:
        s = s / 10
        e = e + 1
    return s, e

