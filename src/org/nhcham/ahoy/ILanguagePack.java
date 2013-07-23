package org.nhcham.ahoy;

public interface ILanguagePack {
    public short getEncodedMessageLength(String s);
    public void encodeMessage(String s, byte[] result);
    public boolean canEncodeMessage(String s);
    public String decodeMessage(final byte[] bits, int offset);
}
