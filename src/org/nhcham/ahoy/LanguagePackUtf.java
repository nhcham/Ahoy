package org.nhcham.ahoy;

import java.util.*;
import java.io.*;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.*;
import android.content.*;
import android.content.res.*;
import android.util.*;

public class LanguagePackUtf implements ILanguagePack
{
    final static String TAG = "LanguagePackUtf";
    
    Context context;
    
    public int languageId;
    public String languageTag;
    public String encoding;
    
    public byte[] languageMarker;
    
    public int extraSlots;
    public int prefixStart;
    public int prefixEnd;
    public int escapeOffset;
    public int alphabetLength;
    public int huffmanKeyDefault;
    public int huffmanKeyEscape;
    public int huffmanKeyWordOffset;
    public int huffmanKeyMonograms;
    public int huffmanKeyBigrams;
    public int huffmanKeyCount;
    
    public int[] alphabet;
    public HashMap<Integer, Integer> alphabetLookup;
    
    public int[] lowercase;
    public int[] huffmanKeys;
    
    public HashMap<Integer, HuffmanTree> huffmanTrees;
    
    public LanguagePackUtf(Context context, final int languageId, final String languageTag, final String languageMarker)
    {
        this.context = context;
        this.languageId = languageId;
        this.languageTag = languageTag;
        this.languageMarker = new byte[languageMarker.length()];
        for (int i = 0; i < languageMarker.length(); i++)
            this.languageMarker[i] = (byte)(languageMarker.charAt(i) == '0' ? 0 : 1);
        this.encoding = languageTag.equals("utf8") ? "UTF-8" : "UTF-16BE";
    }
    
    public short getEncodedMessageLength(String s)
    {
        byte[] result = null;
        try {
//             Log.d(TAG, encoding);
            result = s.getBytes(encoding);
        } catch (UnsupportedEncodingException e) {}
        int length = languageMarker.length + result.length * 8;
        if (length > 32767)
            length = 32767;
        return (short)length;
    }
    
    public void encodeMessage(String s, byte[] result)
    {
        for (int i = 0; i < result.length; i++)
            // TODO: this is slow
            s += " ";
            
        int resultOffset = 0;
        for (int i = 0; i < languageMarker.length; i++)
            result[resultOffset++] = languageMarker[i];
            
        byte[] temp = null;
        try {
            temp = s.getBytes(encoding);
        } catch (UnsupportedEncodingException e) {}
        for (int i = 0; i < temp.length; i++)
        {
            for (int k = 0; k < 8; k++)
            {
                if (resultOffset >= result.length)
                    return;
                result[resultOffset++] = (byte)((temp[i] >> k) & 1);
            }
        }
    }
    
    public boolean canEncodeMessage(String s)
    {
        return true;
    }
    
    public String decodeMessage(final byte[] bits, int offset)
    {
        byte[] temp = new byte[(bits.length - offset) / 8];
        for (int i = 0; i < temp.length; i++)
        {
            temp[i] = 0;
            for (int k = 0; k < 8; k++)
                temp[i] |= bits[offset + i * 8 + k] << k;
        }
        
        ByteBuffer in_buffer = ByteBuffer.wrap(temp);
        CharBuffer out_buffer = null;
        CharsetDecoder decoder = Charset.forName(encoding).newDecoder();
        decoder.onMalformedInput(CodingErrorAction.IGNORE);
        decoder.onUnmappableCharacter(CodingErrorAction.IGNORE);
        try {  
            out_buffer = decoder.decode(in_buffer);
        } catch (CharacterCodingException e) {}
        String result = out_buffer.toString();
        return result.trim();
    }
    
    public String languageTag()
    {
        return languageTag;
    }
};
