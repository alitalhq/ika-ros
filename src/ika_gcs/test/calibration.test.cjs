const assert = require('node:assert/strict');
const test = require('node:test');
const { LineCalibration } = require('../web/calibration.js');

function harness() {
  const calls = [];
  const pending = [];
  let release;
  const c = new LineCalibration((action) => {
    calls.push(action);
    return new Promise((resolve, reject) => pending.push({ resolve, reject }));
  }, () => {}, () => new Promise((resolve) => { release = resolve; }));
  c.connection(true);
  c.update({ supported: true, ready: true, calibrated: false });
  return { c, calls, pending, settle: () => new Promise(setImmediate),
    release: () => release() };
}

async function start(h) {
  const p = h.c.start();
  assert.equal(h.c.active, true);
  assert.deepEqual(h.calls, ['idle']);
  h.pending.shift().resolve({ success: true });
  await p;
}

test('white then black require separate explicit clicks and save only on success', async () => {
  const h = harness();
  await start(h);
  let p = h.c.capture();
  assert.deepEqual(h.calls, ['idle']); // wait for fresh surface samples
  h.release();
  await h.settle();
  assert.deepEqual(h.calls, ['idle', 'white']);
  h.pending.shift().resolve({ success: true });
  await p;
  assert.equal(h.c.step, 'black');
  assert.equal(h.c.active, true);
  assert.equal(h.calls.length, 2); // never auto-capture the second surface
  p = h.c.capture();
  h.release();
  await h.settle();
  h.pending.shift().resolve({ success: true, message: 'saved' });
  await p;
  assert.deepEqual(h.calls, ['idle', 'white', 'black']);
  assert.equal(h.c.active, false);
  assert.equal(h.c.message, 'saved');
});

test('idle refusal never enables surface capture', async () => {
  const h = harness();
  const p = h.c.start();
  h.pending.shift().resolve({ success: false, message: 'rejected' });
  await p;
  assert.equal(h.c.active, false);
  await h.c.capture();
  assert.deepEqual(h.calls, ['idle']);
});

test('disconnect during wait cancels without calling calibration service', async () => {
  const h = harness();
  await start(h);
  const p = h.c.capture();
  h.c.connection(false);
  h.release();
  await p;
  assert.deepEqual(h.calls, ['idle']);
  assert.equal(h.c.active, false);
});

test('late service response cannot revive a cancelled/reconnected session', async () => {
  const h = harness();
  const p = h.c.start();
  h.c.connection(false);
  h.c.connection(true);
  h.pending.shift().resolve({ success: true });
  await p;
  assert.equal(h.c.active, false);
  assert.equal(h.c.available(), false);
});

test('missing, stale or nonserial capability disables calibration', async () => {
  const h = harness();
  h.c.statusAt = Date.now() - 3000;
  await h.c.start();
  h.c.update({ supported: false });
  await h.c.start();
  assert.deepEqual(h.calls, []);
});

test('duplicate clicks and mode changes cannot submit overlapping captures', async () => {
  const h = harness();
  await start(h);
  const p = h.c.capture();
  await h.c.capture();
  h.c.modeChanged('manual');
  h.release();
  await p;
  assert.deepEqual(h.calls, ['idle']);
  assert.equal(h.c.active, false);
});

test('separation failure stays on black step and can be retried', async () => {
  const h = harness();
  await start(h);
  h.c.step = 'black';
  const p = h.c.capture();
  h.release();
  await h.settle();
  h.pending.shift().resolve({ success: false, message: 'D4: surfaces overlap' });
  await p;
  assert.equal(h.c.active, true);
  assert.equal(h.c.busy, false);
  assert.equal(h.c.step, 'black');
  assert.match(h.c.message, /D4/);
});

test('transport timeout releases busy state without reporting success', async () => {
  const h = harness();
  await start(h);
  const p = h.c.capture();
  h.release();
  await h.settle();
  h.pending.shift().reject(new Error('timeout'));
  await p;
  assert.equal(h.c.busy, false);
  assert.equal(h.c.active, true);
  assert.match(h.c.message, /timeout/);
});
