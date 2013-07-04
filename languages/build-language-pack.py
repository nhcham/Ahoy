#!/usr/bin/env python3

import glob
import heapq
import os
import sys
import yaml

DOWNLOAD_PATH = '_downloads'

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

def huffman_keys(ci1, ci2, word_offset, extra_slots, alphabet_size, prefixes):
    result = list()
    
    # add position-dependent bigram prefix keys
    if word_offset < extra_slots and ci1 in prefixes and ci2 in prefixes:
        result.append([ci1, ci2, word_offset])
        
    # add position-independent bigram prefix keys
    if ci1 in prefixes and ci2 in prefixes:
        result.append([ci1, ci2, -1])
        
    # add position-dependent monogram prefix keys
    if word_offset < extra_slots and ci1 in prefixes:
        result.append([ci1, -1, word_offset])
        
    # add position-independent monogram prefix keys
    if ci1 in prefixes:
        result.append([ci1, -1, -1])
    
    # add word offset keys
    if word_offset < extra_slots:
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
        
        encoded_result.append(value)
    
    return encoded_result

def build(lang, languages, extra_slots):
    print("Building language pack for [%s] (%s)..." % (lang, ' / '.join(languages[lang]['names'])))
    
    alphabet = set()
    for c in " .?!,-'/@:+*=&%#":
        alphabet.add(c)
    for x in languages[lang]['alphabet']:
        if type(x) == list:
            for c in range(ord(x[0]), ord(x[1]) + 1):
                alphabet.add(chr(c))
        else:
            for c in x:
                alphabet.add(c)
    alphabet = sorted(list(alphabet))
    alphabet_lookup = dict()
    for index, c in enumerate(alphabet):
        alphabet_lookup[c] = index
    
    '''
    prefixes = set()
    if 'prefix' in languages[lang]:
        for x in languages[lang]['prefix']:
            if type(x) == list:
                for c in range(ord(x[0]), ord(x[1]) + 1):
                    c = chr(c)
                    if not c in alphabet:
                        raise StandardError("Prefix contains %s which is not alphabet." % c)
                    prefixes.add(alphabet_lookup[c])
            else:
                for c in x:
                    if not c in alphabet:
                        raise StandardError("Prefix contains %s which is not alphabet." % c)
                    prefixes.add(alphabet_lookup[c])
    prefixes = sorted(list(prefixes))
    '''
    prefixes = [alphabet_lookup[_] for _ in alphabet if _ != ' ']
    
    print("Alphabet has %d characters: [%s]" % (len(alphabet), ''.join(alphabet)))
    print("A total of %d prefixes are defined: [%s]" % (len(prefixes), ''.join([alphabet[_] for _ in prefixes])))
    
    corpora_path = download_file(lang, languages[lang]['link'])
    
    print("Using sentences from %s." % corpora_path)
    
    huffman_keys_cache = dict()
    frequencies = dict()
        
    def handle_sentence_find_freqs(line):
        line_offset = 0
        word_offset = 0
        ci1 = -1
        ci2 = -1
        for c in line:
            if not c in alphabet_lookup:
                continue
            ci = alphabet_lookup[c]
            
            # pick first best key
            t = (ci1, ci2, word_offset)
            if t not in huffman_keys_cache:
                huffman_keys_cache[t] = huffman_keys(ci1, ci2, word_offset, extra_slots, len(alphabet_lookup), prefixes)
            use_key = huffman_keys_cache[t][0]

            if not use_key in frequencies:
                frequencies[use_key] = dict()
                for _ in range(len(alphabet_lookup)):
                    frequencies[use_key][_] = 0
                    
            frequencies[use_key][ci] += 1
                
            ci2 = ci1
            ci1 = ci
            line_offset += 1
            word_offset += 1
            if (c == ' '):
                word_offset = 0
                ci1 = -1
                ci2 = -1
                
    with open(corpora_path) as f:
        for line in f:
            line = line.strip()
            line = line[line.index("\t") + 1:]
            handle_sentence_find_freqs(line)
     
    #for key in frequencies.keys():
        #print(key)
        #for ci in sorted(frequencies[key], key=lambda x: -frequencies[key][x]):
            #print("[%s] %8d" % (alphabet[ci], frequencies[key][ci]))
            
    print("Created %d frequency tables." % len(frequencies))
    
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
                    string += str(nodes[p][5])
                p = nodes[p][4]
            codes[c] = dict()
            codes[c]['bits'] = string
            codes[c]['bits_length'] = len(string)
            
        return codes, nodes
    
    huffman = dict()
    huffman_tables = dict()
    for key in frequencies.keys():
        a, b = build_huffman(frequencies[key])
        huffman[key] = a
        huffman_tables[key] = b
        
    def handle_sentence_estimate_tree_usage(line):
        
        result_bits = 0
        result_line_length = 0
        
        line_offset = 0
        word_offset = 0
        ci1 = -1
        ci2 = -1
        for c in line:
            if not c in alphabet_lookup:
                continue
            ci = alphabet_lookup[c]
            
            # pick first best key
            t = (ci1, ci2, word_offset)
            if t not in huffman_keys_cache:
                huffman_keys_cache[t] = huffman_keys(ci1, ci2, word_offset, extra_slots, len(alphabet_lookup), prefixes)
            use_key = huffman_keys_cache[t][0]
            
            if (result_bits + huffman[use_key][ci]['bits_length'] <= 192):
                result_bits += huffman[use_key][ci]['bits_length']
                result_line_length += 1
                #sys.stdout.write("[%s]%s" % (alphabet[ci], huffman[use_key][ci]['bits']))
            else:
                #sys.stdout.write("\n")
                return result_line_length
            
            ci2 = ci1
            ci1 = ci
            line_offset += 1
            word_offset += 1
            if (c == ' '):
                word_offset = 0
                ci1 = -1
                ci2 = -1
        #sys.stdout.write("\n")
        return None
        
    print("Created %d Huffman trees, now determining tree usage." % len(frequencies))
    lengths = list()
    with open(corpora_path) as f:
        for line in f:
            line = line.strip()
            line = line[line.index("\t") + 1:]
            length = handle_sentence_estimate_tree_usage(line)
            if length != None:
                lengths.append(length)
    lengths = sorted(lengths)
    print("80%% of all sentences are %d to %d characters long." % (lengths[int((len(lengths) - 1) * 10 / 100)], lengths[int((len(lengths) - 1) * 90 / 100)]))
     
if __name__ == '__main__':
    languages = yaml.load(open('languages.yaml'))

    if len(sys.argv) < 3:
        print("Usage: ./build-language-pack.py [language tag] [word offset slots]")
        exit(1)

    lang = sys.argv[1]
    extra_slots = int(sys.argv[2])
    build(lang, languages, extra_slots)
