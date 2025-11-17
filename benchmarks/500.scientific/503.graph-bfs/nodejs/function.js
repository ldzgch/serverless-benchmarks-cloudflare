import { performance } from "perf_hooks";
import { BarabasiAlbertGenerator } from "graphology-generators/classic";
import bfs from "graphology-traversal/bfs";
import seedrandom from "seedrandom";

/**
 * Handler function for BFS benchmark
 */
export function handler(event) {
    const size = event.size;

    // Optional seed
    if ("seed" in event) {
        seedrandom(event.seed, { global: true });
    }

    // ---- GENERATE GRAPH ----
    const graphGeneratingBegin = performance.now();
    const graph = BarabasiAlbertGenerator(size, 10); // n=size, m=10
    const graphGeneratingEnd = performance.now();

    // ---- BFS TRAVERSAL ----
    const processBegin = performance.now();
    const result = [];
    bfs(graph, '0', (node) => {
        result.push(node);
    });
    const processEnd = performance.now();

    const graphGeneratingTime = (graphGeneratingEnd - graphGeneratingBegin) * 1000; // µs
    const processTime = (processEnd - processBegin) * 1000; // µs

    return {
        result: result, // list of nodes visited in BFS order
        measurement: {
            graph_generating_time: graphGeneratingTime,
            compute_time: processTime
        }
    };
}
