#!/usr/bin/env python3

'''
ftp://ftp.unicode.org/Public/3.0-Update/UnicodeData-3.0.0.html
L Letter
M Mark
N Number
P Punctuation
S Symbol
Z Separator
O Other
'''

import glob
import heapq
import math
import os
import re
import sys
import unicodedata
import yaml
import unicodedata2

DOWNLOAD_PATH = '_downloads'
CLIP_HUFFMAN_TABLES = 300
USE_PREFIXES = True
ESCAPE = chr(0x1b)
SPACE = chr(0x20)

wrote_example_sentences = 0
original_bit_length_per_char = None
    
catnames = dict()
catnames['Lu'] = 'Letter, uppercase'
catnames['Ll'] = 'Letter, lowercase'
catnames['Lt'] = 'Letter, titlecase'
catnames['Lm'] = 'Letter, modifier'
catnames['Lo'] = 'Letter, other'
catnames['Mn'] = 'Mark, nonspacing'
catnames['Mc'] = 'Mark, spacing combining'
catnames['Me'] = 'Mark, enclosing'
catnames['Nd'] = 'Number, decimal digit'
catnames['Nl'] = 'Number, letter'
catnames['No'] = 'Number, other'
catnames['Pc'] = 'Punctuation, connector'
catnames['Pd'] = 'Punctuation, dash'
catnames['Ps'] = 'Punctuation, open'
catnames['Pe'] = 'Punctuation, close'
catnames['Pi'] = 'Punctuation, initial quote'
catnames['Pf'] = 'Punctuation, final quote'
catnames['Po'] = 'Punctuation, other'
catnames['Sm'] = 'Symbol, math'
catnames['Sc'] = 'Symbol, currency'
catnames['Sk'] = 'Symbol, modifier'
catnames['So'] = 'Symbol, other'
catnames['Zs'] = 'Separator, space'
catnames['Zl'] = 'Separator, line'
catnames['Zp'] = 'Separator, paragraph'
catnames['Cc'] = 'Other, control'
catnames['Cf'] = 'Other, format'
catnames['Cs'] = 'Other, surrogate'
catnames['Co'] = 'Other, private use'
catnames['Cn'] = 'Other, not assigned'

def load_scripts():
    regex = re.compile("^([0-9A-F\.]+)\s+;\s+([A-Za-z_]+)\s+#\s+([A-Za-z&]+)\s+")

    groups = dict()

    with open('unicode/Scripts.txt') as f:
        for line in f:
            line = line.strip()
            if len(line) == 0 or line[0] == '#':
                continue
            match = regex.match(line)
            if match == None:
                print(line)
                exit(1)
            
            crange = match.groups()[0]
            script = match.groups()[1]
            category = match.groups()[2]
            if '..' in crange:
                temp = crange.split('..')
                c_start = int(temp[0], 16)
                c_end = int(temp[1], 16)
            else:
                c_start = int(crange, 16)
                c_end = int(crange, 16)
                
            if script not in groups:
                groups[script] = dict()
            if category not in groups[script]:
                groups[script][category] = list()
            groups[script][category].append((c_start, c_end))
            
    return groups

def mix_colors(a, b, f):
    if f < 0.0:
        f = 0.0
    if f > 1.0:
        f = 1.0
    ra = float(int(a[1:3], 16)) / 255.0
    ga = float(int(a[3:5], 16)) / 255.0
    ba = float(int(a[5:7], 16)) / 255.0
    rb = float(int(b[1:3], 16)) / 255.0
    gb = float(int(b[3:5], 16)) / 255.0
    bb = float(int(b[5:7], 16)) / 255.0
    rm = int((ra * (1.0 - f) + rb * f) * 255)
    gm = int((ga * (1.0 - f) + gb * f) * 255)
    bm = int((ba * (1.0 - f) + bb * f) * 255)
    return '#%02x%02x%02x' % (rm, gm, bm)

