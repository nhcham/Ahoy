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
import sys
import unicodedata
import yaml
import unicodedata2

DOWNLOAD_PATH = '_downloads'
CLIP_HUFFMAN_TABLES = 512
USE_PREFIXES = True
ESCAPE = chr(0x1b)
SPACE = chr(0x20)

wrote_example_sentences = 0
original_bit_length_per_char = None
had_important_defined = True
    
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
huffman_key_label[-1] = 'ESCP'

def huffman_keys(ci1, ci2, word_offset, extra_slots, alphabet_size, prefixes, alphabet):
    result = list()
    
    ## add position-dependent bigram prefix keys
    #if word_offset >= 0 and word_offset < extra_slots and ci1 in prefixes and ci2 in prefixes:
        #result.append([ci1, ci2, word_offset])
        
    # add position-independent bigram prefix keys
    global had_important_defined
    if had_important_defined:
        if ci1 in prefixes and ci2 in prefixes:
            result.append([ci1, ci2, -1])
        
    ## add position-dependent monogram prefix keys
    #if word_offset >= 0 and word_offset < extra_slots and ci1 in prefixes:
        #result.append([ci1, -1, word_offset])
        
    # add position-independent monogram prefix keys
    if ci1 in prefixes:
        result.append([ci1, -1, -1])
    
    # add word offset keys
    if word_offset >= 0 and word_offset < extra_slots:
        result.append([-1, -1, word_offset])

    # add default key
    result.append([-1, -1, -1])
    
    encoded_result = list()
    for item in result:
        _ci1 = item[0]
        _ci2 = item[1]
        _word_offset = item[2]
        
        if _ci1 < 0:
            _ci1 = alphabet_size
        if _ci2 < 0:
            _ci2 = alphabet_size
        if _word_offset < 0:
            _word_offset = extra_slots
            
        value = (_word_offset * (alphabet_size + 1) + _ci2) * (alphabet_size + 1) + _ci1
        
        if not value in huffman_key_label:
            label = "%s/%s%s" % (_word_offset if _word_offset < extra_slots else '-',
                                 alphabet[_ci2] if _ci2 < alphabet_size else '-', 
                                 alphabet[_ci1] if _ci1 < alphabet_size else '-')
            huffman_key_label[value] = label
        
        encoded_result.append(value)
    
    return encoded_result

