// test.js
const path = require("path");
const { handler } = require("./function.js");

// Minimal fake storage backend from the benchmark framework
// DO NOT MODIFY — the real framework will replace it during actual deployment.
// Only used here for local testing.

async function run() {
    // Example event based on serverless-benchmarks structure
    const event = {
        bucket: {
            bucket: "local-bucket",
            input: "input-prefix",
            output: "output-prefix"
        },
        object: {
            key: "sample-folder",    // directory to compress
        }
    };

    try {
        console.log("Running local test…");
        const result = await handler(event);
        console.log("Handler result:");
        console.log(JSON.stringify(result, null, 2));
    } catch (err) {
        console.error("Handler threw an error:");
        console.error(err);
    }
}

run();
