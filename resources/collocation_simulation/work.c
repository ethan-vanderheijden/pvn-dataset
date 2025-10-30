#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <time.h>
#include <unistd.h>

// 3 seconds in milliseconds
#define EPOCH 1200
// jobs for epoch arrive in 4 batches
#define EPOCH_SEGMENTS 4
// each iteration of do_work() will take approximately 3 milliseconds
#define ITERATION_TIME 3

char help[] =
    "Simulates a program that does work and sleeps for a fixed period of time every epoch.\n"
    "Prints average number of carried over iterations per epoch to stdout.\n"
    "Usage: ./work [-e epoch] [-h] <tuning> <utilization_histogram>\n"
    "  -h                       Show this help message and exit.\n"
    "  -e <epoch>               Stop after this many epochs (Default: 0 to run forever).\n"
    "  <tuning>                 Number of iterations to perform in each epoch. Set this such that "
    "each run takes exactly 3ms.\n"
    "  <utilization_histogram>  Path to description of utilization histogram to sample from.\n";

volatile int done = 0;

static void handle_signal(int sig) { done = 1; }

static inline int utilization_to_iterations(int cpu_utilization) {
    return (cpu_utilization * EPOCH) / (EPOCH_SEGMENTS * 100 * ITERATION_TIME);
}

typedef struct {
    int total_weight;
    int* buckets;
    int bucket_size;
} utilization_t;

void do_work(int tuning) {
    for (int i = 0; i < tuning; i++) {
        volatile int is_prime = 1;
        for (int j = 2; j * j <= i; j++) {
            if (i % j == 0) {
                is_prime = 0;
                break;
            }
        }
    }
}

int read_histogram(const char* path, utilization_t* util) {
    memset(util, 0, sizeof(utilization_t));

    FILE* file = fopen(path, "r");
    if (!file) {
        perror("Failed to open utilization histogram file");
        return -1;
    }

    ssize_t read;
    ssize_t len = 0;
    char* line = NULL;
    int bucket_index = 0;
    while ((read = getline(&line, &len, file)) != -1) {
        if (util->buckets == NULL) {
            if (sscanf(line, "bucket_size: %d", &util->bucket_size) != 1) {
                fprintf(stderr, "Failed to read bucket_size from histogram file\n");
                free(line);
                fclose(file);
                return -1;
            }
            if (100 % util->bucket_size != 0) {
                fprintf(stderr, "bucket_size must evenly divide 100\n");
                free(line);
                fclose(file);
                return -1;
            }
            util->buckets = (int*)malloc(sizeof(int) * (100 / util->bucket_size));
            if (!util->buckets) {
                perror("Failed to allocate memory for histogram buckets");
                free(line);
                fclose(file);
                return -1;
            }
        } else {
            if (bucket_index >= 100 / util->bucket_size) {
                fprintf(stderr, "Too many buckets in histogram file\n");
                free(util->buckets);
                free(line);
                fclose(file);
                return -1;
            }

            int weight = atoi(line);
            util->total_weight += weight;
            util->buckets[bucket_index++] = weight;
        }
    }

    free(line);
    fclose(file);
    return 0;
}

int random_range(int min, int max) {
    if (min >= max) {
        return min;
    }
    return min + rand() / (RAND_MAX / (max - min + 1) + 1);
}

int sample_utilization(utilization_t* util) {
    int r = random_range(1, util->total_weight);
    int cumulative = 0;
    for (int i = 0; i < 100 / util->bucket_size; i++) {
        cumulative += util->buckets[i];
        if (r <= cumulative) {
            return i * util->bucket_size + (util->bucket_size + 1) / 2;
        }
    }
    return 100;
}

int main(int argc, char* argv[]) {
    int max_epochs = 0;
    int opt;
    while ((opt = getopt(argc, argv, "he:")) != -1) {
        switch (opt) {
            case 'e':
                max_epochs = atoi(optarg);
                break;
            default:
                printf("%s", help);
                return opt != 'h';
        }
    }

    if (argc - optind != 2) {
        printf("%s", help);
        return 1;
    }

    int rand_seed;
    if (getrandom(&rand_seed, sizeof(rand_seed), 0) != sizeof(rand_seed)) {
        perror("Failed to get random seed");
        return 1;
    }
    srand(rand_seed);

    utilization_t util;
    if (read_histogram(argv[optind + 1], &util) != 0) {
        return 1;
    }

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    int tuning = atoi(argv[optind]);
    int iterations = 0;
    int epoch = 0;

    unsigned int carried_over_epochs = 0;
    unsigned long long total_carried_over = 0;

outer:
    while (!done && (max_epochs == 0 || epoch < max_epochs)) {
        int cpu_utilization = sample_utilization(&util);
        printf("Epoch %d: utilization %d\n", epoch + 1, cpu_utilization);

        for (int i = 0; i < EPOCH_SEGMENTS; i++) {
            if (done) {
                break outer;
            }

            int new_iterations = utilization_to_iterations(cpu_utilization);
            printf("  Segment %d: adding %d iterations (total %d)\n", i + 1, new_iterations,
                   iterations + new_iterations);
            iterations += new_iterations;

            struct timespec start;
            clock_gettime(CLOCK_MONOTONIC, &start);

            struct timespec cur_time;
            unsigned long long elapsed_ns;
            for (; iterations > 0; iterations--) {
                if (done) {
                    break outer;
                }

                do_work(tuning);
                clock_gettime(CLOCK_MONOTONIC, &cur_time);
                elapsed_ns = (cur_time.tv_sec - start.tv_sec) * 1000000000ULL +
                             (cur_time.tv_nsec - start.tv_nsec);
                if (elapsed_ns >= (EPOCH / EPOCH_SEGMENTS) * 1000000ULL) {
                    break;
                }
            }

            if (iterations == 0) {
                printf("  Finished segment %d early, sleeping...\n", i + 1);
                unsigned long long sleep_ns = (EPOCH / EPOCH_SEGMENTS) * 1000000ULL - elapsed_ns;
                struct timespec sleep_time;
                sleep_time.tv_sec = sleep_ns / 1000000000ULL;
                sleep_time.tv_nsec = sleep_ns % 1000000000ULL;
                nanosleep(&sleep_time, NULL);
            } else {
                printf("  Segment %d: leftover iterations %d\n", i + 1, iterations);
            }
        }

        epoch++;
        if (iterations > 0) {
            carried_over_epochs++;
            total_carried_over += iterations;
        }
    }

    printf("Carry over frequency: %.2f%%, average carry over: %.2f\n",
           (carried_over_epochs * 100.0) / epoch,
           carried_over_epochs ? (total_carried_over * 1.0) / carried_over_epochs : 0.0);
    return 0;
}