def download_file(lang, url):
    file_path = os.path.join(DOWNLOAD_PATH, os.path.basename(url))
    if not os.path.exists(file_path):
        # create directory if it doesn't exist
        dirname = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        os.system("cd %s; wget \"%s\"; tar xzf \"%s\"; cd .." % (dirname, url, filename))
    return glob.glob(os.path.join(DOWNLOAD_PATH, '%s*-sentences*' % lang))[0]

huffman_key_label = dict()
huffman_key_label[1] = 'ESCAPE'

def huffman_keys(ci1, ci2, word_offset, extra_slots, alphabet):
    result = list()
    
    # add position-independent bigram prefix keys
    if ci1 in range(alphabet['prefix_start'], alphabet['prefix_end']) and ci2 in range(alphabet['prefix_start'], alphabet['prefix_end']):
        result.append(alphabet['huffman_key_bigrams'] + (ci2 - alphabet['prefix_start']) * (alphabet['prefix_end'] - alphabet['prefix_start']) + (ci1 - alphabet['prefix_start']))
        huffman_key_label[result[-1]] = "%s%s>" % (alphabet['charset'][ci2], alphabet['charset'][ci1])
        
    # add position-independent monogram prefix keys
    if ci1 in range(alphabet['prefix_start'], alphabet['prefix_end']):
        result.append(alphabet['huffman_key_monograms'] + (ci1 - alphabet['prefix_start']))
        huffman_key_label[result[-1]] = "%s>" % alphabet['charset'][ci1]
    
    # add word offset keys
    if word_offset >= 0 and word_offset < extra_slots:
        result.append(alphabet['huffman_key_word_offsets'] + word_offset)
        huffman_key_label[result[-1]] = "#%d" % word_offset

    # add default key
    result.append(alphabet['huffman_key_default'])
    huffman_key_label[result[-1]] = '-'
    
    return result

