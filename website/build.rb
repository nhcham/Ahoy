#!/usr/bin/env ruby1.9.1

require 'fileutils'
require 'yaml'

puts "Building website..."
FileUtils::rm_rf('out') if File::exists?('out')
FileUtils::mkdir('out')
FileUtils::cp_r('src/template/include', 'out/')

template = File::read('src/template/template.html')

menu = []
menu.push(['Ahoy!', 'index.html'])
menu.push(['Try it out', 'try.html'])
menu.push(['Download', 'download.html'])
menu.push(['Questions and answers', 'faq.html'])
menu.push(['Languages', 'languages.html'])
menu.push(['Contribute', 'contribute.html'])
# menu.push(['Technical details', 'documentation.html'])

languages = YAML::load(open('../languages/languages.yaml'))

lang_menu = "<ul id='submenu'>\n"
languages.keys.sort.each do |tag|
    lang_menu += "<li><a title='#{languages[tag]['names'].first}' href='lang-#{tag}.html'>#{languages[tag]['native']}</a></li>\n"
end
lang_menu += "</ul>\n"

lang_rows = ""
languages.keys.sort.each do |tag|
    row = ''
    
    row += "<td>#{tag}</td>"
    row += "<td><a href='lang-#{tag}.html'>#{languages[tag]['native']}</a></td>"
    row += "<td>#{languages[tag]['names'].first}</td>"
    if languages[tag]['status'] == 'published'
        row += "<td style='background-color: #73d216;'>published &ndash; <a href='lang-#{tag}.html'>see details</a></td>"
    elsif languages[tag]['status'] == 'draft'
        row += "<td style='background-color: #b8de32;'>draft &ndash; <a href='lang-#{tag}.html'>confirmation required</a></td>"
#             cell.html("draft &ndash; <a href='lang-" + pack.languageTag + ".html'>confirmation required</a>");
#             cell.css('background-color', '#b8de32');
    elsif languages[tag]['status'] == 'sketch'
        row += "<td style='background-color: #fce94f;'>rough draft &ndash; <a href='lang-#{tag}.html'>input required</a></td>"
#             cell.html("rough draft &ndash; <a href='lang-" + pack.languageTag + ".html'>input required</a>");
#             cell.css('background-color', '#fce94f');
    else
        puts("Whoa.")
        exit(1)
    end
    
    length_10 = '&ndash;'
    length_90 = '&ndash;'
    alphabet_length = '&ndash;'
    important_chars = '&ndash;'
    huffman_trees = '&ndash;'
    pack_size = '&ndash;'
    
    stats_path = "../languages/_huffman/ahoy-language-pack-#{tag}-stats.yaml"
    if File::exists?(stats_path)
        stats = YAML::load(open(stats_path))
        length_10 = stats['length_10']
        length_90 = stats['length_90']
        alphabet_length = stats['alphabet']['alphabet_length']
        important_chars = stats['alphabet']['escape_offset'] - stats['alphabet']['prefix_start']
        prefix_chars = stats['alphabet']['prefix_end'] - stats['alphabet']['prefix_start']
        pack_size = sprintf('%1.1f  kB', stats['pack_size'] / 1024.0) if stats.include?('pack_size')
    end
    
    row += "<td style='text-align: right;'>#{alphabet_length}</td>"
    row += "<td style='text-align: right;'>#{important_chars}</td>"
    row += "<td style='text-align: right;'>#{prefix_chars}</td>"
    row += "<td style='text-align: right;'>#{languages[tag]['trees']}</td>"
    row += "<td style='text-align: right;'>#{length_10} &ndash; #{length_90}</td>"
    row += "<td style='text-align: right;'>#{pack_size}</td>"
    
    lang_rows += "<tr>#{row}</tr>\n"
end

