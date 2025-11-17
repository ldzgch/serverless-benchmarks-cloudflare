const fs = require('fs');
const path = require('path');
const os = require('os');
const uuid = require('uuid');
const archiver = require('archiver');
const storage = require('./storage');

const storage_handler = new storage.storage();

function parseDirectory(directory) {
    let size = 0;

    function walk(dir) {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            const full = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                walk(full);
            } else {
                size += fs.statSync(full).size;
            }
        }
    }

    walk(directory);
    return size;
}

function makeArchive(srcDir, archivePath) {
    return new Promise((resolve, reject) => {
        const output = fs.createWriteStream(archivePath);
        const archive = archiver('zip');

        output.on('close', resolve);
        archive.on('error', reject);

        archive.pipe(output);
        archive.directory(srcDir, false);
        archive.finalize();
    });
}

exports.handler = async function (event) {
    const bucket = event.bucket.bucket;
    const input_prefix = event.bucket.input;
    const output_prefix = event.bucket.output;
    const key = event.object.key;

    const downloadPath = path.join(os.tmpdir(), `${key}-${uuid.v4()}`);
    fs.mkdirSync(downloadPath, { recursive: true });

    // ---- DOWNLOAD DIRECTORY ----
    const s3_download_begin = Date.now();
    await storage_handler.downloadDirectory(bucket, path.join(input_prefix, key), downloadPath);
    const s3_download_stop = Date.now();

    const size = parseDirectory(downloadPath);

    // ---- COMPRESS ----
    const compress_begin = Date.now();
    const archiveName = `${key}.zip`;
    const archivePath = path.join(downloadPath, archiveName);
    await makeArchive(downloadPath, archivePath);
    const compress_end = Date.now();

    // ---- UPLOAD ----
    const s3_upload_begin = Date.now();
    const archiveSize = fs.statSync(archivePath).size;

    const uploadedKey = await storage_handler.upload(
        bucket,
        path.join(output_prefix, archiveName),
        archivePath
    );

    const s3_upload_stop = Date.now();

    // ---- Python-style microsecond timings ----
    const download_time = (s3_download_stop - s3_download_begin) * 1000;
    const upload_time = (s3_upload_stop - s3_upload_begin) * 1000;
    const process_time = (compress_end - compress_begin) * 1000;

    return {
        result: {
            bucket: bucket,
            key: uploadedKey
        },
        measurement: {
            download_time: download_time,
            download_size: size,
            upload_time: upload_time,
            upload_size: archiveSize,
            compute_time: process_time
        }
    };
};
