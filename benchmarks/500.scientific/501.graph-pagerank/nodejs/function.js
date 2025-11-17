import { performance } from "perf_hooks";
import { BarabasiAlbertGenerator } from "graphology-generators/classic";
import pagerank from "graphology-metrics/centrality/pagerank";

/**
 * Handler function
 */
export function handler(event) {
    const size = event.size;

    // Optional seed
    if ("seed" in event) {
        // Node.js random seed workaround
        const seedrandom = await import("seedrandom");
        seedrandom(event.seed, { global: true });
    }

    // ---- GENERATE GRAPH ----
    const graphGeneratingBegin = performance.now();
    const graph = BarabasiAlbertGenerator(size, 10); // n = size, m = 10
    const graphGeneratingEnd = performance.now();

    // ---- COMPUTE PAGERANK ----
    const processBegin = performance.now();
    const result = pagerank(graph);
    const processEnd = performance.now();

    const graphGeneratingTime = (graphGeneratingEnd - graphGeneratingBegin) * 1000; // µs
    const processTime = (processEnd - processBegin) * 1000; // µs

    return {
        result: result[0], // match Python returning first element
        measurement: {
            graph_generating_time: graphGeneratingTime,
            compute_time: processTime
        }
    };
}
