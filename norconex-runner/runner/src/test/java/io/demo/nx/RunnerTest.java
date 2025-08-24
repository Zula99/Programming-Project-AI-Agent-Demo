package io.demo.nx;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import static org.junit.jupiter.api.Assertions.*;

class RunnerTest {
    
    private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();
    private final PrintStream originalOut = System.out;
    
    @BeforeEach
    void setUpStreams() {
        System.setOut(new PrintStream(outContent));
    }
    
    @AfterEach
    void restoreStreams() {
        System.setOut(originalOut);
    }
    
    @Test
    void testMainWithNoArgs() {
        Runner.main(new String[]{});
        assertEquals("OK" + System.lineSeparator(), outContent.toString());
    }
    
    @Test
    void testMainWithArgs() {
        Runner.main(new String[]{"arg1", "arg2"});
        assertEquals("OK" + System.lineSeparator(), outContent.toString());
    }
}