def build(lang, languages, extra_slots):
    def iterate_line(line):
        word_offset = 0
        ci1 = -1
        ci2 = -1
        for c in line:
            if (c not in alphabet['lookup']) or (c == ESCAPE):
                continue
            ci = alphabet['lookup'][c]
            
            yield(ci, ci1, ci2, word_offset)
                
            ci2 = ci1
            ci1 = ci
            # turn ci1 into an important prefix character if possible
            if ci1 in range(alphabet['prefix_end'], alphabet['escape_offset']):
                ci1 = alphabet['lowercase'][ci1 - alphabet['prefix_end']]
            word_offset += 1
            if (c == SPACE):
                word_offset = 0
                ci1 = -1
                ci2 = -1
        
    def handle_sentence_find_characters(line):
        for c in line:
            if not c in char_map:
                char_map[c] = 0
            char_map[c] += 1
            
    def handle_sentence_find_freqs(line):
        for (ci, ci1, ci2, word_offset) in iterate_line(line):
            #print("[%s] [%s] [%s]" % (alphabet['charset'][ci2], alphabet['charset'][ci1], alphabet['charset'][ci]))
            escape_ci = None
            if ci > alphabet['escape_offset']:
                # this is not one of the most important characters, insert an escape
                # instead and add this character to the escaped characters table
                escape_ci = ci
                ci = alphabet['escape_offset']
                
            t = (ci1, ci2, word_offset)
            if t not in huffman_keys_cache:
                huffman_keys_cache[t] = huffman_keys(ci1, ci2, word_offset, extra_slots, alphabet)

            # use favorite (first) key
            use_key = huffman_keys_cache[t][0]

            if not use_key in frequencies:
                frequencies[use_key] = dict()
                for _ in range(0, escape_offset + 1):
                    frequencies[use_key][_] = 0
                    
            frequencies[use_key][ci] += 1
            
            if huffman_keys_cache[t][-1] != huffman_keys_cache[t][0]:
                # also fill default Huffman tree if we just didn't do so
                use_key = huffman_keys_cache[t][-1]

                if not use_key in frequencies:
                    frequencies[use_key] = dict()
                    for _ in range(0, escape_offset + 1):
                        frequencies[use_key][_] = 0
                        
                frequencies[use_key][ci] += 1

            if escape_ci != None:
                # we have encountered a rare character, put it in a special Huffman tree
                ci = escape_ci
                use_key = alphabet['huffman_key_escape']

                if not use_key in frequencies:
                    frequencies[use_key] = dict()
                    for _ in range(alphabet['escape_offset'] + 1, alphabet['alphabet_length']):
                        frequencies[use_key][_] = 0
                        
                frequencies[use_key][ci] += 1
            
    def iterate_lines(path, half):
        with open(path) as f:
            offset = 0
            for line in f:
                offset = (offset + 1) % 2
                if offset == half:
                    line = line.strip()
                    line = line[line.index("\t") + 1:]
                    yield line

    def build_huffman(freqs):
        # nodes has 6 elements for each entry:
        # - character or nil
        # - count (accumulated or from freqs)
        # - left child or nil
        # - right child or nil
        # - parent node or nil
        # - 0 or 1 or nil (is left or right child of parent node)
        nodes = list()
        heap = []
        for c, count in freqs.items():
            nodes.append([c, count, None, None, None, None])
            heapq.heappush(heap, (count, len(nodes) - 1))
        while len(heap) > 1:
            _a = heapq.heappop(heap)
            a = _a[1]
            nodes[a][4] = len(nodes)
            nodes[a][5] = 0

            _b = heapq.heappop(heap)
            b = _b[1]
            nodes[b][4] = len(nodes)
            nodes[b][5] = 1
        
            nodes.append([None, nodes[a][1] + nodes[b][1], a, b, None, None])
            heapq.heappush(heap, (nodes[a][1] + nodes[b][1], len(nodes) - 1))

        codes = dict()
        for i in range(len(freqs)):
            c = nodes[i][0]
            string = ''
            p = i
            while p != None:
                if nodes[p][5] != None:
                    string = str(nodes[p][5]) + string
                p = nodes[p][4]
            codes[c] = dict()
            codes[c]['bits'] = string
            codes[c]['bits_length'] = len(string)
            
        return codes, nodes
    
    def handle_sentence_estimate_tree_usage(line):
        
        for (ci, ci1, ci2, word_offset) in iterate_line(line):
            escape_ci = None
            if ci > alphabet['escape_offset']:
                # this is not one of the most important characters, insert an escape
                # instead
                # because we just want to determine tree usage, we don't handle the
                # actual escaped character here any further...
                escape_ci = ci
                ci = alphabet['escape_offset']

            # pick first best key
            t = (ci1, ci2, word_offset)
            if t not in huffman_keys_cache:
                huffman_keys_cache[t] = huffman_keys(ci1, ci2, word_offset, extra_slots, alphabet)
                
            use_key = None
            for key in huffman_keys_cache[t]:
                if key in huffman:
                    use_key = key
                    break
            
            if not use_key in huffman_key_histogram:
                huffman_key_histogram[use_key] = 0
            huffman_key_histogram[use_key] += 1
            
    def handle_sentence_find_updated_freqs(line):
        for (ci, ci1, ci2, word_offset) in iterate_line(line):
            escape_ci = None
            if ci > alphabet['escape_offset']:
                # this is not one of the most important characters, insert an escape
                # instead and add this character to the escaped characters table
                escape_ci = ci
                ci = alphabet['escape_offset']

            t = (ci1, ci2, word_offset)
            if t not in huffman_keys_cache:
                huffman_keys_cache[t] = huffman_keys(ci1, ci2, word_offset, extra_slots, alphabet)
            
            use_key = None
            for key in huffman_keys_cache[t]:
                if key in keep_keys:
                    use_key = key
                    break
            if use_key == None:
                # if we couldn't find a matching key, use the default key
                # which is always the last possible key returned
                use_key = huffman_keys_cache[t][-1]

            if not use_key in frequencies:
                frequencies[use_key] = dict()
                for _ in range(0, alphabet['escape_offset'] + 1):
                    frequencies[use_key][_] = 0
                    
            frequencies[use_key][ci] += 1
            
            if escape_ci != None:
                # we have encountered a rare character, put it in a special Huffman tree
                ci = escape_ci
                use_key = alphabet['huffman_key_escape']
                
                if not use_key in frequencies:
                    frequencies[use_key] = dict()
                    for _ in range(alphabet['escape_offset'] + 1, alphabet['alphabet_length']):
                        frequencies[use_key][_] = 0
                        
                frequencies[use_key][ci] += 1
                
    def handle_sentence_find_lengths(line):
        
        result_bits = 0
        result_line_length = 0
        maximum_reached = False
        
        html_line = ""
        html_line_no_markup = ''
        
        has_funny_spaces = False
        
        for (ci, ci1, ci2, word_offset) in iterate_line(line):
            if unicodedata.category(alphabet['charset'][ci]) in ['Mn', 'Mc', 'Me']:
                has_funny_spaces = True

            escape_ci = None
            if ci > alphabet['escape_offset']:
                # this is not one of the most important characters, insert an escape
                # instead and add this character to the escaped characters table
                escape_ci = ci
                ci = alphabet['escape_offset']

            # pick first best key
            t = (ci1, ci2, word_offset)
            
            if t not in huffman_keys_cache:
                huffman_keys_cache[t] = huffman_keys(ci1, ci2, word_offset, extra_slots, alphabet)

            use_key = None
            for key in huffman_keys_cache[t]:
                if key in huffman:
                    use_key = key
                    break
            
            if not use_key in huffman_key_histogram:
                huffman_key_histogram[use_key] = 0
            huffman_key_histogram[use_key] += 1
            
            if escape_ci != None:
                # we have come across a rare character, see if we can fit both
                # ESCAPE and the character in here...
                delta = huffman[use_key][ci]['bits_length']
                delta += huffman[alphabet['huffman_key_escape']][escape_ci]['bits_length']
                
                use_bits = float(delta)
                color = '#ffffff'
                if use_bits < original_bit_length_per_char:
                    color = mix_colors('#73d216', '#ffffff', use_bits / original_bit_length_per_char)
                else:
                    color = mix_colors('#ffffff', '#a40000', (use_bits - original_bit_length_per_char) / (16.0 - original_bit_length_per_char))
                html_line += "<span style='background-color: %s'>%s</span>" % (color, alphabet['charset'][escape_ci])
                html_line_no_markup += alphabet['charset'][escape_ci]
                
                if not maximum_reached and (result_bits + delta <= 192):
                    result_bits += delta
                    result_line_length += 1
                else:
                    if not maximum_reached:
                        html_line += "<span class='toomuch'>"
                        maximum_reached = True
            else:
                
                use_bits = float(huffman[use_key][ci]['bits_length'])
                color = '#ffffff'
                if use_bits < original_bit_length_per_char:
                    color = mix_colors('#73d216', '#ffffff', use_bits / original_bit_length_per_char)
                else:
                    color = mix_colors('#ffffff', '#a40000', (use_bits - original_bit_length_per_char) / (16.0 - original_bit_length_per_char))
                html_line += "<span style='background-color: %s'>%s</span>" % (color, alphabet['charset'][ci])
                html_line_no_markup += alphabet['charset'][ci]
                
                if not maximum_reached and (result_bits + huffman[use_key][ci]['bits_length'] <= 192):
                    result_bits += huffman[use_key][ci]['bits_length']
                    result_line_length += 1
                else:
                    if not maximum_reached:
                        html_line += "<span class='toomuch'>"
                        maximum_reached = True
            
        #sys.stdout.write("\n")
        global wrote_example_sentences
        
        if maximum_reached:
            html_line += "</span>"
            if wrote_example_sentences < 10:
                wrote_example_sentences += 1
                fout.write("<li style='font-family: monospace;'>%s" % html_line)
                if has_funny_spaces:
                    fout.write("<br /><span style='color: #888;'>%s</span>" % html_line_no_markup)
                fout.write("</li>\n")
                
        return result_line_length if maximum_reached else None
    
    def save_huffman_tables(huffman_tables):
        offset_histogram = dict()
        offset_max = None
        for key, table in huffman_tables.items():
            for row_index in range(len(table)):
                row = table[row_index]
                if row[2] != None:
                    for _ in (2, 3):
                        offset = row_index - row[_]
                        if offset_max == None or offset > offset_max:
                            offset_max = offset
                        if not offset in offset_histogram:
                            offset_histogram[offset] = 0
                        offset_histogram[offset] += 1
        # set missing values in offset histogram to 0
        for i in range(offset_max):
            if not i in offset_histogram:
                offset_histogram[i] = 0
        offset_huffman1, offset_huffman2 = build_huffman(offset_histogram)
        
        # determine maximum offset^2 value
        offset_2_max = None
        for row_index in range(offset_max + 1, len(offset_huffman2)):
            row = offset_huffman2[row_index]
            for _ in (2, 3):
                offset = row_index - row[_]
                if offset_2_max == None or offset > offset_2_max:
                    offset_2_max = offset
                    
        offset_byte_count = 1
        if offset_max > 0xff:
            offset_byte_count = 2
        if offset_max > 0xffff:
            offset_byte_count = 3
        if offset_max > 0xffffff:
            offset_byte_count = 4
            
        out_bit_length = 0
        
        for row_index in range(offset_max + 1, len(offset_huffman2)):
            out_bit_length += 2 * offset_byte_count * 8
            
        print("offset huffman table: %1.1f bytes" % (out_bit_length / 8))
        for key, table in huffman_tables.items():
            for row_index in range(len(table)):
                row = table[row_index]
                if row[2] != None:
                    for _ in (2, 3):
                        offset = row_index - row[_]
                        out_bit_length += offset_huffman1[offset]['bits_length']
        print("total size: %1.1f bytes (%1.1f bytes per Huffman tree)" % ((out_bit_length / 8.0), (out_bit_length / 8.0 / len(huffman_tables))))
        return int(out_bit_length / 8.0)
        

    def write_char_table(alphabet):
        fout.write("<h2>Character map</h2>\n")
        
        script_count = dict()
        for c in (set(alphabet['charset']) | set(char_map.keys())):
            script = unicodedata2.script(c)
            if not script in script_count:
                script_count[script] = 0
            if c in char_map:
                script_count[script] += char_map[c]
            
        max_count = 0
        for c, count in char_map.items():
            if c != SPACE:
                if count > max_count:
                    max_count = count
        last_script = None
        
        def comp(a, b):
            scripta = script_count[unicodedata2.script(a)]
            scriptb = script_count[unicodedata2.script(b)]
            if scripta == scriptb:
                if a < b:
                    return -1
                else:
                    return 1
            else:
                if scripta < scriptb:
                    return 1
                else:
                    return -1
                
        def cmp_to_key(mycmp):
            'Convert a cmp= function into a key= function'
            class K(object):
                def __init__(self, obj, *args):
                    self.obj = obj
                def __lt__(self, other):
                    return mycmp(self.obj, other.obj) < 0
                def __gt__(self, other):
                    return mycmp(self.obj, other.obj) > 0
                def __eq__(self, other):
                    return mycmp(self.obj, other.obj) == 0
                def __le__(self, other):
                    return mycmp(self.obj, other.obj) <= 0  
                def __ge__(self, other):
                    return mycmp(self.obj, other.obj) >= 0
                def __ne__(self, other):
                    return mycmp(self.obj, other.obj) != 0
            return K
        
        for c in sorted(list(set(alphabet['charset']) | set(char_map.keys())), key = cmp_to_key(comp)):
            script = unicodedata2.script(c)
            if script != last_script:
                fout.write("<h3>%s</h3>\n" % script)
            last_script = script
                
            ratio = 0.0
            if c in char_map:
                ratio = float(char_map[c]) / max_count
                if ratio > 1.0:
                    ratio = 1.0
            ratio = ratio ** 0.33
            name = '(unknown)'
            try:
                name = unicodedata.name(c)
            except ValueError:
                pass
            color = mix_colors('#ffffff', '#73d216', ratio)
            font_color = '#000'
            if c not in char_map or (char_map[c] < 10):
                font_color = '#aaa'
            css_class = ''
            if c in alphabet['lookup']:
                ci = alphabet['lookup'][c]
                if ci >= alphabet['prefix_start'] and ci < alphabet['prefix_end']:
                    css_class = 'butter'
                elif ci >= alphabet['prefix_end'] and ci < alphabet['escape_offset']:
                    css_class = 'butter-dashed'
                elif ci > alphabet['escape_offset']:
                    css_class = 'aluminium'
            else:
                css_class = 'strike'
            fout.write("<div title='%s' class='cb %s' style='color: %s; background-color: %s;'>%s</div>\n" % (name, css_class, font_color, color, c))
        fout.write("\n")
        
    def parse_character_set(entries, char_map):
        result = set()
        for x in entries:
            if type(x) == list:
                for c in range(ord(x[0]), ord(x[1]) + 1):
                    result.add(chr(c))
            else:
                if 'script:' in x:
                    # pull characters from script
                    for category, ranges in scripts[x.replace('script:', '')].items():
                        for r in ranges:
                            c_start = r[0]
                            c_end = r[1]
                            for ci in range(c_start, c_end + 1):
                                result.add(chr(ci))
                elif 'probable:' in x:
                    # pull characters from script
                    for category, ranges in scripts[x.replace('probable:', '')].items():
                        for r in ranges:
                            c_start = r[0]
                            c_end = r[1]
                            for ci in range(c_start, c_end + 1):
                                c = chr(ci)
                                if c in char_map and char_map[c] >= 10:
                                    result.add(c)
                else:
                    for c in x:
                        result.add(c)
        return result
        
        
    fout = open('html/report-%s.html' % lang, 'w')
    fout.write("<html>\n")
    fout.write("<meta http-equiv='content-type' content='text/html; charset=utf-8'>\n");
    fout.write("<head>\n")
    fout.write("<link rel='stylesheet' type='text/css' href='css/styles.css' />\n");
    fout.write("</head>\n")
    fout.write("<body>\n")
    fout.write("<h1>Language pack for [%s] (%s)</h1>" % (lang, ' / '.join(languages[lang]['names'])))
    
    scripts = load_scripts()
    
    print("Building language pack for [%s] (%s)..." % (lang, ' / '.join(languages[lang]['names'])))

    corpora_path = download_file(lang, languages[lang]['link'])
    fout.write("<p>Using example sentences downloaded from <a href='%s'>%s</a>.</p>\n" % (languages[lang]['link'], languages[lang]['link']))
    print("Using sentences from %s." % corpora_path)
    
    char_map = dict()
    
    with open(corpora_path) as f:
        for line in f:
            line = line.strip()
            line = line[line.index("\t") + 1:]
            handle_sentence_find_characters(line)
        
    #print(''.join(sorted(list(char_map.keys()))))

    alphabet = set(char_map.keys())
    
    important = parse_character_set(languages[lang]['important'], char_map) if 'important' in languages[lang] else set()
    supplement = parse_character_set(languages[lang]['supplement'], char_map) if 'supplement' in languages[lang] else set()
    ignore = parse_character_set(languages[lang]['ignore'], char_map) if 'ignore' in languages[lang] else set()
    
    important -= set([SPACE])
    supplement -= set([SPACE])
    
    # always add cerain characters so that we can post URLs, e-mail addresses
    # and use hashtags
    for c in "0123456789.?!,-'/@:+*=&%#$()\"":
        important.add(c)
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz":
        supplement.add(c)
    
    alphabet -= ignore
    alphabet |= supplement
    alphabet |= important
    
    # alphabet is a list of characters, thus assigning a character to every number
    # in the range from 0 to len(alphabet) - 1:
    # [SPACE][PREFIXES][IMPORTANT BUT NOT PREFIX][ESCAPE][RARE CHARACTERS]
    #         |         \_prefix_end              \_escape_offset
    #         \_prefix_start
    
    # now construct the alphabet
    temp = []
    
    # append SPACE
    temp.append(SPACE)
    prefix_start = len(temp)
    
    # append important prefix characters
    # Apparently, it may happen that Python's lower() function turns a single character
    # into something for which len() returns 2
    # TODO: Maybe use Unicode.txt lowercase data instead?
    temp.extend(sorted(set([(_.lower() if len(_.lower()) == 1 else _) for _ in important])))
    prefix_end = len(temp)
    
    # append remaining important characters
    temp.extend(sorted([_ for _ in important if _ not in temp]))
    
    # append ESCAPE
    escape_offset = len(temp)
    temp.append(ESCAPE)
    
    # append remaining rare characters
    temp.extend(sorted([_ for _ in (supplement | alphabet) if _ not in temp]))
    alphabet_length = len(temp)
    
    if len(temp) != len(set(temp)):
        print("Oops, there are duplicate characters in the alphabet.")
        exit(1)
    
    alphabet = dict()
    alphabet['charset'] = temp
    alphabet['lookup'] = dict()
    for index, c in enumerate(temp):
        alphabet['lookup'][c] = index
    alphabet['prefix_start'] = prefix_start
    alphabet['prefix_end'] = prefix_end
    alphabet['escape_offset'] = escape_offset
    alphabet['alphabet_length'] = alphabet_length
    alphabet['lowercase'] = list()
    for ci in range(prefix_end, escape_offset):
        lc = ci
        c = temp[ci].lower()
        if c in alphabet['lookup']:
            lc = alphabet['lookup'][c]
        alphabet['lowercase'].append(lc)
        
    alphabet['huffman_key_default'] = 0
    alphabet['huffman_key_escape'] = 1
    alphabet['huffman_key_word_offsets'] = 2
    alphabet['huffman_key_monograms'] = alphabet['huffman_key_word_offsets'] + extra_slots
    alphabet['huffman_key_bigrams'] = alphabet['huffman_key_monograms'] + (alphabet['prefix_end'] - alphabet['prefix_start'])
    
    write_char_table(alphabet)
    
    print("Alphabet has %d total / %d important / %d prefix characters." % 
            (alphabet['alphabet_length'], 
             alphabet['escape_offset'] - alphabet['prefix_start'], 
             alphabet['prefix_end'] - alphabet['prefix_start']))
    original_bit_length_per_char = math.log(alphabet['alphabet_length']) / math.log(2)
    print("Uninformed information content is %1.2f bits per character." % (original_bit_length_per_char))
    
    if '--charset' in sys.argv or 'important' not in languages[lang]:
        fout.write("</body>\n")
        fout.write("</html>\n")
        fout.close()
        exit()
        
    huffman_keys_cache = dict()
    frequencies = dict()
    
    for line in iterate_lines(corpora_path, 0):
        handle_sentence_find_freqs(line)
        
    #for key in frequencies.keys():
        #print(huffman_key_label[key])
        #for ci in sorted(frequencies[key], key=lambda x: -frequencies[key][x]):
            #print("[%s] %8d" % (alphabet[ci], frequencies[key][ci]))
            
    print("Created %d frequency tables." % len(frequencies))
    
    huffman = dict()
    huffman_tables = dict()
    for key in frequencies.keys():
        a, b = build_huffman(frequencies[key])
        huffman[key] = a
        huffman_tables[key] = b
        
    print("Created %d Huffman trees, now determining tree usage." % len(huffman))
    
    huffman_key_histogram = dict()
        
    for line in iterate_lines(corpora_path, 1):
        handle_sentence_estimate_tree_usage(line)
     
    keys_by_usage = sorted(huffman_key_histogram.keys(), key=lambda x: -huffman_key_histogram[x])
    #for key in keys_by_usage:
        #print("[%4s] %8d" % (huffman_key_label[key], huffman_key_histogram[key]))
        
    original_length_10 = None
    original_length_90 = None
    original_file_size = None
        
    #for clip_count in [1000, 700, 500, 300, 200, 100, 50]:
    for clip_count in [None, 1000, 500, 400, 300, 250, 200, 100, 50]:
        keep_keys = set(keys_by_usage)
        if clip_count != None:
            if clip_count >= len(keys_by_usage):
                continue
            keep_keys = set(keys_by_usage[0:clip_count])
        keep_keys.add(alphabet['huffman_key_default'])
        keep_keys.add(alphabet['huffman_key_escape'])
        
        print("Now re-creating frequency tables...")
        frequencies = dict()
            
        for line in iterate_lines(corpora_path, 0):
            handle_sentence_find_updated_freqs(line)
        
        #for key in frequencies.keys():
            #print(key)
            #for ci in sorted(frequencies[key], key=lambda x: -frequencies[key][x]):
                #print("[%s] %8d" % (alphabet[ci], frequencies[key][ci]))
                
        print("Re-created %d frequency tables." % len(frequencies))
        
        huffman = dict()
        huffman_tables = dict()
        for key in frequencies.keys():
            a, b = build_huffman(frequencies[key])
            huffman[key] = a
            huffman_tables[key] = b
            
        print("Re-created %d Huffman trees, now determining message length range." % len(huffman))
            
        huffman_key_histogram = dict()
        
        if clip_count == None:
            fout.write("<h2>Example sentences</h2>\n")
            fout.write("<ul>\n")
        
        lengths = list()
        for line in iterate_lines(corpora_path, 1):
            length = handle_sentence_find_lengths(line)
            if length != None:
                lengths.append(length)
                    
        if clip_count == None:
            fout.write("</ul>\n")
            fout.write("<h2>Language pack performance</h2>\n")
            fout.write("<table>\n")
            fout.write("<tr><th>Huffman trees</th><th colspan='4'>Message length (10% &ndash; 90%)</th><th>Performance</th><th colspan='2'>File size (kB)</th></tr>\n")
            
        lengths = sorted(lengths)
        print("80%% of all sentences are %d to %d characters long." % (lengths[int((len(lengths) - 1) * 10 / 100)], lengths[int((len(lengths) - 1) * 90 / 100)]))
        
        file_size = save_huffman_tables(huffman_tables)
        length_10 = lengths[int((len(lengths) - 1) * 10 / 100)]
        length_50 = lengths[int((len(lengths) - 1) * 50 / 100)]
        length_90 = lengths[int((len(lengths) - 1) * 90 / 100)]
        if clip_count == None:
            original_length_10 = length_10
            original_length_90 = length_90
            original_file_size = file_size
            
        fout.write("<tr><td>%d</td><td>%d</td><td>%d%%</td><td>%d</td><td>%d%%</td><td>%d%%</td><td>%1.1f</td><td>%d%%</td></tr>\n" %
                   (len(keys_by_usage) if clip_count == None else clip_count,
                    length_10,
                    int(length_10 * 100.0 / original_length_10),
                    length_90,
                    int(length_90 * 100.0 / original_length_90),
                    float(length_50) * 100.0 / (192.0 / original_bit_length_per_char),
                    file_size / 1024.0,
                    int(file_size * 100.0 / original_file_size)))
        fout.flush()
        
        #keys_by_usage = sorted(huffman_key_histogram.keys(), key=lambda x: -huffman_key_histogram[x])
        #for key in keys_by_usage:
            #print("[%4s] %8d" % (huffman_key_label[key], huffman_key_histogram[key]))
        
    fout.write("</table>\n")
        
    fout.write("</body>\n")
    fout.write("</html>\n")
    fout.close()
        
if __name__ == '__main__':
    languages = yaml.load(open('languages.yaml'))

    if len(sys.argv) < 2:
        print("Usage: ./build-language-pack.py [language tag]")
        exit(1)

    lang = sys.argv[1]
    extra_slots = 10
    build(lang, languages, extra_slots)
