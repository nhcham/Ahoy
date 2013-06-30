package org.nhcham.ahoy;

import java.util.zip.CRC32;
import java.io.UnsupportedEncodingException;
import android.util.Log;

public class ApMessageFilter
{
    final static String TAG = "ApMessageFilter";
    
    public static String ssidToMessage(final String s)
    {
//         return s;
        if (s.startsWith("`"))
            return s.substring(1);
        else
            return null;
    }
    
    public static String messageToSsid(final String s)
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
//         return s;
    }
};
