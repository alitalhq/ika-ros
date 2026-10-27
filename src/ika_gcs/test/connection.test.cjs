const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function harness() {
  const elements = new Map();
  const sessions = [];
  const topics = [];
  const timers = new Map();
  let timerId = 0;
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value: id === 'host' ? 'robot' : id === 'v-max' ? '0.4' : '1.2',
      children: [], classList: { remove() {}, toggle() {} },
      addEventListener() {}, appendChild(child) { this.children.push(child); },
      clientWidth: 400, clientHeight: 400,
      getContext() { return { clearRect() {} }; },
    });
    return elements.get(id);
  }
  class Ros extends EventEmitter {
    constructor() { super(); sessions.push(this); }
    connect(url) { this.url = url; }
    close() { this.emit('close'); }
  }
  class Topic {
    constructor(options) { this.options = options; this.messages = []; topics.push(this); }
    subscribe() {}
    publish(message) { this.messages.push(message); }
  }
  const context = vm.createContext({
    ROSLIB: { Ros, Topic, Message: class { constructor(m) { Object.assign(this, m); } } },
    document: { body: element('body'), getElementById: element,
      createElement: element, querySelectorAll: () => [] },
    window: { addEventListener() {}, devicePixelRatio: 1, location: { hostname: 'robot' } },
    navigator: { getGamepads: () => [] },
    localStorage: { getItem: () => null, setItem() {} },
    setInterval() {},
    setTimeout(callback, delay) { timers.set(++timerId, { callback, delay }); return timerId; },
    clearTimeout(id) { timers.delete(id); },
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8'), context);
  return { sessions, topics, timers, element, run: (code) => vm.runInContext(code, context),
    retry() {
      assert.equal(timers.size, 1);
      const [id, timer] = timers.entries().next().value;
      timers.delete(id);
      timer.callback();
      return timer.delay;
    } };
}

test('bridge not ready at page load is retried once per failure, with capped backoff', () => {
  const h = harness();
  for (const expected of [1000, 2000, 4000, 8000, 10000, 10000]) {
    const session = h.sessions.at(-1);
    session.emit('error');
    session.emit('close');
    assert.equal(h.retry(), expected);
  }
  h.sessions.at(-1).emit('connection');
  assert.equal(h.element('conn-state').className, 'dot on');
  h.sessions.at(-1).emit('close');
  assert.equal(h.retry(), 1000);
});

test('old socket events and pending retry cannot override a manually selected host', () => {
  const h = harness();
  const old = h.sessions[0];
  old.emit('error');
  h.element('host').value = 'other-robot:9999';
  h.run('connect()');
  const current = h.sessions.at(-1);
  current.emit('connection');
  old.emit('close');
  old.emit('error');
  assert.equal(h.timers.size, 0);
  assert.equal(current.url, 'ws://other-robot:9999');
  assert.equal(h.element('conn-state').className, 'dot on');
});

test('reconnection clears held motion and publishes future commands on the new socket', () => {
  const h = harness();
  h.sessions[0].emit('connection');
  h.run("heldKeys.add('w'); teleopTick()");
  const first = h.topics.find((t) => t.options.name === '/cmd_vel/teleop');
  assert.equal(first.messages.length, 1);
  h.sessions[0].emit('close');
  h.retry();
  const current = h.sessions.at(-1);
  current.emit('connection');
  h.run('teleopTick()');
  assert.equal(first.messages.length, 1);
  assert.equal(h.topics.filter((t) => t.options.name === '/cmd_vel/teleop').length, 1);
  h.run("heldKeys.add('w'); teleopTick()");
  const publishers = h.topics.filter((t) => t.options.name === '/cmd_vel/teleop');
  assert.equal(publishers.length, 2);
  assert.equal(publishers[1].options.ros, current);
  assert.equal(publishers[1].messages[0].linear.x, 0.4);
});
