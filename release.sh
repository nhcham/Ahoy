#!/bin/bash
ant clean release
jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore ~/.ssh/nhcham.keystore bin/Ahoy-unsigned.apk nhcham
zipalign -v 4 bin/Ahoy-unsigned.apk bin/Ahoy-release.apk
