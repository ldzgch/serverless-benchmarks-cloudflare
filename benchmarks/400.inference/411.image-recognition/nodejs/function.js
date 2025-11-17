import fs from "fs";
import path from "path";
import os from "os";
import { v4 as uuidv4 } from "uuid";
import storage from "./storage/index.js";
import { readFileSync } from "fs";

// Optional: WASM-based PyTorch or similar library
// npm install @xenova/torch
import * as torch from "@xenova/torch";
import sharp from "sharp";

const client = storage.get_instance();
const SCRIPT_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname));

const classIdx = JSON.parse(readFileSync(path.join(SCRIPT_DIR, "imagenet_class_index.json")));
const idx2label = Object.keys(classIdx).map(k => classIdx[k][1]);

let model = null;

/**
 * Load image and preprocess like torchvision transforms
 */
async function preprocessImage(imagePath) {
    // Resize + center crop + normalize to tensor
    const imageBuffer = fs.readFileSync(imagePath);
    let image = sharp(imageBuffer).resize(256, 256, { fit: "cover" }).toFormat("png");
    const resizedBuffer = await image.toBuffer();

    // Convert buffer to Float32Array and normalize
    const tensor = torch.from(resizedBuffer).div(255.0);
    // Assuming tensor shape is [H, W, C], we need [C, H, W]
    return tensor.permute([2, 0, 1]).unsqueeze(0); // add batch dimension
}

export async function handler(event) {
    const bucket = event.bucket.bucket;
    const inputPrefix = event.bucket.input;
    const modelPrefix = event.bucket.model;
    const key = event.object.input;
    const modelKey = event.object.model;

    const downloadPath = path.join(os.tmpdir(), `${key}-${uuidv4()}`);

    // ---- DOWNLOAD IMAGE ----
    const imageDownloadBegin = Date.now();
    await client.download(bucket, path.join(inputPrefix, key), downloadPath);
    const imageDownloadEnd = Date.now();

    // ---- LOAD MODEL (cache globally) ----
    let modelDownloadBegin, modelDownloadEnd, modelProcessBegin, modelProcessEnd;
    if (!model) {
        modelDownloadBegin = Date.now();
        const modelPath = path.join(os.tmpdir(), modelKey);
        await client.download(bucket, path.join(modelPrefix, modelKey), modelPath);
        modelDownloadEnd = Date.now();

        modelProcessBegin = Date.now();
        model = await torch.load(modelPath); // or torch.loadStateDict equivalent
        model.eval();
        modelProcessEnd = Date.now();
    } else {
        modelDownloadBegin = modelDownloadEnd = Date.now();
        modelProcessBegin = modelProcessEnd = Date.now();
    }

    // ---- INFERENCE ----
    const processBegin = Date.now();
    const inputTensor = await preprocessImage(downloadPath);

    const output = await model.forward(inputTensor);
    const [maxVal, index] = torch.max(output, 1);
    const prob = torch.softmax(output[0], 0);
    const ret = idx2label[index.item()];
    const processEnd = Date.now();

    // ---- TIMINGS (microseconds) ----
    const downloadTime = (imageDownloadEnd - imageDownloadBegin) * 1000 + (modelDownloadEnd - modelDownloadBegin) * 1000;
    const modelTime = (modelProcessEnd - modelProcessBegin) * 1000;
    const processTime = (processEnd - processBegin) * 1000;
    const modelDownloadTime = (modelDownloadEnd - modelDownloadBegin) * 1000;

    return {
        result: { idx: index.item(), class: ret },
        measurement: {
            download_time: downloadTime,
            compute_time: processTime + modelTime,
            model_time: modelTime,
            model_download_time: modelDownloadTime
        }
    };
}
