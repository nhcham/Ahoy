package org.nhcham.ahoy;

import java.util.*;
import java.io.*;
import android.content.*;
import android.content.res.*;
import android.util.*;

public class LanguagePack implements ILanguagePack
{
    final static String TAG = "LanguagePack";
    
    Context context;
    
    public int languageId;
    public String languageTag;
    
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
    
    private void expectString(BufferedInputStream stream, final String s, byte[] buffer) throws IOException
    {
        stream.read(buffer, 0, s.length());
        if (!new String(buffer, 0, s.length(), "US-ASCII").equals(s))
            throw new IOException();
    }

    private int readInt(BufferedInputStream stream, byte[] buffer) throws IOException
    {
        stream.read(buffer, 0, 4);
        return ((buffer[0] & 0xff)) |
               ((buffer[1] & 0xff) << 8) |
               ((buffer[2] & 0xff) << 16)|
               ((buffer[3] & 0xff) << 24);
    }

    private short readShort(BufferedInputStream stream, byte[] buffer) throws IOException
    {
        stream.read(buffer, 0, 2);
        return (short)(((buffer[0] & 0xff)) |
                       ((buffer[1] & 0xff) << 8));
    }

    private byte readByte(BufferedInputStream stream, byte[] buffer) throws IOException
    {
        stream.read(buffer, 0, 1);
        return (byte)(buffer[0] & 0xff);
    }

    public LanguagePack(Context context, final int languageId, final String languageTag, final String languageMarker)
    {
        this.context = context;
        this.languageId = languageId;
        this.languageTag = languageTag;
        this.languageMarker = new byte[languageMarker.length()];
        for (int i = 0; i < languageMarker.length(); i++)
            this.languageMarker[i] = (byte)(languageMarker.charAt(i) == '0' ? 0 : 1);
        
        try
        {
            BufferedInputStream stream = new BufferedInputStream(context.getAssets().open(String.format("ahoy-language-pack-%s-summary.alp", languageTag)));
            byte[] buffer = new byte[1024];
            expectString(stream, "AHOY_LANGUAGE_PACK\0", buffer);
            expectString(stream, String.format("%s\0", languageTag), buffer);
            expectString(stream, "V1\0", buffer);
            
            extraSlots = readInt(stream, buffer);
            prefixStart = readInt(stream, buffer);
            prefixEnd = readInt(stream, buffer);
            escapeOffset = readInt(stream, buffer);
            alphabetLength = readInt(stream, buffer);
            huffmanKeyDefault = readInt(stream, buffer);
            huffmanKeyEscape = readInt(stream, buffer);
            huffmanKeyWordOffset = readInt(stream, buffer);
            huffmanKeyMonograms = readInt(stream, buffer);
            huffmanKeyBigrams = readInt(stream, buffer);
            huffmanKeyCount = readInt(stream, buffer);
            
            alphabet = new int[alphabetLength];
            alphabetLookup = new HashMap<Integer, Integer>();

            // read alphabet
            for (int i = 0; i < alphabetLength; i++)
            {
                int codePoint = readInt(stream, buffer);
                alphabet[i] = codePoint;
                alphabetLookup.put(codePoint, i);
            }
            
            // now parse lowercase entries
            lowercase = new int[escapeOffset - prefixEnd];
            
            for (int i = 0; i < escapeOffset - prefixEnd; i++)
                lowercase[i] = readInt(stream, buffer);
            
            // now parse the Huffman keys
            huffmanTrees = new HashMap<Integer, HuffmanTree>();
            huffmanKeys = new int[huffmanKeyCount];
            
            for (int i = 0; i < huffmanKeyCount; i++)
            {
                int huffmanKey = readInt(stream, buffer);
                huffmanKeys[i] = huffmanKey;
                int codePointCount = escapeOffset + 1;
                if (huffmanKey == huffmanKeyEscape)
                    codePointCount = alphabetLength - escapeOffset - 1;
                huffmanTrees.put(huffmanKey, new HuffmanTree(codePointCount, 
                    (huffmanKey == huffmanKeyEscape) ? (escapeOffset + 1) : 0));
            }
            
            for (int i = 0; i < huffmanKeyCount; i++)
            {
                int huffmanKey = huffmanKeys[i];
                
                int codePointCount = escapeOffset + 1;
                if (huffmanKey == huffmanKeyEscape)
                    codePointCount = alphabetLength - escapeOffset - 1;
                    
                byte[] numbers = new byte[codePointCount];
                stream.read(numbers, 0, numbers.length);
                huffmanTrees.get(huffmanKey).setLengthInfo(numbers);
            }
        } catch (IOException e) {
            // TODO: what do we do with this?
            Log.e(TAG, "exception", e);
        }
    }
    
