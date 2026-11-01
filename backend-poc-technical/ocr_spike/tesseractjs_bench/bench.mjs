import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createWorker } from 'tesseract.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SAMPLES_DIR = path.resolve(__dirname, '../samples/synthetic');
const PHOTOS_DIR = path.resolve(__dirname, '../samples/photos');
const OUTPUT_FILE = path.resolve(__dirname, '../tesseractjs_results.json');

async function benchmarkWorker(langs, label, allFiles) {
  console.log(`\n================================================================`);
  console.log(`BENCHMARKING Tesseract.js with languages: [${langs.join(', ')}]`);
  console.log(`================================================================`);

  const initStart = performance.now();
  const worker = await createWorker(langs, 1, {
    logger: m => {}
  });
  const initDuration = (performance.now() - initStart) / 1000.0;
  console.log(`Worker initialized in ${initDuration.toFixed(2)}s`);

  let peakMem = process.memoryUsage().rss;
  const timings = [];
  const results = {};

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

    console.log(`[${label}] [${item.name}] (${item.category}): ${Math.round(elapsedMs)} ms, Conf: ${Math.round(ret.data.confidence)}%`);
  }

  await worker.terminate();

  const finalPeakMb = Number((peakMem / (1024 * 1024)).toFixed(2));
  const meanLatencyMs = Math.round(timings.reduce((a, b) => a + b, 0) / timings.length);

  return {
    langs: langs,
    worker_init_seconds: Number(initDuration.toFixed(2)),
    peak_memory_mb: finalPeakMb,
    mean_latency_ms: meanLatencyMs,
    results: results
  };
}

async function runBenchmark() {
  console.log('================================================================');
  console.log('TESSERACT.JS BENCHMARK RUNNER (Node.js Engine — Correction 3)');
  console.log('================================================================\n');

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

  // Run 1: 'eng' only (clean fair test for English documents)
  const resEng = await benchmarkWorker(['eng'], 'eng-only', allFiles);

  // Run 2: 'eng+urd' (bilingual test)
  const resEngUrd = await benchmarkWorker(['eng', 'urd'], 'eng+urd', allFiles);

  const benchmarkSummary = {
    engine: 'Tesseract.js (Node.js)',
    total_samples: allFiles.length,
    eng: resEng,
    eng_urd: resEngUrd,
    // Keep backward-compatible top-level keys pointing to 'eng' (default clean test)
    worker_init_seconds: resEng.worker_init_seconds,
    peak_memory_mb: resEng.peak_memory_mb,
    mean_latency_ms: resEng.mean_latency_ms,
    results: resEng.results
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(benchmarkSummary, null, 2), 'utf8');

  console.log('\n----------------------------------------------------------------');
  console.log(`BENCHMARK COMPLETE`);
  console.log(`Total Samples Processed: ${allFiles.length}`);
  console.log(`'eng' only Mean Latency: ${resEng.mean_latency_ms} ms, Peak Mem: ${resEng.peak_memory_mb} MB`);
  console.log(`'eng+urd' Mean Latency: ${resEngUrd.mean_latency_ms} ms, Peak Mem: ${resEngUrd.peak_memory_mb} MB`);
  console.log(`Results saved to: ${OUTPUT_FILE}`);
  console.log('================================================================');
}

runBenchmark().catch(err => {
  console.error('Benchmark Error:', err);
  process.exit(1);
});
