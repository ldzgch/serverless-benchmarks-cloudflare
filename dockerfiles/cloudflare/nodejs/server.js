/*
 * This is a generic web server wrapper for sebs Node.js benchmarks.
 * It uses the built-in 'http' module to create a server,
 * imports the benchmark's 'handler.js', and executes it
 * for each incoming POST request.
 */
const http = require('http');
// Import the benchmark's handler function
const { handler } = require('./handler');

const server = http.createServer(async (req, res) => {
    
    if (req.method !== 'POST') {
        res.writeHead(405, { 'Content-Type': 'text/plain' });
        res.end('Method Not Allowed');
        return;
    }

    let body = '';
    req.on('data', chunk => {
        body += chunk.toString(); // convert Buffer to string
    });

    req.on('end', async () => {
        try {
            // Parse the incoming event
            const event = JSON.parse(body);

            // Execute the benchmark handler
            const result = await handler(event, {});
            
            // Return the result
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result));

        } catch (e) {
            console.error("Handler error:", e);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }
    });
});

const port = process.env.PORT || 8080;
server.listen(port, () => {
    console.log(`Server listening on port ${port}`);
});