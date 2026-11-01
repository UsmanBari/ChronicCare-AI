import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createWorker } from 'tesseract.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SAMPLES_DIR = path.resolve(__dirname, '../samples/synthetic');
const PHOTOS_DIR = path.resolve(__dirname, '../samples/photos');
const OUTPUT_FILE = path.resolve(__dirname, '../tesseractjs_results.json');

async function runBenchmark() {
  console.log('================================================================');
  console.log('TESSERACT.JS BENCHMARK RUNNER (Node.js Engine)');
  console.log('================================================================\n');

  const initialMem = process.memoryUsage().rss;
  console.log(`Initial Node Process Memory (RSS): ${(initialMem / (1024 * 1024)).toFixed(2)} MB`);

  console.log('\nInitializing Tesseract.js Worker with languages: eng + urd...');
  const initStart = performance.now();
  const worker = await createWorker(['eng', 'urd'], 1, {
    logger: m => {}
  });
  const initDuration = (performance.now() - initStart) / 1000.0;
  console.log(`Worker initialized in ${initDuration.toFixed(2)}s`);

  // Gather image files
  const syntheticFiles = fs.readdirSync(SAMPLES_DIR)
    .filter(f => f.endsWith('.png'))
    .map(f => ({ name: f, path: path.join(SAMPLES_DIR, f), category: 'synthetic' }));

  const photoFiles = fs.existsSync(PHOTOS_DIR)
    ? fs.readdirSync(PHOTOS_DIR)
        .filter(f => f.endsWith('.png') || f.endsWith('.jpg') || f.endsWith('.jpeg'))
        .map(f => ({ name: f, path: path.join(PHOTOS_DIR, f), category: 'handwritten' }))
    : [];

  const allFiles = [...syntheticFiles, ...photoFiles];
  console.log(`Found ${allFiles.length} files to benchmark (${syntheticFiles.length} synthetic, ${photoFiles.length} handwritten).\n`);

  const results = {};
  let peakMem = process.memoryUsage().rss;
  const timings = [];

  for (const item of allFiles) {
    const t0 = performance.now();
    const ret = await worker.recognize(item.path);
    const elapsedMs = performance.now() - t0;
    timings.push(elapsedMs);

    const currentMem = process.memoryUsage().rss;
    if (currentMem > peakMem) {
      peakMem = currentMem;
    }

    results[item.name] = {
      category: item.category,
      latency_ms: Math.round(elapsedMs),
      text: ret.data.text,
      confidence: Math.round(ret.data.confidence)
    };

    console.log(`[${item.name}] (${item.category}): ${Math.round(elapsedMs)} ms, Conf: ${Math.round(ret.data.confidence)}%`);
  }

  await worker.terminate();

  const finalPeakMb = (peakMem / (1024 * 1024)).toFixed(2);
  const meanLatencyMs = Math.round(timings.reduce((a, b) => a + b, 0) / timings.length);

  const benchmarkSummary = {
    engine: 'Tesseract.js (Node.js)',
    worker_init_seconds: Number(initDuration.toFixed(2)),
    peak_memory_mb: Number(finalPeakMb),
    total_samples: allFiles.length,
    mean_latency_ms: meanLatencyMs,
    results: results
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(benchmarkSummary, null, 2), 'utf8');

  console.log('\n----------------------------------------------------------------');
  console.log(`BENCHMARK COMPLETE`);
  console.log(`Total Samples Processed: ${allFiles.length}`);
  console.log(`Mean Latency: ${meanLatencyMs} ms per image`);
  console.log(`Peak Process Memory: ${finalPeakMb} MB`);
  console.log(`Results saved to: ${OUTPUT_FILE}`);
  console.log('================================================================');
}

runBenchmark().catch(err => {
  console.error('Benchmark Error:', err);
  process.exit(1);
});

