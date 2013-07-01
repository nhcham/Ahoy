#!/bin/bash
VERSION_NUMBER=`grep -o 'android:versionName="[^"]*"' AndroidManifest.xml | sed s/android:versionName=//g | sed s/\"//g`
echo $VERSION_NUMBER
ant clean release
jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore ~/.ssh/nhcham.keystore bin/Ahoy-unsigned.apk nhcham
zipalign -v 4 bin/Ahoy-unsigned.apk bin/Ahoy-$VERSION_NUMBER.apk