languages.keys.sort.each do |tag|
    content = template.dup
    html_path = "../languages/html/report-#{tag}.html"
    
    insert = lang_menu + "\n"
    
    nativeName = languages[tag]['native']
    englishName = languages[tag]['names'].first
    
    insert += "<h2>Language pack for <span style='font-family: sans-serif;'>#{nativeName}</span>"
    if nativeName != englishName
        insert += " (#{englishName})"
    end
    insert += "</h2>\n"
    
    insert += "<div class='box'>\n"
    insert += "<p>\n"
    if languages[tag]['status'] == 'published'
        insert += "<img src='include/dialog-ok.png' style='float: left; margin-right: 0.7em;' />\n"
        insert += "<b>Status: published</b>. This language pack has already been finalized and published.\n"
    elsif languages[tag]['status'] == 'draft'
        insert += "<img src='include/emblem-important.png' style='float: left; margin-right: 0.7em;' />\n"
        insert += "<b>Status: draft</b>. This draft has been created by native speakers. Confirmation from native speakers is required to finalize the draft and publish the language pack.  Are there characters missing? Are rarely used characters marked as important? Do the example sentences look good? If you are a native speaker, please send your feedback to: <a href='mailto:info@nhcham.org'>info@nhcham.org</a>.\n"
    elsif languages[tag]['status'] == 'sketch'
        insert += "<img src='include/emblem-important.png' style='float: left; margin-right: 0.7em;' />\n"
        insert += "<b>Status: rough draft</b>. This draft has been created from example sentences by non-native speakers. Review from native speakers is required to turn this into a draft. Are there characters missing? Are rarely used characters marked as important? Do the example sentences look good? If you are a native speaker, please send your feedback to: <a href='mailto:info@nhcham.org'>info@nhcham.org</a>.\n"
    else
        puts "No state defined for #{tag}."
        exit(1)
    end
    insert += "</p>\n"
    insert += "</div>\n"
    
    character_map_part = ''
    example_sentences_part = ''
    if File::exists?(html_path)
        sub = File::read(html_path)
        character_map_part = sub[0, sub.index('<h3>Example sentences</h3>')]
        example_sentences_part = sub[sub.index('<h3>Example sentences</h3>'), sub.size]
    end
    
    insert += character_map_part
    
    insert += "<h3>Language pack rules</h3>\n"
    insert += "<p>Starting with all characters that appear in the example sentences, declare the following characters as:</p>\n"
    insert += "<ul>\n"
    ['important', 'supplement', 'ignore'].each do |which|
        insert += "<li><b>#{which == 'supplement' ? 'supplementary' : which}:</b>\n"
        if languages[tag].include?(which)
            items = []
            languages[tag][which].each do |item|
                v = item
                if v.class == Array
                    items.push("#{v[0]} &ndash; #{v[1]}")
                else
                    v = item.sub('script:', '') + ' (all)' if item.index('script:') == 0
                    v = item.sub('probable:', '') + ' (probable)' if item.index('probable:') == 0
                    items.push(v)
                end
            end
            insert += items.join(', ')
        else
            insert += "<em>(none)</em>"
        end
        insert += "</li>\n"
    end
    insert += "</ul>\n"
    
    
    stats_path = "../languages/_huffman/ahoy-language-pack-#{tag}-stats.yaml"
    if File::exists?(stats_path)
        stats = YAML::load(open(stats_path))
        if stats.include?('huffman_keys')
            
            insert += "<h3>Used Huffman trees</h3>\n"
            insert += "<ul>\n"
    
            huffman_trees = {}
            huffman_trees['word_offsets'] = []
            huffman_trees['monograms'] = []
            huffman_trees['bigrams'] = []
            stats['huffman_keys'].each_pair do |key, name|
                if key >= stats['alphabet']['huffman_key_word_offsets'] && key < stats['alphabet']['huffman_key_monograms']
                    huffman_trees['word_offsets'].push(name.to_s)
                elsif key >= stats['alphabet']['huffman_key_monograms'] && key < stats['alphabet']['huffman_key_bigrams']
                    huffman_trees['monograms'].push(name.to_s)
                elsif key >= stats['alphabet']['huffman_key_bigrams']
                    huffman_trees['bigrams'].push(name.to_s)
                end
            end
            
            if huffman_trees['word_offsets'].size > 0
                insert += "<li><b>word offsets:</b> <span style='font-family: sans-serif;'>#{huffman_trees['word_offsets'].sort.join(' &nbsp;')}</span></li>\n"
            end
            if huffman_trees['monograms'].size > 0
                insert += "<li><b>monograms:</b> <span style='font-family: sans-serif;'>#{huffman_trees['monograms'].sort.join(' &nbsp;')}</span></li>\n"
            end
            if huffman_trees['bigrams'].size > 0
                insert += "<li><b>bigrams:</b> <span style='font-family: sans-serif;'>#{huffman_trees['bigrams'].sort.join(' &nbsp;')}</span></li>\n"
            end
            insert += "</ul>\n"
        end
    end
    
    insert += example_sentences_part
    
    insert += "<h3>Miscellaneous</h3>\n"
    insert += "<p>Example sentences have been downloaded from <a href='#{languages[tag]['link']}'>#{languages[tag]['link']}</a></p>\n"
    insert += "<p><b>Symbol meanings:</b></p>\n"
    insert += "<div class='cb' style='color: #aaa; background-color: #fff; display: inline-block;'>A</div>&nbsp;&nbsp;&nbsp;&nbsp;The character has appeared less than 10 times in the example sentences.<br />\n"
    insert += "<div class='cb' style='color: #000; background-color: #fff; display: inline-block;'>A</div>&nbsp;&nbsp;&nbsp;&nbsp;The character has appeared at least 10 times, but was seen very rarely.<br />\n"
    insert += "<div class='cb' style='color: #000; background-color: #73d216; display: inline-block;'>A</div>&nbsp;&nbsp;&nbsp;&nbsp;The character has been seen very often.<br />\n"
    insert += "<div class='cb butter' style='color: #000; display: inline-block;'>A</div>&nbsp;&nbsp;&nbsp;&nbsp;The character is included as an important character.<br />\n"
    insert += "<div class='cb butter-dashed' style='color: #000; display: inline-block;'>A</div>&nbsp;&nbsp;&nbsp;&nbsp;The character is included as an important character, but there's already a lowercase variant of it.<br />\n"
    insert += "<div class='cb aluminium' style='color: #000; display: inline-block;'>A</div>&nbsp;&nbsp;&nbsp;&nbsp;The character is included as a supplementary character.<br />\n"
    insert += "<div class='cb strike' style='color: #000; display: inline-block;'>A</div>&nbsp;&nbsp;&nbsp;&nbsp;The character is excluded from the language pack.<br />\n"
    insert += "<p>Hint: Hover over a character to see its unicode name.</p>\n"
    content.sub!('#{CONTENT}', insert)

    menu_html = menu.map do |x|
        "<li><a href='#{x[1]}'>#{x[0]}</a></li>"
    end
    content.sub!('#{MENU}', menu_html.join("\n"))
    
    open("out/lang-#{tag}.html", 'w') do |f|
        f.write(content)
    end
end


menu.each do |item|
    caption = item[0]
    page = item[1]
    
    content = template.dup
    content.sub!('#{CONTENT}', File::read("src/pages/#{page}"))
    
    scripts = ''
    if page == 'try.html'
        scripts = "<script src='include/ahoy.js' type='text/javascript'></script>"
    end
    content.sub!('#{SCRIPTS_HERE}', scripts)
    content.sub!('#{LANG_ROWS_HERE}', lang_rows);
    
    menu_html = menu.map do |x|
        "<li#{(item[1] == x[1]) ? ' class=\'menu_current\'' : ''}><a href='#{x[1]}'>#{x[0]}</a></li>"
    end
    content.sub!('#{MENU}', menu_html.join("\n"))
    
    open("out/#{page}", 'w') do |f|
        f.write(content)
    end
end

system("cd out; python -m SimpleHTTPServer")
