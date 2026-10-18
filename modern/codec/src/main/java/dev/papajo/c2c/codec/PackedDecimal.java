package dev.papajo.c2c.codec;

import java.math.BigDecimal;
import java.math.BigInteger;

/** COMP-3 (packed decimal): two digits per byte, low nibble of last byte is sign (C/F = +, D = -). */
public final class PackedDecimal {
    private PackedDecimal() {}

    public static BigDecimal decode(byte[] b, int scale) {
        StringBuilder digits = new StringBuilder(b.length * 2);
        for (int i = 0; i < b.length; i++) {
            int hi = (b[i] >> 4) & 0x0F, lo = b[i] & 0x0F;
            digits.append(digit(hi, b, i));
            if (i < b.length - 1) {
                digits.append(digit(lo, b, i));
            } else if (lo != 0x0C && lo != 0x0F && lo != 0x0D) {
                throw new IllegalArgumentException("bad sign nibble: " + Integer.toHexString(lo));
            }
        }
        BigInteger v = new BigInteger(digits.toString());
        if ((b[b.length - 1] & 0x0F) == 0x0D) v = v.negate();
        return new BigDecimal(v, scale);
    }

    /** Encode to {@code length} bytes; value must already have the target scale (no implicit rounding). */
    public static byte[] encode(BigDecimal value, int length) {
        BigInteger u = value.unscaledValue();
        String d = u.abs().toString();
        int nDigits = length * 2 - 1;
        if (d.length() > nDigits) throw new ArithmeticException("overflow: " + value + " into " + length + " bytes");
        d = "0".repeat(nDigits - d.length()) + d;
        byte[] out = new byte[length];
        for (int i = 0; i < length; i++) {
            int hi = d.charAt(i * 2) - '0';
            int lo = (i == length - 1) ? (u.signum() < 0 ? 0x0D : 0x0C) : d.charAt(i * 2 + 1) - '0';
            out[i] = (byte) ((hi << 4) | lo);
        }
        return out;
    }

    private static int digit(int n, byte[] b, int i) {
        if (n > 9) throw new IllegalArgumentException("bad digit nibble at byte " + i);
        return n;
    }
}
