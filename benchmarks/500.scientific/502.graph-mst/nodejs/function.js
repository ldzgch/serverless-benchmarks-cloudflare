import { performance } from "perf_hooks";
import { BarabasiAlbertGenerator } from "graphology-generators/classic";
import { kruskal } from "graphology-mst";
import seedrandom from "seedrandom";

/**
 * Handler function for spanning tree benchmark
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

    // ---- COMPUTE SPANNING TREE ----
    const processBegin = performance.now();
    const spanningTree = kruskal(graph); // returns a new graph
    const processEnd = performance.now();

    const graphGeneratingTime = (graphGeneratingEnd - graphGeneratingBegin) * 1000; // µs
    const processTime = (processEnd - processBegin) * 1000; // µs

    return {
        result: spanningTree.nodes()[0], // match Python returning first element
        measurement: {
            graph_generating_time: graphGeneratingTime,
            compute_time: processTime
        }
    };
}
