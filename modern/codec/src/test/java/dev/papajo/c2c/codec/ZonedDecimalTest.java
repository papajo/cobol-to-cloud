package dev.papajo.c2c.codec;

import static org.junit.jupiter.api.Assertions.*;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class ZonedDecimalTest {
    @Test
    void acctBalanceFromCardDemoData() {
        // ACCT-CURR-BAL PIC S9(10)V99 from acctdata record 1: "00000001940{" = +194.00
        assertEquals(new BigDecimal("194.00"), ZonedDecimal.decode("00000001940{", 2));
    }

    @Test
    void negativeOverpunch() {
        assertEquals(new BigDecimal("-12.35"), ZonedDecimal.decode("0000123N", 2));
        assertEquals(new BigDecimal("-0.10"), ZonedDecimal.decode("00001}", 2));
    }

    @Test
    void discGroupRate() {
        // DIS-INT-RATE PIC S9(04)V99: "00150{" = 15.00
        assertEquals(new BigDecimal("15.00"), ZonedDecimal.decode("00150{", 2));
    }

    @Test
    void roundTrips() {
        for (String s : new String[]{"-98765.43", "0.00", "1.01", "-0.09"}) {
            BigDecimal v = new BigDecimal(s);
            assertEquals(v, ZonedDecimal.decode(ZonedDecimal.encode(v, 12), 2));
        }
        assertEquals("00000001940{", ZonedDecimal.encode(new BigDecimal("194.00"), 12));
    }

    @Test
    void rejectsGarbage() {
        assertThrows(IllegalArgumentException.class, () -> ZonedDecimal.decode("12 4{", 0));
        assertThrows(IllegalArgumentException.class, () -> ZonedDecimal.decode("123#", 0));
        assertThrows(ArithmeticException.class, () -> ZonedDecimal.encode(new BigDecimal("12345"), 4));
    }
}
