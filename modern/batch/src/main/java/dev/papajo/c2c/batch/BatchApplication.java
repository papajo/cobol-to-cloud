package dev.papajo.c2c.batch;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/** One Spring Batch job per migrated JCL member; select with --spring.batch.job.name=<JCLNAME>. */
@SpringBootApplication
public class BatchApplication {
    public static void main(String[] args) {
        System.exit(SpringApplication.exit(SpringApplication.run(BatchApplication.class, args)));
    }
}
