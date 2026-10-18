package dev.papajo.c2c.codec;

import java.math.BigDecimal;
import java.math.BigInteger;

/**
 * Signed zoned decimal (PIC S9(n)V9(m) USAGE DISPLAY), EBCDIC overpunch convention as seen after cp037 decoding:
 * last char {/A..I = +0..9, }/J..R = -0..9; a plain digit is treated as positive (unsigned or F-zone).
 */
public final class ZonedDecimal {
    private static final String POS = "{ABCDEFGHI";
    private static final String NEG = "}JKLMNOPQR";

    private ZonedDecimal() {}

    public static BigDecimal decode(String field, int scale) {
        if (field.isEmpty()) throw new IllegalArgumentException("empty field");
        char last = field.charAt(field.length() - 1);
        int digit, sign = 1;
        if (Character.isDigit(last)) {
            digit = last - '0';
        } else if (POS.indexOf(last) >= 0) {
            digit = POS.indexOf(last);
        } else if (NEG.indexOf(last) >= 0) {
            digit = NEG.indexOf(last);
            sign = -1;
        } else {
            throw new IllegalArgumentException("bad overpunch: '" + last + "' in '" + field + "'");
        }
        String head = field.substring(0, field.length() - 1);
        if (!head.chars().allMatch(Character::isDigit)) throw new IllegalArgumentException("non-digit in '" + field + "'");
        BigInteger v = new BigInteger(head + digit);
        return new BigDecimal(sign < 0 ? v.negate() : v, scale);
    }

    /** Encode signed; value must already be at target scale. Zero is encoded as positive ({), like Enterprise COBOL. */
    public static String encode(BigDecimal value, int length) {
        BigInteger u = value.unscaledValue();
        String d = u.abs().toString();
        if (d.length() > length) throw new ArithmeticException("overflow: " + value + " into " + length + " digits");
        d = "0".repeat(length - d.length()) + d;
        int lastDigit = d.charAt(length - 1) - '0';
        char over = (u.signum() < 0 ? NEG : POS).charAt(lastDigit);
        return d.substring(0, length - 1) + over;
    }
}
