package org.nhcham.ahoy;

import java.util.zip.CRC32;
import java.util.*;
import java.io.*;
import android.content.*;
import android.content.res.*;
import android.util.*;

public class HuffmanTree
{
    final static String TAG = "HuffmanTree";
    
    private int symbolCount;
    private int symbolOffset;
    private int downstreamSlots;
    private int upstreamSlots;
    private short[] downstreamLinks;
    private short[] upstreamLinks;
    private byte[] lengths;
    
    public HuffmanTree(int _symbolCount, int _symbolOffset)
    {
        symbolCount = _symbolCount;
        symbolOffset = _symbolOffset;
        downstreamSlots = symbolCount - 1;
        upstreamSlots = symbolCount + symbolCount - 2;
        downstreamLinks = null;
        upstreamLinks = null;
        lengths = null;
    }
    
    public void setLengthInfo(final byte[] numbers)
    {
        lengths = numbers;
    }
    
    public void setLinksInfo(final short[] numbers)
    {
        downstreamLinks = new short[downstreamSlots << 1];
        upstreamLinks = new short[upstreamSlots << 1];
        for (int i = 0; i < symbolCount - 1; i++)
        {
            short left = (short)((symbolCount + i) - numbers[i << 1]);
            short right = (short)((symbolCount + i) - numbers[(i << 1) + 1]);
            downstreamLinks[i << 1] = left;
            downstreamLinks[(i << 1) + 1] = right;
            upstreamLinks[left << 1] = (short)(i + symbolCount);
            upstreamLinks[(left << 1) + 1] = 0;
            upstreamLinks[right << 1] = (short)(i + symbolCount);
            upstreamLinks[(right << 1) + 1] = 1;
        }
    }
    
    public int encode(final int symbol)
    {
        int p = symbol - symbolOffset;
        // assert(0 >= p < symbolCount)
        int length = 0;
        int result = 0;
        while (p < upstreamSlots)
        {
            result <<= 1;
            // upstreamLinks[(p << 1) + 1] must be 0 or 1
            result |= upstreamLinks[(p << 1) + 1];
            length += 1;
            p = upstreamLinks[p << 1];
        }
        // length must not be larger than 31
        result |= 1 << length;
        return result;
    }
    
    public int decode(int code)
    {
        int p = upstreamSlots;
        while (p >= symbolCount)
        {
            p = downstreamLinks[((p - symbolCount) << 1) | (code & 1)];
            code >>= 1;
        }
        return p + symbolOffset;
    }
    
    public byte getCodeLength(final int symbol)
    {
        return lengths[symbol - symbolOffset];
    }

};
