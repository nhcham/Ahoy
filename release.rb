#!/usr/bin/env ruby

require 'fileutils'

commitCount = `git rev-list --count HEAD`.to_i
versionTag = `git describe --dirty`
puts "Version code: #{commitCount}, version name: #{versionTag}"

FileUtils::rm_rf('_release_build') if File::exists?('_release_build')
FileUtils::mkdir('_release_build')

FileUtils::cp_r('src', '_release_build')
FileUtils::cp_r('res', '_release_build')
FileUtils::cp(Dir['*.properties'], '_release_build')
FileUtils::cp('AndroidManifest.xml', '_release_build')
FileUtils::cp('build.xml', '_release_build')

manifest = File::read('_release_build/AndroidManifest.xml')
manifest.sub!(/android:versionCode="[^"]*"/, "android:versionCode=\"#{commitCount}\"")
manifest.sub!(/android:versionName="[^"]*"/, "android:versionName=\"#{versionTag}\"")
File::open('_release_build/AndroidManifest.xml', 'w') { |f| f.write(manifest) }
Dir::chdir('_release_build')
system("ant release")
system("jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore ~/.ssh/nhcham.keystore bin/Ahoy-unsigned.apk nhcham")
system("zipalign -v 4 bin/Ahoy-unsigned.apk bin/Ahoy-#{versionTag}.apk")
Dir::chdir('..')

FileUtils::mv("_release_build/bin/Ahoy-#{versionTag}.apk", ".")
FileUtils::rm_rf('_release_build') 
