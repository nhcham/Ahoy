#!/usr/bin/env python3

import glob
import os
import shutil
import struct
import sys
import yaml
import json

languages = yaml.load(open('languages/languages.yaml'))

max_number = 0
count = 0

os.system("rm assets/*")

seen_ids = set()

with open('assets/languages.txt', 'w') as fout:
    fout.write("1 utf8 10000001\n")
    seen_ids.add(1)
    fout.write("2 utf16 10000010\n")
    seen_ids.add(2)
    for lang in sorted(languages.keys()):
        if 'language_id' in languages[lang]:
            lang_id = languages[lang]['language_id']
            if lang_id >= 128:
                print("Error")
                exit(1)
            if lang_id in seen_ids:
                print("Error")
                exit(1)
            seen_ids.add(lang_id)
            path1 = 'languages/_huffman/ahoy-language-pack-%s-summary.alp' % lang
            path2 = 'languages/_huffman/ahoy-language-pack-%s-links.alp' % lang
            if os.path.exists(path1) and os.path.exists(path2):
                shutil.copy(path1, 'assets')
                shutil.copy(path2, 'assets')
                fout.write("%d %s %s\n" % (lang_id, lang, "{0:b}".format(128 + lang_id)))
            else:
                print("Error")
                
os.chdir('languages/_huffman')

lang_index = 1
for lang in sorted(languages.keys()):
    path = 'languages/_huffman/ahoy-language-pack-%s-summary.alp' % lang
    if os.path.exists(path):
        sys.stdout.write("%d %s %s\n" % (lang_index, lang, languages[lang]['native']))
        lang_index += 1

with open('../../languages.json', 'w') as f:
    f.write(json.dumps(languages, sort_keys = True, 
            indent = 4, separators = (',', ': ')))
    
command = list()
command.append('zip')
command.append('add')
command.append('../../website/src/template/include/ahoy-language-packs.zip')
command.append('../../languages.json')
for path in glob.glob('*-summary.alp'):
    command.append('./' + path)
    
os.execvp(command[0], command[1:])

