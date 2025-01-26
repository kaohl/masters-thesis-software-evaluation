import re

param_of_gen_type = re.compile('>\\s+\\w+\\s*,') # 'List<String> x,'
param_of_arr_type = re.compile(']\\s+\\w+\\s*,') # 'int[] x,'
param_of_sim_type = re.compile('\\s*(\\w+)\\s+\\w+\\s*,')  # 'int x,'

replacements = [
    ('&lt;', '<'),
    ('&gt;', '>')
]

def get_plist(params):
    # All patterns assumes that there is a trailing
    # comma in the input string. Append it if the
    # caller missed it.
    params = params.strip()
    if params == '':
        return '';
    if params[-1] != ',':
        params = params + ','
    # Parsing JaCoCo HTML content so replace symbols.
    for p, r in replacements:
        params = params.replace(p, r)
    plist = []
    xs = param_of_arr_type.split(params)
    if len(xs) > 1:
        for ix, x in enumerate(xs):
            if x == '':
                continue
            # Append the target separator on all but the last.
            if ix + 1 < len(xs):
                x = x + "]"
            m = param_of_sim_type.match(x)
            while not m is None:
                plist.append(m.groups()[0])
                x = x[m.span()[1]+1:].strip()
                m = param_of_sim_type.match(x)
            if len(x) > 0:
                ys = param_of_gen_type.split(x)
                if len(ys) > 1:
                    for iy, y in enumerate(ys):
                        if y == '':
                            continue
                        # Append the target separator on all but the last.
                        if iy + 1 < len(ys):
                            y = y + ">"
                        m = param_of_sim_type.match(y)
                        while not m is None:
                            plist.append(m.groups()[0])
                            y = y[m.span()[1]+1:]
                            m = param_of_sim_type.match(y)
                        y = y.strip()
                        if iy + 1 == len(ys) and ix + 1 == len(xs): # Last.
                            y = y[:-1] # Drop trailing comma.
                        if y != "":
                            plist.append(y)
                else:
                    x = x.strip()
                    if ix + 1 == len(xs): # Last.
                        x = x[:-1] # Drop trailing comma.
                    plist.append(x)
    else:
        ys = param_of_gen_type.split(params)
        if len(ys) > 1:
            for iy, y in enumerate(ys):
                #y = y.strip()
                if y == '':
                    continue
                # Append the target separator on all but the last.
                if iy + 1 < len(ys):
                    y = y + ">"
                m = param_of_sim_type.match(y)
                while not m is None:
                    plist.append(m.groups()[0])
                    y = y[m.span()[1]+1:]
                    m = param_of_sim_type.match(y)
                y = y.strip()
                if iy + 1 == len(ys): # Last.
                    y = y[:-1] # Drop trailing comma.
                if y != "":
                    plist.append(y)
        else:
            m = param_of_sim_type.match(params)
            while not m is None:
                plist.append(m.groups()[0])
                params = params[m.span()[1]+1:]
                m      = param_of_sim_type.match(params)
    return ",".join(plist)
