import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const PORT = 8080;
const BASE_URL = `http://localhost:${PORT}`;

async function isServerUp() {
  try {
    const res = await fetch(`${BASE_URL}/`, { signal: AbortSignal.timeout(1000) });
    return res.status === 200;
  } catch {
    return false;
  }
}

async function runTests() {
  let serverProcess = null;

  if (!(await isServerUp())) {
    console.log('[Test] Spawning production server on port', PORT);
    serverProcess = spawn(process.execPath, ['server.mjs'], {
      env: { ...process.env, PORT: String(PORT) },
      stdio: 'pipe',
    });

    serverProcess.stderr.on('data', (d) => process.stderr.write(d));

    // Wait for server to become ready
    const start = Date.now();
    let ready = false;
    while (Date.now() - start < 10000) {
      if (await isServerUp()) {
        ready = true;
        break;
      }
      await new Promise((r) => setTimeout(r, 200));
    }

    if (!ready) {
      serverProcess.kill('SIGKILL');
      throw new Error('Server failed to start within 10 seconds');
    }
  }

  try {
    console.log('Testing standalone production server on', BASE_URL);

    // Test 1: Root endpoint & Security Headers
    console.log('1. Checking root endpoint & security headers...');
    const rootRes = await fetch(`${BASE_URL}/`);
    assert.strictEqual(rootRes.status, 200, `Expected status 200, got ${rootRes.status}`);
    const xfo = rootRes.headers.get('x-frame-options');
    const csp = rootRes.headers.get('content-security-policy');
    const xcto = rootRes.headers.get('x-content-type-options');
    console.log('   Headers:', { xfo, csp, xcto });
    assert.strictEqual(xfo, 'DENY');
    assert.ok(csp && csp.includes("frame-ancestors 'none'"));
    assert.strictEqual(xcto, 'nosniff');
    console.log('   ✓ Root endpoint & security headers verified.');

    // Test 2: Active API endpoints on Preview/Production
    console.log('2. Checking /api/openai/hud-summary keyless degradation...');
    const hudRes = await fetch(`${BASE_URL}/api/openai/hud-summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: 'test' }),
    });
    // In keyless environment, returns 503 or degraded response cleanly without crashing
    assert.ok([200, 503].includes(hudRes.status), `Expected 200 or 503, got ${hudRes.status}`);
    console.log(`   ✓ HUD summary proxy responded honestly with HTTP ${hudRes.status}.`);

    // Test 6: GET /api/forest/status
    console.log('6. Checking /api/forest/status endpoint...');
    const forestStatusRes = await fetch(`${BASE_URL}/api/forest/status`);
    assert.strictEqual(forestStatusRes.status, 200, `Expected 200, got ${forestStatusRes.status}`);
    const forestStatus = await forestStatusRes.json();
    assert.strictEqual(forestStatus.status, 'nominal');
    assert.strictEqual(forestStatus.model.type, 'RULE_BASED_BASELINE');
    assert.ok(forestStatus.monitored_hotspots_count >= 5);
    console.log('   ✓ Forest Intelligence status & model metadata verified.');

    // Test 7: GET /api/forest/zones
    console.log('7. Checking /api/forest/zones catalog endpoint...');
    const forestZonesRes = await fetch(`${BASE_URL}/api/forest/zones`);
    assert.strictEqual(forestZonesRes.status, 200, `Expected 200, got ${forestZonesRes.status}`);
    const forestZones = await forestZonesRes.json();
    assert.ok(Array.isArray(forestZones.zones), 'Expected zones array');
    assert.ok(forestZones.zones.length >= 5);
    console.log(`   ✓ Forest zones catalog verified with ${forestZones.zones.length} monitored hotspots.`);

    // Test 8: POST /api/forest/predict
    console.log('8. Checking /api/forest/predict endpoint...');
    const predictRes = await fetch(`${BASE_URL}/api/forest/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        zoneId: 'amazon-rondonia',
      }),
    });
    assert.strictEqual(predictRes.status, 200, `Expected 200, got ${predictRes.status}`);
    const predictData = await predictRes.json();
    assert.strictEqual(predictData.prediction.observation_type, 'PREDICTED_RISK');
    assert.ok(Array.isArray(predictData.prediction.contributing_factors));
    console.log(`   ✓ Forest risk prediction verified: ${predictData.prediction.risk_level} (${(predictData.prediction.risk_probability * 100).toFixed(0)}%).`);

    // Test 9: POST /api/forest/analyze (Synchronous <= 1000 km2)
    console.log('9. Checking /api/forest/analyze synchronous mode (<= 1000 km²)...');
    const smallPoly = [
      [-62.0, -9.8],
      [-61.9, -9.8],
      [-61.9, -9.9],
      [-62.0, -9.9],
      [-62.0, -9.8],
    ];
    const analyzeSyncRes = await fetch(`${BASE_URL}/api/forest/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        coordinates: smallPoly,
        provider: 'sentinel-2',
      }),
    });
    assert.strictEqual(analyzeSyncRes.status, 200, `Expected 200, got ${analyzeSyncRes.status}`);
    const analyzeSyncData = await analyzeSyncRes.json();
    assert.strictEqual(analyzeSyncData.mode, 'SYNCHRONOUS');
    assert.ok(analyzeSyncData.result.change_detection);
    console.log(`   ✓ Synchronous change detection completed for ${analyzeSyncData.result.geodesic_area_km2.toFixed(1)} km².`);

    // Test 10: POST /api/forest/analyze (Asynchronous > 1000 km2 with 202 Accepted)
    console.log('10. Checking /api/forest/analyze asynchronous mode (> 1000 km²)...');
    const largePoly = [
      [-63.0, -9.0],
      [-61.0, -9.0],
      [-61.0, -11.0],
      [-63.0, -11.0],
      [-63.0, -9.0],
    ];
    const analyzeAsyncRes = await fetch(`${BASE_URL}/api/forest/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        coordinates: largePoly,
        provider: 'landsat',
      }),
    });
    assert.strictEqual(analyzeAsyncRes.status, 202, `Expected 202 Accepted, got ${analyzeAsyncRes.status}`);
    const analyzeAsyncData = await analyzeAsyncRes.json();
    assert.strictEqual(analyzeAsyncData.mode, 'ASYNCHRONOUS');
    assert.ok(analyzeAsyncData.jobId);
    console.log(`   ✓ Async job created: ${analyzeAsyncData.jobId} (status: ${analyzeAsyncData.status}).`);

    // Poll async job status
    await new Promise((r) => setTimeout(r, 200));
    const jobPollRes = await fetch(`${BASE_URL}/api/forest/jobs/${analyzeAsyncData.jobId}`);
    assert.strictEqual(jobPollRes.status, 200);
    const jobStatus = await jobPollRes.json();
    assert.ok(['QUEUED', 'RUNNING', 'COMPLETED'].includes(jobStatus.status));
    console.log(`   ✓ Async job poll verified: status is ${jobStatus.status}.`);

    // Test 11: POST /api/forest/predict payload size cap (64KB rejection)
    console.log('11. Checking /api/forest/predict payload cap (> 64KB)...');
    const oversizedPayload = { data: 'x'.repeat(70 * 1024) };
    const overRes = await fetch(`${BASE_URL}/api/forest/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(oversizedPayload),
    });
    assert.strictEqual(overRes.status, 413, `Expected 413, got ${overRes.status}`);
    console.log('   ✓ Oversized payload correctly rejected with HTTP 413.');

    console.log('\nAll production server verification tests PASSED successfully!');
  } finally {
    if (serverProcess) {
      serverProcess.kill('SIGTERM');
    }
  }
}

runTests().catch((err) => {
  console.error('Verification failed:', err);
  process.exit(1);
});
