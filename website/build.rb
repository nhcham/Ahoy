#!/usr/bin/env ruby1.9.1

require 'fileutils'

puts "Building website..."
FileUtils::rm_rf('out') if File::exists?('out')
FileUtils::mkdir('out')
FileUtils::cp_r('src/template/include', 'out/')

template = File::read('src/template/template.html')

menu = []
menu.push(['Ahoy!', 'index.html'])
menu.push(['Try it out', 'try.html'])

menu.each do |item|
    caption = item[0]
    page = item[1]
    
    content = template.dup
    content.sub!('#{CONTENT}', File::read("src/pages/#{page}"))
    
    menu_html = menu.map do |x|
        "<li#{(item[1] == x[1]) ? ' class=\'menu_current\'' : ''}><a href='#{x[1]}'>#{x[0]}</a></li>"
    end
    content.sub!('#{MENU}', menu_html.join("\n"))
    
    open("out/#{page}", 'w') do |f|
        f.write(content)
    end
end

system("cd out; python -m SimpleHTTPServer")