    private void loadLinks()
    {
        try
        {
            BufferedInputStream stream = new BufferedInputStream(context.getAssets().open(String.format("ahoy-language-pack-%s-links.alp", languageTag)));
            for (int i = 0; i < huffmanKeyCount; i++)
            {
                int huffmanKey = huffmanKeys[i];
                
                int count = huffmanTrees.get(huffmanKey).symbolCount - 1;
                    
                short[] numbers = new short[count * 2];
                byte[] buffer = new byte[2];
                for (int k = 0; k < count * 2; k++)
                {
                    stream.read(buffer, 0, 2);
                    numbers[k] = (short)(((buffer[0] & 0xff)) |
                       ((buffer[1] & 0xff) << 8));
                }
                /*
                if (i == huffmanKeyWordOffset)
                {
                    for (int k = 0; k < count; k++)
                    {
                        short left = numbers[k << 1];
                        short right = numbers[(k << 1) + 1];
                        Log.d(TAG, String.format("%d,%d,%d", k + huffmanTrees.get(huffmanKey).symbolCount, left, right));
                    }
                }
                */
                huffmanTrees.get(huffmanKey).setLinksInfo(numbers);
            }
        } catch (IOException e) {
            // TODO: what do we do with this?
            Log.e(TAG, "exception", e);
        }
    }
    
    private void unloadLinks()
    {
        for (int i = 0; i < huffmanKeyCount; i++)
        {
            int huffmanKey = huffmanKeys[i];
            huffmanTrees.get(huffmanKey).unsetLinksInfo();
        }
    }
    
    public short getEncodedMessageLength(String s)
    {
        short bitLength = 0;
        bitLength += languageMarker.length;
        int ci2 = -1;
        int ci1 = -1;
        int wordOffset = 0;
        for (int i = 0; i < s.length(); i++)
        {
            int codePoint = s.codePointAt(i);
            if (alphabetLookup.containsKey(codePoint))
            {
                int huffmanKey = huffmanKeyDefault;
                if (wordOffset >= 0 && wordOffset < extraSlots)
                {
                    int testKey = huffmanKeyWordOffset + wordOffset;
                    if (huffmanTrees.containsKey(testKey))
                        huffmanKey = testKey;
                }
                if (ci1 >= prefixStart && ci1 < prefixEnd)
                {
                    int testKey = huffmanKeyMonograms + (ci1 - prefixStart);
                    if (huffmanTrees.containsKey(testKey))
                        huffmanKey = testKey;
                }
                if (ci1 >= prefixStart && ci1 < prefixEnd && ci2 >= prefixStart && ci2 < prefixEnd)
                {
                    int testKey = huffmanKeyBigrams + (ci2 - prefixStart) * (prefixEnd - prefixStart) + (ci1 - prefixStart);
                    if (huffmanTrees.containsKey(testKey))
                        huffmanKey = testKey;
                }
                
                int ci = alphabetLookup.get(codePoint);
                if (ci < escapeOffset)
                    bitLength += huffmanTrees.get(huffmanKey).getCodeLength(ci);
                else
                    bitLength += huffmanTrees.get(huffmanKey).getCodeLength(escapeOffset) + huffmanTrees.get(huffmanKeyEscape).getCodeLength(ci);
                if (ci == 0)
                {
                    ci2 = -1;
                    ci1 = -1;
                    wordOffset = 0;
                } else {
                    ci2 = ci1;
                    ci1 = ci;
                    if (ci1 >= prefixEnd && ci < escapeOffset)
                        ci1 = lowercase[ci1 - prefixEnd];
                    wordOffset++;
                }
            }
        }
        return bitLength;
    }
    
