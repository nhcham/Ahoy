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
    
    public int symbolCount;
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
            short left = numbers[i << 1];
            short right = numbers[(i << 1) + 1];
            downstreamLinks[i << 1] = left;
            downstreamLinks[(i << 1) + 1] = right;
            upstreamLinks[left << 1] = (short)(i + symbolCount);
            upstreamLinks[(left << 1) + 1] = 0;
            upstreamLinks[right << 1] = (short)(i + symbolCount);
            upstreamLinks[(right << 1) + 1] = 1;
        }
    }
    
    public void unsetLinksInfo()
    {
        downstreamLinks = null;
        upstreamLinks = null;
    }
    
    public int encode(final int symbol)
    {
        /*
        encodes a symbol into a bit pattern:
        000001xxxxxxx
        the most significant 1 describes the length of the code,
        the least significant bit represents the path taken from the root node, etc.
        */
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
    
    public int[] decode(final byte[] bits, int offset)
    {
        /*
        decodes bit pattern to symbol and new offset
        returns symbol -1 if incomplete
        */
        int p = upstreamSlots;
        int[] result = new int[2];
        while (p >= symbolCount)
        {
            p = downstreamLinks[((p - symbolCount) << 1) | (int)(bits[offset++])];
            if (offset >= bits.length)
            {
                result[0] = -1;
                result[1] = offset;
                return result;
            }
        }
        result[0] = p + symbolOffset;
        result[1] = offset;
        return result;
    }
    
    public byte getCodeLength(final int symbol)
    {
        return lengths[symbol - symbolOffset];
    }

};
