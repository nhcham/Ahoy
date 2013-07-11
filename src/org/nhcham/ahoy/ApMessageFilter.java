package org.nhcham.ahoy;

import java.util.zip.CRC32;
import java.util.*;
import java.io.*;
import android.content.*;
import android.content.res.*;
import android.util.*;

public class ApMessageFilter
{
    final static String TAG = "ApMessageFilter";
    public HashMap<Integer, LanguagePack> languagePacks;
    
    public ApMessageFilter(Context context)
    {
        languagePacks = new HashMap<Integer, LanguagePack>();
        try
        {
            BufferedReader r = new BufferedReader(new InputStreamReader(context.getAssets().open("languages.txt")));
            String line;
            while ((line = r.readLine()) != null)
            {
                line = line.trim();
                int spaceOffset = line.indexOf(' ');
                if (spaceOffset < 0)
                    continue;
                int languageId = Integer.parseInt(line.substring(0, spaceOffset), 10);
                int spaceOffset2 = line.indexOf(' ', spaceOffset + 1);
                if (spaceOffset2 < 0)
                    continue;
                String languageTag = line.substring(spaceOffset + 1, spaceOffset2);
                String languageNativeName = line.substring(spaceOffset2 + 1);
                Log.d(TAG, String.format("Now loading [%d] [%s] (%s)...", languageId, languageTag, languageNativeName));
                LanguagePack pack = new LanguagePack(context, languageId, languageTag, languageNativeName);
                languagePacks.put(languageId, pack);
            }
        } catch (IOException e) {
            // TODO: what do we do with this?
        }
    }
    
    public String ssidToMessage(final String s)
    {
        if (s.startsWith("`"))
            return s.substring(1);
        else
            return null;
    }
    
    public String messageToSsid(final String s)
    {
        if (s.length() < 30)
        {
            try
            {
                CRC32 crc = new CRC32();
                crc.update(s.getBytes("US-ASCII"));
                Log.d(TAG, String.format("Checksum = %x", crc.getValue()));
            } catch (UnsupportedEncodingException e) { }
        }
        return "`" + s;
    }
    
    public int[] encodeMessage(final String message)
    {
        Log.d(TAG, String.format("Encoding message: [%s]", message));
        int minimumBitLength = -1;
        int minimumBitLengthLang = -1;
        for (int languageId : languagePacks.keySet())
        {
            LanguagePack pack = languagePacks.get(languageId);
            if (pack.canEncodeMessage(message))
            {
                short bitLength = pack.getEncodedMessageLength(message);
                if (minimumBitLength == -1 || bitLength < minimumBitLength)
                {
                    minimumBitLength = bitLength;
                    minimumBitLengthLang = languageId;
                }
            }
        }
        Log.d(TAG, String.format("Message is probably [%s], length is %3d bits: [%s]", minimumBitLengthLang, minimumBitLength, message));
        int[] result = new int[2];
        result[0] = minimumBitLength;
        result[1] = minimumBitLengthLang;
        return result;
    }
};
