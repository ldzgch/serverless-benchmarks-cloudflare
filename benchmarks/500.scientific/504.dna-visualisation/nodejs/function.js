import fs from "fs";
import path from "path";
import os from "os";
import { Readable } from "stream";
import storage from "./storage/index.js";
import { transform } from "squiggle"; // assuming squiggle is installed in Node.js

const client = storage.get_instance();

export async function handler(event) {
    const bucket = event.bucket.bucket;
    const inputPrefix = event.bucket.input;
    const outputPrefix = event.bucket.output;
    const key = event.object.key;

    const downloadPath = path.join(os.tmpdir(), key);

    // ---- DOWNLOAD ----
    const downloadBegin = Date.now();
    await client.download(bucket, path.join(inputPrefix, key), downloadPath);
    const downloadStop = Date.now();

    const data = fs.readFileSync(downloadPath, "utf-8");

    // ---- PROCESS ----
    const processBegin = Date.now();
    const result = transform(data);
    const processEnd = Date.now();

    // ---- UPLOAD ----
    const uploadBegin = Date.now();
    const buf = Readable.from(JSON.stringify(result));
    const keyName = await client.uploadStream(bucket, path.join(outputPrefix, key), buf);
    const uploadStop = Date.now();

    const downloadTime = (downloadStop - downloadBegin) * 1000; // µs
    const processTime = (processEnd - processBegin) * 1000; // µs
    const uploadTime = (uploadStop - uploadBegin) * 1000; // µs

    return {
        result: {
            bucket: bucket,
            key: keyName
        },
        measurement: {
            download_time: downloadTime,
            compute_time: processTime,
            upload_time: uploadTime
        }
    };
}