    public void encodeMessage(String s, byte[] result)
    {
        this.loadLinks();
        for (int i = 0; i < result.length; i++)
            // TODO: this is slow
            s += new String(alphabet, 0, 1);
            
        int ci2 = -1;
        int ci1 = -1;
        int wordOffset = 0;
        int resultOffset = 0;
        
//         String log = new String();
        
        for (int i = 0; i < languageMarker.length; i++)
            result[resultOffset++] = languageMarker[i];
            
        for (int i = 0; i < s.length(); i++)
        {
            int codePoint = s.codePointAt(i);
            if (alphabetLookup.containsKey(codePoint))
            {
                int huffmanKey = huffmanKeyDefault;
                if (wordOffset >= 0 && wordOffset < extraSlots)
                {
                    int testKey = huffmanKeyWordOffset + wordOffset;
                    if (huffmanTrees.containsKey(testKey))
                        huffmanKey = testKey;
                }
                if (ci1 >= prefixStart && ci1 < prefixEnd)
                {
                    int testKey = huffmanKeyMonograms + (ci1 - prefixStart);
                    if (huffmanTrees.containsKey(testKey))
                        huffmanKey = testKey;
                }
                if (ci1 >= prefixStart && ci1 < prefixEnd && ci2 >= prefixStart && ci2 < prefixEnd)
                {
                    int testKey = huffmanKeyBigrams + (ci2 - prefixStart) * (prefixEnd - prefixStart) + (ci1 - prefixStart);
                    if (huffmanTrees.containsKey(testKey))
                        huffmanKey = testKey;
                }
                
                int ci = alphabetLookup.get(codePoint);
                if (ci < escapeOffset)
                {
                    int code = huffmanTrees.get(huffmanKey).encode(ci);
                    while (code >= 2)
                    {
                        result[resultOffset++] = (byte)(code & 1);
//                         log += (code & 1) == 0 ? "0" : "1";
                        if (resultOffset >= result.length)
                        {
                            this.unloadLinks();
//                             Log.d(TAG, log);
                            return;
                        }
                        code >>= 1;
                    }
//                     log += String.format("[%x,%d] ", codePoint, huffmanKey);
                }
                else
                {
                    int code = huffmanTrees.get(huffmanKey).encode(escapeOffset);
                    while (code >= 2)
                    {
                        result[resultOffset++] = (byte)(code & 1);
//                         log += (code & 1) == 0 ? "0" : "1";
                        if (resultOffset >= result.length)
                        {
                            this.unloadLinks();
//                             Log.d(TAG, log);
                            return;
                        }
                        code >>= 1;
                    }
//                     log += String.format("[ESC] ");
                    code = huffmanTrees.get(huffmanKeyEscape).encode(ci);
                    while (code >= 2)
                    {
                        result[resultOffset++] = (byte)(code & 1);
//                         log += (code & 1) == 0 ? "0" : "1";
                        if (resultOffset >= result.length)
                        {
                            this.unloadLinks();
//                             Log.d(TAG, log);
                            return;
                        }
                        code >>= 1;
                    }
//                     log += String.format("[%x] ", codePoint);
                }
                if (ci == 0)
                {
                    ci2 = -1;
                    ci1 = -1;
                    wordOffset = 0;
                } else {
                    ci2 = ci1;
                    ci1 = ci;
                    if (ci1 >= prefixEnd && ci < escapeOffset)
                        ci1 = lowercase[ci1 - prefixEnd];
                    wordOffset++;
                }
            }
        }
        
        this.unloadLinks();
    }
    
    public boolean canEncodeMessage(String s)
    {
        for (int i = 0; i < s.length(); i++)
            if (!alphabetLookup.containsKey(s.codePointAt(i)))
                return false;
        return true;
    }
    
    public String decodeMessage(final byte[] bits, int offset)
    {
        this.loadLinks();
        String result = new String();
        int ci2 = -1;
        int ci1 = -1;
        int wordOffset = 0;
        int lastNonSpaceLength = 0;
        while (true)
        {
            int huffmanKey = huffmanKeyDefault;
            if (wordOffset >= 0 && wordOffset < extraSlots)
            {
                int testKey = huffmanKeyWordOffset + wordOffset;
                if (huffmanTrees.containsKey(testKey))
                    huffmanKey = testKey;
            }
            if (ci1 >= prefixStart && ci1 < prefixEnd)
            {
                int testKey = huffmanKeyMonograms + (ci1 - prefixStart);
                if (huffmanTrees.containsKey(testKey))
                    huffmanKey = testKey;
            }
            if (ci1 >= prefixStart && ci1 < prefixEnd && ci2 >= prefixStart && ci2 < prefixEnd)
            {
                int testKey = huffmanKeyBigrams + (ci2 - prefixStart) * (prefixEnd - prefixStart) + (ci1 - prefixStart);
                if (huffmanTrees.containsKey(testKey))
                    huffmanKey = testKey;
            }
            
            int[] symbol_and_offset = huffmanTrees.get(huffmanKey).decode(bits, offset);
            offset = symbol_and_offset[1];
            int symbol = symbol_and_offset[0];
            if (symbol == -1)
                break;
            int ci = symbol;
            if (ci == escapeOffset)
            {
                symbol_and_offset = huffmanTrees.get(huffmanKeyEscape).decode(bits, offset);
                offset = symbol_and_offset[1];
                symbol = symbol_and_offset[0];
                if (symbol == -1)
                    break;
                ci = symbol;
            }
            // TODO: this is slow
            result += new String(alphabet, ci, 1);
            if (ci != 0)
                lastNonSpaceLength = result.length();
            if (ci == 0)
            {
                ci2 = -1;
                ci1 = -1;
                wordOffset = 0;
            } else {
                ci2 = ci1;
                ci1 = ci;
                if (ci1 >= prefixEnd && ci < escapeOffset)
                    ci1 = lowercase[ci1 - prefixEnd];
                wordOffset++;
            }
        }
        this.unloadLinks();
        // now strip trailing SPACE characters...
        return result.substring(0, lastNonSpaceLength);
    }
};
