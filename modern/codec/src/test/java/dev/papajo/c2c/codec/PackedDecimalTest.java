package dev.papajo.c2c.codec;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class PackedDecimalTest {
    @Test
    void decodesPositiveWithScale() {
        // PIC S9(5)V99 COMP-3: 7 digits + sign nibble = 4 bytes → 12 34 56 7C
        assertEquals(new BigDecimal("12345.67"),
                PackedDecimal.decode(new byte[]{0x12, 0x34, 0x56, 0x7C}, 2));
    }

    @Test
    void decodesNegative() {
        assertEquals(new BigDecimal("-0.05"),
                PackedDecimal.decode(new byte[]{0x00, 0x00, 0x00, 0x5D}, 2));
    }

    @Test
    void unsignedFIsPositive() {
        assertEquals(new BigDecimal("42"), PackedDecimal.decode(new byte[]{0x04, 0x2F}, 0));
    }

    @Test
    void roundTrips() {
        BigDecimal v = new BigDecimal("-98765.43");
        assertEquals(v, PackedDecimal.decode(PackedDecimal.encode(v, 4), 2));
    }

    @Test
    void overflowFails() {
        assertThrows(ArithmeticException.class, () -> PackedDecimal.encode(new BigDecimal("123456789"), 4));
    }

    @Test
    void badSignFails() {
        assertThrows(IllegalArgumentException.class, () -> PackedDecimal.decode(new byte[]{0x12, 0x33}, 0));
    }
}