def build(lang, languages, extra_slots):
    def iterate_line(line):
        word_offset = 0
        ci1 = -1
        ci2 = -1
        for c in line:
            if (c not in alphabet_lookup) or (c == ESCAPE):
                continue
            ci = alphabet_lookup[c]
            
            # pick first best key
            yield (c, ci, ci1, ci2, word_offset)
                
            ci2 = ci1
            ci1 = ci
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
        for (c, ci, ci1, ci2, word_offset) in iterate_line(line):
            escape_char = None
            if ci > escape_index:
                # this is not one of the most important characters, insert an escape
                # instead and add this character to the escaped characters table
                escape_char = c
                c = ESCAPE
                ci = alphabet_lookup[c]
                
            t = (ci1, ci2, word_offset)
            if t not in huffman_keys_cache:
                huffman_keys_cache[t] = huffman_keys(ci1, ci2, word_offset, extra_slots, len(alphabet_lookup), prefixes, alphabet)

            # use favorite (first) key
            use_key = huffman_keys_cache[t][0]

            if not use_key in frequencies:
                frequencies[use_key] = dict()
                for _ in range(0, escape_index + 1):
                    frequencies[use_key][_] = 0
                    
            frequencies[use_key][ci] += 1
            
            if huffman_keys_cache[t][-1] != huffman_keys_cache[t][0]:
                # also fill default Huffman tree if we just didn't do so
                use_key = huffman_keys_cache[t][-1]

                if not use_key in frequencies:
                    frequencies[use_key] = dict()
                    for _ in range(0, escape_index + 1):
                        frequencies[use_key][_] = 0
                        
                frequencies[use_key][ci] += 1
                

            if escape_char != None:
                # we have encountered a rare character, put it in a special Huffman tree
                c = escape_char
                ci = alphabet_lookup[c]
                use_key = -1

                if not use_key in frequencies:
                    frequencies[use_key] = dict()
                    for _ in range(escape_index + 1, len(alphabet)):
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
        
        result_bits = 0
        result_line_length = 0
        maximum_reached = False
        
        for (c, ci, ci1, ci2, word_offset) in iterate_line(line):
            escape_char = None
            if ci > escape_index:
                # this is not one of the most important characters, insert an escape
                # instead and add this character to the escaped characters table
                escape_char = c
                c = ESCAPE
                ci = alphabet_lookup[c]

            # pick first best key
            t = (ci1, ci2, word_offset)
            if t not in huffman_keys_cache:
                huffman_keys_cache[t] = huffman_keys(ci1, ci2, word_offset, extra_slots, len(alphabet_lookup), prefixes, alphabet)
                
            use_key = None
            for key in huffman_keys_cache[t]:
                if key in huffman:
                    use_key = key
                    break
            
            if not use_key in huffman_key_histogram:
                huffman_key_histogram[use_key] = 0
            huffman_key_histogram[use_key] += 1
            
            if not maximum_reached:
                if (result_bits + huffman[use_key][ci]['bits_length'] <= 192):
                    result_bits += huffman[use_key][ci]['bits_length']
                    result_line_length += 1
                    #sys.stdout.write("<span class='b%d'>%s</span" % (huffman[use_key][ci]['bits_length'], alphabet[ci]))
                else:
                    #sys.stdout.write("\n")
                    maximum_reached = True
            
        #sys.stdout.write("\n")
        return result_line_length if maximum_reached else None
        
    def handle_sentence_find_updated_freqs(line):
        for (c, ci, ci1, ci2, word_offset) in iterate_line(line):
            escape_char = None
            if ci > escape_index:
                # this is not one of the most important characters, insert an escape
                # instead and add this character to the escaped characters table
                escape_char = c
                c = ESCAPE
                ci = alphabet_lookup[c]

            t = (ci1, ci2, word_offset)
            if t not in huffman_keys_cache:
                huffman_keys_cache[t] = huffman_keys(ci1, ci2, word_offset, extra_slots, len(alphabet_lookup), prefixes, alphabet)
            
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
                for _ in range(0, escape_index + 1):
                    frequencies[use_key][_] = 0
                    
            frequencies[use_key][ci] += 1
            
            if escape_char != None:
                # we have encountered a rare character, put it in a special Huffman tree
                c = escape_char
                ci = alphabet_lookup[c]
                use_key = -1
                
                if not use_key in frequencies:
                    frequencies[use_key] = dict()
                    for _ in range(escape_index + 1, len(alphabet)):
                        frequencies[use_key][_] = 0
                        
                frequencies[use_key][ci] += 1
                
    def handle_sentence_find_lengths(line):
        
        result_bits = 0
        result_line_length = 0
        maximum_reached = False
        
        html_line = ''
        html_line_no_markup = ''
        
        has_funny_spaces = False
        
        for (c, ci, ci1, ci2, word_offset) in iterate_line(line):
            if unicodedata.category(c) in ['Mn', 'Mc', 'Me']:
                has_funny_spaces = True

            escape_char = None
            if ci > escape_index:
                # this is not one of the most important characters, insert an escape
                # instead and add this character to the escaped characters table
                escape_char = c
                c = ESCAPE
                ci = alphabet_lookup[c]

            # pick first best key
            t = (ci1, ci2, word_offset)
            
            if t not in huffman_keys_cache:
                huffman_keys_cache[t] = huffman_keys(ci1, ci2, word_offset, extra_slots, len(alphabet_lookup), prefixes, alphabet)

            use_key = None
            for key in huffman_keys_cache[t]:
                if key in huffman:
                    use_key = key
                    break
            
            if not use_key in huffman_key_histogram:
                huffman_key_histogram[use_key] = 0
            huffman_key_histogram[use_key] += 1
            
            if not maximum_reached:
                if escape_char != None:
                    # we have come across a rare character, see if we can fit both
                    # ESCAPE and the character in here...
                    delta = huffman[use_key][ci]['bits_length']
                    delta += huffman[-1][alphabet_lookup[escape_char]]['bits_length']
                    if (result_bits + delta <= 192):
                        result_bits += delta
                        result_line_length += 1
                        
                        use_bits = float(delta)
                        color = '#ffffff'
                        if use_bits < original_bit_length_per_char:
                            color = mix_colors('#73d216', '#ffffff', use_bits / original_bit_length_per_char)
                        else:
                            color = mix_colors('#ffffff', '#a40000', (use_bits - original_bit_length_per_char) / (16.0 - original_bit_length_per_char))
                        html_line += "<span style='background-color: %s'>%s</span>" % (color, escape_char)
                        html_line_no_markup += escape_char
                        
                        #sys.stdout.write("%s[%d] " % (alphabet[ci], huffman[use_key][ci]['bits_length']))
                        #sys.stdout.write("%s[%d] " % (escape_char, huffman[-1][alphabet_lookup[escape_char]]['bits_length']))
                        #sys.stdout.write("<span class='b%d'>%s</span" % (huffman[use_key][ci]['bits_length'], alphabet[ci]))
                    else:
                        #sys.stdout.write("\n")
                        maximum_reached = True
                else:
                    if (result_bits + huffman[use_key][ci]['bits_length'] <= 192):
                        result_bits += huffman[use_key][ci]['bits_length']
                        result_line_length += 1
                        use_bits = float(huffman[use_key][ci]['bits_length'])
                        color = '#ffffff'
                        if use_bits < original_bit_length_per_char:
                            color = mix_colors('#73d216', '#ffffff', use_bits / original_bit_length_per_char)
                        else:
                            color = mix_colors('#ffffff', '#a40000', (use_bits - original_bit_length_per_char) / (16.0 - original_bit_length_per_char))
                        html_line += "<span style='background-color: %s'>%s</span>" % (color, alphabet[ci])
                        html_line_no_markup += alphabet[ci]
                        #sys.stdout.write("%s[%d] " % (alphabet[ci], huffman[use_key][ci]['bits_length']))
                        #sys.stdout.write("<span class='b%d'>%s</span>" % (huffman[use_key][ci]['bits_length'], alphabet[ci]))
                    else:
                        #sys.stdout.write("\n")
                        maximum_reached = True
            
        #sys.stdout.write("\n")
        global wrote_example_sentences
        
        if maximum_reached:
            if wrote_example_sentences < 20:
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
        

    def write_char_table():
        fout.write("<h2>Character map</h2>\n")
        
        script_count = dict()
        for c in char_map.keys():
            script = unicodedata2.script(c)
            if not script in script_count:
                script_count[script] = 0
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
        
        for c in sorted(list(char_map.keys()), key = cmp_to_key(comp)):
            script = unicodedata2.script(c)
            if script != last_script:
                fout.write("<h3>%s</h3>\n" % script)
            last_script = script
                
            ratio = float(char_map[c]) / max_count
            if ratio > 1.0:
                ratio = 1.0
            ratio = ratio ** 0.5
            name = '(unknown)'
            try:
                name = unicodedata.name(c)
            except ValueError:
                pass
            color = mix_colors('#ffffff', '#73d216', ratio)
            font_color = '#000'
            if (char_map[c] < 10):
                font_color = '#aaa'
            fout.write("<div title='%s' class='cb%s' style='color: %s; background-color: %s;'>%s</div>\n" % (name, ' important' if c in safe_alphabet else (' ignored' if c in ignored else ''), font_color, color, c))
        fout.write("\n")
        
    fout = open('html/report-%s.html' % lang, 'w')
    fout.write("<html>\n")
    fout.write("<meta http-equiv='content-type' content='text/html; charset=utf-8'>\n");
    fout.write("<head>\n")
    fout.write("<link rel='stylesheet' type='text/css' href='css/styles.css' />\n");
    fout.write("</head>\n")
    fout.write("<body>\n")
    fout.write("<h1>Language pack for [%s] (%s)</h1>" % (lang, ' / '.join(languages[lang]['names'])))
    
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
    
    if not 'important' in languages[lang]:
        global had_important_defined
        had_important_defined = False
        print("There are no important characters defined, so we're using everything we can find...")
        print("Warning: This will make the language pack much bigger.")
        languages[lang]['important'] = ''.join(sorted(list(char_map.keys())))
        
    ignored = set()
    if 'ignore' in languages[lang]:
        for c in languages[lang]['ignore']:
            ignored.add(c)
    
    safe_alphabet = set()
    safe_alphabet.add(SPACE)
    
    for c in "0123456789":
        safe_alphabet.add(c)
    for c in ".?!,-'/@:+*=&%#$()\"":
        safe_alphabet.add(c)
        
    for x in languages[lang]['important']:
        if type(x) == list:
            for c in range(ord(x[0]), ord(x[1]) + 1):
                safe_alphabet.add(chr(c))
        else:
            for c in x:
                safe_alphabet.add(c)
                
    ignored -= safe_alphabet
    alphabet |= safe_alphabet
    alphabet -= ignored
    
    # [SAFE ALPHABET STARTING WITH SPACE][ESCAPE][REMAINING ALPHABET]
    temp = []
    temp.append(SPACE)
    temp.extend(sorted(list(safe_alphabet - set(SPACE))))
    temp.append(ESCAPE)
    escape_index = len(temp) - 1
    temp.extend(sorted(list(alphabet - set(temp))))
    alphabet = temp
    alphabet_lookup = dict()
    for index, c in enumerate(alphabet):
        alphabet_lookup[c] = index
    
    prefixes = list()
    if USE_PREFIXES:
        prefixes = [alphabet_lookup[_] for _ in alphabet if _ not in [SPACE, ESCAPE] and _ in safe_alphabet]
    
    write_char_table()
        
    #print("Alphabet has %d characters: [%s]" % (len(alphabet), ''.join(alphabet)))
    #print("A total of %d prefixes are defined: [%s]" % (len(prefixes), ''.join([alphabet[_] for _ in prefixes])))
    print("Alphabet has %d characters, %d of which are highly important." % (len(alphabet), len(safe_alphabet)))
    original_bit_length_per_char = math.log(len(alphabet)) / math.log(2)
    print("Uninformed information content is %1.2f bits per character." % (original_bit_length_per_char))
    print("A total of %d prefixes are defined." % (len(prefixes)))
    
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
        
    lengths = list()
    for line in iterate_lines(corpora_path, 1):
        length = handle_sentence_estimate_tree_usage(line)
        if length != None:
            lengths.append(length)
            
    lengths = sorted(lengths)
    print("80%% of all sentences are %d to %d characters long." % (lengths[int((len(lengths) - 1) * 10 / 100)], lengths[int((len(lengths) - 1) * 90 / 100)]))
     
    keys_by_usage = sorted(huffman_key_histogram.keys(), key=lambda x: -huffman_key_histogram[x])
    #for key in keys_by_usage:
        #print("[%4s] %8d" % (huffman_key_label[key], huffman_key_histogram[key]))
        
    keep_keys = set(keys_by_usage[0:CLIP_HUFFMAN_TABLES])
    
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
    
    fout.write("<h2>Example sentences</h2>\n")
    fout.write("<ul>\n")
    
    lengths = list()
    for line in iterate_lines(corpora_path, 1):
        length = handle_sentence_find_lengths(line)
        if length != None:
            lengths.append(length)
                
    fout.write("</ul>\n")
    
    lengths = sorted(lengths)
    print("80%% of all sentences are %d to %d characters long." % (lengths[int((len(lengths) - 1) * 10 / 100)], lengths[int((len(lengths) - 1) * 90 / 100)]))
    
    save_huffman_tables(huffman_tables)
    
    #keys_by_usage = sorted(huffman_key_histogram.keys(), key=lambda x: -huffman_key_histogram[x])
    #for key in keys_by_usage:
        #print("[%4s] %8d" % (huffman_key_label[key], huffman_key_histogram[key]))
        
    fout.write("</body>\n")
    fout.write("</html>\n")
    fout.close()
        
if __name__ == '__main__':
    languages = yaml.load(open('languages.yaml'))

    if len(sys.argv) < 3:
        print("Usage: ./build-language-pack.py [language tag] [word offset slots]")
        exit(1)

    lang = sys.argv[1]
    extra_slots = int(sys.argv[2])
    build(lang, languages, extra_slots)
