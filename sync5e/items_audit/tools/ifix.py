"""Layout repairs for item text whose lists/tables the CSV export squashed together.
Only whitespace/markup is added; the words stay 1:1.

  fix_text(text, old_text=None) -> (new_text, [notes])
"""
import re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tables_manual

JOIN = re.compile(r'(?<=[a-z\)\]%"\'’])\.(?=[A-Z])')
DICE_HDR = re.compile(r'^(\d*d\d+)\s*([A-Z][A-Za-z ,\'’()/-]*?)(?=(?:0?1|00)(?:[-–]\d+)?[A-Z(])')

def _rows_by_keys(body):
    """'01-10Aberrations11-15Beasts...' or '1The target...2The head...' -> [(key, text)] using consecutive keys."""
    rows, pos, nxt = [], 0, None
    keyre = re.compile(r'(\d{1,3})(?:[-–](\d{1,3}))?')
    m = keyre.match(body)
    if not m: return None
    while m:
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
        if m.group(1) == '00': a = b = 100
        start_text = m.end()
        want = (b + 1) % 100 if b != 100 else None
        # find the next key that starts at b+1 and is followed by a capital/quote/paren
        nm = None
        if want is not None:
            pats = [str(want).zfill(2), str(want)] if want < 10 else [str(want)]
            if want == 0: pats = ['00']
            best = None
            for ptn in pats:
                for mm in re.finditer(re.escape(ptn) + r'(?:[-–](\d{1,3}))?(?=[A-Z("“‘\'])', body[start_text:]):
                    if mm.start() == 0: continue
                    if best is None or mm.start() < best[0]: best = (mm.start(), mm)
                    break
            if best: nm = keyre.match(body, start_text + best[0])
        key = m.group(0)
        txt = body[start_text: nm.start() if nm else len(body)].strip()
        if not txt: return None
        rows.append((key, txt))
        m = nm
    return rows if len(rows) >= 2 else None

def fix_dice_table(para):
    m = DICE_HDR.match(para)
    if not m: return None
    die, head = m.group(1), m.group(2).strip()
    if re.search(r'[a-z)][A-Z]', head): return None      # more than two columns squashed together: can't split safely
    body = para[m.end():]
    # a trailing sentence after the table (e.g. weapon property text) stays outside it
    rows = _rows_by_keys(body)
    if not rows: return None
    # sanity: keys must cover the die (last key ends at the die size, or 00/100 for d100)
    size = int(die.split('d')[1])
    last = rows[-1][0]
    end = int(re.split(r'[-–]', last)[-1]); end = 100 if end == 0 else end
    if end != size: return None
    out = f'| {die} | {head} |\n|---|---|\n' + '\n'.join(f'| {k} | {t.replace("|", "/")} |' for k, t in rows)
    return out

def fix_list(para):
    parts = [p.strip() for p in JOIN.split(para)]
    if len(parts) < 3: return None
    parts = [p if p.endswith(('.', '!', '?', ':', ')')) else p + '.' for p in parts[:-1]] + [parts[-1]]
    return '\n'.join('- ' + p for p in parts)

def _cells(line): return [c.strip() for c in line.strip().strip('|').split('|')]
def _split_seq(text, keys):
    # split text at each key in order (case-insensitive); returns pieces after each key, or None
    pos, out, lo = 0, [], text.lower()
    idx = []
    for k in keys:
        i = lo.find(k.lower(), pos)
        if i < 0: return None
        idx.append(i); pos = i + len(k)
    return idx
def rebuild_from_old(para, old_table):
    lines = [l for l in old_table.strip().split('\n') if l.strip()]
    if len(lines) < 3: return None
    head = _cells(lines[0]); rows = [_cells(l) for l in lines[2:]]
    if any(len(r) != len(head) for r in rows): return None
    keys = [r[0] for r in rows]
    idx = _split_seq(para, keys)
    if idx is None: return None
    htxt = para[:idx[0]]
    hidx = _split_seq(htxt, head)
    if hidx is None or hidx[0] != 0: return None
    H = [htxt[hidx[i]:(hidx[i + 1] if i + 1 < len(hidx) else len(htxt))].strip() for i in range(len(head))]
    out = []
    for i, r in enumerate(rows):
        seg = para[idx[i]:(idx[i + 1] if i + 1 < len(idx) else len(para))]
        if len(head) == 2:
            cells = [seg[:len(r[0])], seg[len(r[0]):]]
        else:
            cidx = _split_seq(seg, r)
            if cidx is None or cidx[0] != 0: return None
            cells = [seg[cidx[j]:(cidx[j + 1] if j + 1 < len(cidx) else len(seg))] for j in range(len(r))]
        out.append([c.strip().replace('|', '/') for c in cells])
    if any(not c for row in out for c in row): return None
    tail = ''
    last_old, last_new = rows[-1][-1], out[-1][-1]
    if len(last_new) > len(last_old) + 3 and last_new.lower().startswith(last_old.lower()):
        tail = last_new[len(last_old):].strip(); out[-1][-1] = last_new[:len(last_old)]
    return '| ' + ' | '.join(H) + ' |\n|' + '---|' * len(H) + '\n' + '\n'.join('| ' + ' | '.join(row) + ' |' for row in out) + ('\n\n' + tail if tail else '')

def table_blocks(t):
    return re.findall(r'(?:^\|.*\|[ \t]*\n?)+', t or '', re.M)

def fix_text(text, old_text=None):
    if not text: return text, []
    notes, out = [], []
    old_tables = table_blocks(old_text) if old_text else []
    for para in text.split('\n\n'):
        joins = len(re.findall(r'[a-z\)\.%][A-Z0-9][a-z]', para)) + len(re.findall(r'\d[A-Z][a-z]', para))
        if joins < 3 or para.lstrip().startswith(('|', '- ')):
            out.append(para); continue
        mt = tables_manual.rebuild(para)
        if mt:
            out.append(mt); notes.append('flattened table rebuilt by hand'); continue
        t = fix_dice_table(para)
        if t:
            out.append(t); notes.append('dice table rebuilt'); continue
        if old_tables and re.match(r'^(\d*d\d+)?[A-Z][a-z]+[A-Z]', para):
            rb = next((rebuild_from_old(para, ot) for ot in old_tables if rebuild_from_old(para, ot)), None)
            if rb:
                out.append(rb); notes.append("flattened table rebuilt with the sheet's rows and columns"); continue
        if re.match(r'^(\d*d\d+)', para) or re.match(r'^[A-Z][a-z]+(?: [A-Z]?[a-z]+)?[A-Z][a-z]+(?: [A-Za-z]+)?[A-Z]', para):
            out.append(para); notes.append('flattened table left as in the CSV'); continue
        l = fix_list(para)
        if l:
            out.append(l); notes.append('list split into items'); continue
        out.append(para)
    # sentences the export glued together ("higher.When") get their space back
    res = []
    out = [re.sub(r'\s*\[[−-]\]\s*', '. ', o).replace('.. ', '. ') if '[−]' in o or '[-]' in o else o for o in out]
    for para in out:
        if para.lstrip().startswith('|'): res.append(para); continue
        new = re.sub(r'(?<=[a-z\)])\.(?=[A-Z][a-z])', '. ', para)
        if new != para: notes.append('missing space added')
        res.append(new)
    return '\n\n'.join(res), notes
