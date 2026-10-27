'use strict';

// İKA host arayüzü: rosbridge (roslib.js) üzerinden robotla konuşur.
// Robotun yayınladığı her şey ROS topic/servis isimleriyle aşağıda toplanır.

const API = {
  mode: ['/ika/mode', 'std_msgs/msg/String'],
  estopActive: ['/ika/estop_active', 'std_msgs/msg/Bool'],
  obstacle: ['/ika/obstacle_distance', 'std_msgs/msg/Float32'],
  pose: ['/ika/robot_pose', 'geometry_msgs/msg/PoseStamped'],
  odom: ['/wheel/odom', 'nav_msgs/msg/Odometry'],
  map: ['/map', 'nav_msgs/msg/OccupancyGrid'],
  plan: ['/plan', 'nav_msgs/msg/Path'],
  line: ['/line/state', 'ika_interfaces/msg/LineState'],
  lineStatus: ['/line_follower/status', 'std_msgs/msg/String'],
  rosout: ['/rosout', 'rcl_interfaces/msg/Log'],
  teleop: ['/cmd_vel/teleop', 'geometry_msgs/msg/Twist'],
  goal: ['/goal_pose', 'geometry_msgs/msg/PoseStamped'],
  setMode: ['/ika/set_mode', 'ika_interfaces/srv/SetMode'],
  estop: ['/ika/estop', 'std_srvs/srv/SetBool'],
  saveMap: ['/ika/save_map', 'ika_interfaces/srv/SaveMap'],
};
const ROSBRIDGE_PORT = 9090;
const OUR_NODES = /mode_manager|map_manager|line_follower|ika_base|ika_imu|line_sensor/;

const $ = (id) => document.getElementById(id);
let ros = null;
let connected = false;
let reconnectTimer = null;
let reconnectDelay = 1000;
const state = { mode: 'idle', estop: false, map: null, pose: null, plan: [], goal: null, obstacleAt: 0 };

// --- kayıt ---------------------------------------------------------------
function log(text, level = 'info') {
  const el = $('log');
  const line = document.createElement('div');
  line.className = level;
  line.textContent = `[${new Date().toLocaleTimeString('tr-TR', { hour12: false })}] ${text}`;
  el.appendChild(line);
  while (el.children.length > 300) el.removeChild(el.firstChild);
  el.scrollTop = el.scrollHeight;
}

// --- bağlantı --------------------------------------------------------------
function storedHost() {
  try { return localStorage.getItem('ika-host'); } catch (e) { return null; }
}

function connect() {
  const host = $('host').value.trim() || 'localhost';
  try { localStorage.setItem('ika-host', host); } catch (e) { /* gizli pencere */ }
  reconnectDelay = 1000;
  connectTo(host);
}

function resetTeleop() {
  teleopTopic = null;
  wasMoving = false;
  heldKeys.clear();
  heldPads.clear();
  document.querySelectorAll('.key.pressed').forEach((b) => b.classList.remove('pressed'));
}

function retryConnection(activeRos, host) {
  if (ros !== activeRos || reconnectTimer !== null) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectTo(host);
  }, reconnectDelay);
  reconnectDelay = Math.min(reconnectDelay * 2, 10000);
}

function connectTo(host) {
  if (reconnectTimer !== null) clearTimeout(reconnectTimer);
  reconnectTimer = null;
  const url = `ws://${host.includes(':') ? host : `${host}:${ROSBRIDGE_PORT}`}`;
  const previous = ros;
  const activeRos = new ROSLIB.Ros();
  ros = activeRos;
  connected = false;
  $('conn-state').className = 'dot off';
  resetTeleop();
  if (previous) previous.close();
  activeRos.on('connection', () => {
    if (ros !== activeRos || connected) return;
    if (reconnectTimer !== null) clearTimeout(reconnectTimer);
    reconnectTimer = null;
    reconnectDelay = 1000;
    connected = true;
    $('conn-state').className = 'dot on';
    log(`bağlandı: ${host}`);
    subscribeAll();
  });
  activeRos.on('close', () => {
    if (ros !== activeRos) return;
    if (connected) log('bağlantı koptu; yeniden bağlanılacak', 'warn');
    connected = false;
    resetTeleop();
    $('conn-state').className = 'dot off';
    retryConnection(activeRos, host);
  });
  activeRos.on('error', () => {
    if (ros !== activeRos) return;
    if (reconnectTimer === null) log(`rosbridge'e ulaşılamadı: ${url}; yeniden denenecek`, 'error');
    connected = false;
    resetTeleop();
    $('conn-state').className = 'dot off';
    retryConnection(activeRos, host);
  });
  activeRos.connect(url);
}

function topic([name, type], options = {}) {
  return new ROSLIB.Topic({ ros, name, messageType: type, ...options });
}

function call([name, type], request, done) {
  const service = new ROSLIB.Service({ ros, name, serviceType: type });
  service.callService(new ROSLIB.ServiceRequest(request), done,
    (err) => log(`${name}: ${err}`, 'error'));
}

function subscribeAll() {
  topic(API.mode).subscribe((m) => { state.mode = m.data; renderMode(); });
  topic(API.estopActive).subscribe((m) => { state.estop = m.data; renderMode(); });
  topic(API.obstacle).subscribe((m) => {
    state.obstacleAt = Date.now();
    $('obstacle').textContent = `${m.data.toFixed(2)} m`;
  });
  topic(API.pose, { throttle_rate: 100 }).subscribe((m) => {
    state.pose = m;
    const p = m.pose.position;
    $('pose').textContent = `${p.x.toFixed(2)}, ${p.y.toFixed(2)} (${m.header.frame_id})`;
    drawMap();
  });
  topic(API.odom, { throttle_rate: 200 }).subscribe((m) => {
    const t = m.twist.twist;
    $('speed').textContent = `${t.linear.x.toFixed(2)} m/s · ${t.angular.z.toFixed(2)} rad/s`;
  });
  topic(API.map, { throttle_rate: 2000 }).subscribe((m) => { setMap(m); });
  topic(API.plan, { throttle_rate: 500 }).subscribe((m) => {
    state.plan = m.poses.map((p) => p.pose.position);
    drawMap();
  });
  topic(API.line, { throttle_rate: 100 }).subscribe(renderLine);
  topic(API.lineStatus).subscribe((m) => { $('line-status').textContent = m.data; });
  topic(API.rosout, { queue_length: 20 }).subscribe((m) => {
    if (m.level >= 30 || (m.level >= 20 && OUR_NODES.test(m.name))) {
      log(`${m.name}: ${m.msg}`, m.level >= 40 ? 'error' : m.level >= 30 ? 'warn' : 'info');
    }
  });
}

// --- mod / acil durdurma -------------------------------------------------
function renderMode() {
  const badge = $('mode-badge');
  badge.textContent = state.estop ? 'ACİL DURDURMA' : state.mode.toUpperCase();
  badge.className = `badge mode-${state.estop ? 'estop' : state.mode}`;
  document.body.classList.toggle('estop-active', state.estop);
  $('estop').classList.toggle('hidden', state.estop);
  $('release').classList.toggle('hidden', !state.estop);
  document.querySelectorAll('[data-mode]').forEach((b) => {
    b.classList.toggle('active', b.dataset.mode === state.mode);
  });
}

function setMode(mode) {
  if (!connected) return;
  call(API.setMode, { mode }, (res) => log(`mod: ${res.message}`, res.success ? 'info' : 'warn'));
}

function setEstop(active) {
  if (!connected) return;
  if (active) publishTwist(0, 0);
  call(API.estop, { data: active }, () => {});
}

// --- sürüş ---------------------------------------------------------------
const KEYS = {
  w: [1, 0], arrowup: [1, 0], s: [-1, 0], arrowdown: [-1, 0],
  a: [0, 1], arrowleft: [0, 1], d: [0, -1], arrowright: [0, -1],
};
const heldKeys = new Set();
const heldPads = new Set();
let teleopTopic = null;
let wasMoving = false;

function publishTwist(v, w) {
  if (!connected) return;
  if (!teleopTopic) teleopTopic = topic(API.teleop);
  teleopTopic.publish(new ROSLIB.Message({
    linear: { x: v, y: 0, z: 0 }, angular: { x: 0, y: 0, z: w },
  }));
}

function gamepadInput() {
  const pads = navigator.getGamepads ? navigator.getGamepads() : [];
  for (const pad of pads) {
    if (!pad) continue;
    const dead = (x) => (Math.abs(x) < 0.15 ? 0 : x);
    const v = -dead(pad.axes[1] || 0);
    const w = -dead(pad.axes[0] || 0);
    if (v || w) return [v, w];
  }
  return [0, 0];
}

function teleopTick() {
  let v = 0;
  let w = 0;
  for (const vec of [...[...heldKeys].map((k) => KEYS[k]), ...heldPads]) {
    v += vec[0];
    w += vec[1];
  }
  const [gv, gw] = gamepadInput();
  v = Math.max(-1, Math.min(1, v + gv));
  w = Math.max(-1, Math.min(1, w + gw));
  const moving = v !== 0 || w !== 0;
  if (state.estop) return;
  if (moving) {
    publishTwist(v * parseFloat($('v-max').value), -w * parseFloat($('w-max').value));
  } else if (wasMoving) {
    publishTwist(0, 0);
  }
  wasMoving = moving;
}

function typing(e) {
  return e.target instanceof HTMLInputElement && e.target.type !== 'range' && e.target.type !== 'checkbox';
}

window.addEventListener('keydown', (e) => {
  if (typing(e)) return;
  if (e.code === 'Space') { e.preventDefault(); setEstop(true); return; }
  const key = e.key.toLowerCase();
  if (KEYS[key]) { e.preventDefault(); heldKeys.add(key); }
});
window.addEventListener('keyup', (e) => heldKeys.delete(e.key.toLowerCase()));
window.addEventListener('blur', () => heldKeys.clear());

document.querySelectorAll('.key').forEach((btn) => {
  const vec = [parseFloat(btn.dataset.v), parseFloat(btn.dataset.w)];
  const release = () => { heldPads.delete(vec); btn.classList.remove('pressed'); };
  btn.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    btn.setPointerCapture(e.pointerId);
    heldPads.add(vec);
    btn.classList.add('pressed');
  });
  btn.addEventListener('pointerup', release);
  btn.addEventListener('pointercancel', release);
});

// --- çizgi sensörü -------------------------------------------------------
function renderLine(msg) {
  const box = $('line-sensors');
  if (box.children.length !== msg.sensors.length) {
    box.replaceChildren(...msg.sensors.map(() => document.createElement('span')));
  }
  msg.sensors.forEach((on, i) => {
    box.children[i].classList.toggle('on', on);
    box.children[i].title = `ham: ${msg.raw[i]}`;
  });
  $('line-raw').textContent = msg.raw.length ? `ham: ${msg.raw.join(' ')}` : '';
}

// --- harita --------------------------------------------------------------
const canvas = $('map');
const ctx = canvas.getContext('2d');
const mapImage = document.createElement('canvas');
let view = null;   // { scale, ox, oy } — dünya <-> piksel dönüşümü

function setMap(msg) {
  const { width: w, height: h, resolution, origin } = msg.info;
  mapImage.width = w;
  mapImage.height = h;
  const mctx = mapImage.getContext('2d');
  const img = mctx.createImageData(w, h);
  const css = getComputedStyle(document.documentElement);
  const rgb = (name) => css.getPropertyValue(name).trim().match(/\w\w/g).map((x) => parseInt(x, 16));
  const free = rgb('--free');
  const occupied = rgb('--occupied');
  const unknown = rgb('--unknown');
  for (let j = 0; j < h; j++) {
    for (let i = 0; i < w; i++) {
      const v = msg.data[j * w + i];
      const c = v < 0 ? unknown : v >= 65 ? occupied : free;
      const k = ((h - 1 - j) * w + i) * 4;   // OccupancyGrid satır 0 = en alt
      img.data[k] = c[0]; img.data[k + 1] = c[1]; img.data[k + 2] = c[2]; img.data[k + 3] = 255;
    }
  }
  mctx.putImageData(img, 0, 0);
  state.map = { w, h, resolution, origin: origin.position };
  $('map-info').textContent = `${w}×${h} hücre · ${resolution.toFixed(2)} m/hücre`;
  drawMap();
}

function toCanvas(x, y) {
  const m = state.map;
  return [view.ox + (x - m.origin.x) / m.resolution * view.scale,
    view.oy + (m.h - (y - m.origin.y) / m.resolution) * view.scale];
}

function toWorld(cx, cy) {
  const m = state.map;
  return [m.origin.x + (cx - view.ox) / view.scale * m.resolution,
    m.origin.y + (m.h - (cy - view.oy) / view.scale) * m.resolution];
}

function yawOf(q) {
  return Math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z));
}

function resizeCanvas() {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * dpr;
  canvas.height = canvas.clientHeight * dpr;
  drawMap();
}

function drawMap() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const m = state.map;
  if (!m) return;
  const scale = Math.min(canvas.width / m.w, canvas.height / m.h);
  view = { scale, ox: (canvas.width - m.w * scale) / 2, oy: (canvas.height - m.h * scale) / 2 };
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(mapImage, view.ox, view.oy, m.w * scale, m.h * scale);
  const px = (meters) => meters / m.resolution * scale;

  if (state.plan.length > 1) {
    ctx.strokeStyle = '#f0a830';
    ctx.lineWidth = 2;
    ctx.beginPath();
    state.plan.forEach((p, i) => {
      const [x, y] = toCanvas(p.x, p.y);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
  if (state.goal) {
    const [x, y] = toCanvas(state.goal[0], state.goal[1]);
    ctx.strokeStyle = '#f0a830';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, Math.max(6, px(0.08)), 0, 2 * Math.PI);
    ctx.stroke();
  }
  if (state.pose && state.pose.header.frame_id === 'map') {
    const p = state.pose.pose.position;
    const [x, y] = toCanvas(p.x, p.y);
    const r = Math.max(6, px(0.12));
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(-yawOf(state.pose.pose.orientation));
    ctx.fillStyle = '#4c8dff';
    ctx.beginPath();
    ctx.moveTo(r * 1.4, 0);
    ctx.lineTo(-r, r);
    ctx.lineTo(-r * 0.5, 0);
    ctx.lineTo(-r, -r);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }
}

canvas.addEventListener('click', (e) => {
  if (!$('goal-mode').checked || !state.map || !view || !connected) return;
  if (state.estop) { log('acil durdurma aktifken hedef verilemez', 'warn'); return; }
  const rect = canvas.getBoundingClientRect();
  const dpr = canvas.width / rect.width;
  const [x, y] = toWorld((e.clientX - rect.left) * dpr, (e.clientY - rect.top) * dpr);
  let yaw = 0;
  if (state.pose && state.pose.header.frame_id === 'map') {
    const p = state.pose.pose.position;
    yaw = Math.atan2(y - p.y, x - p.x);
  }
  // Önce modu açıkça nav'a al; mode_manager'ın /goal_pose'u duyması tek
  // bir mesaja bağlı kalmasın.
  call(API.setMode, { mode: 'nav' }, (res) => {
    if (!res.success) { log(`hedef verilemedi: ${res.message}`, 'warn'); return; }
    state.goal = [x, y];
    topic(API.goal).publish(new ROSLIB.Message({
      header: { frame_id: 'map', stamp: { sec: 0, nanosec: 0 } },
      pose: {
        position: { x, y, z: 0 },
        orientation: { x: 0, y: 0, z: Math.sin(yaw / 2), w: Math.cos(yaw / 2) },
      },
    }));
    log(`hedef: ${x.toFixed(2)}, ${y.toFixed(2)}`);
    drawMap();
  });
});

// --- olaylar -------------------------------------------------------------
$('host').value = storedHost() || window.location.hostname || 'localhost';
$('connect').addEventListener('click', connect);
$('estop').addEventListener('click', () => setEstop(true));
$('release').addEventListener('click', () => setEstop(false));
document.querySelectorAll('[data-mode]').forEach((b) => {
  b.addEventListener('click', () => setMode(b.dataset.mode));
});
$('goal-mode').addEventListener('change', (e) => canvas.classList.toggle('goal', e.target.checked));
$('save-map').addEventListener('click', () => {
  if (!connected) return;
  log('harita kaydediliyor...');
  call(API.saveMap, { name: $('map-name').value.trim() },
    (res) => log(res.message, res.success ? 'info' : 'error'));
});
for (const id of ['v-max', 'w-max']) {
  const update = () => {
    $(`${id}-label`).textContent = `${$(id).value} ${id === 'v-max' ? 'm/s' : 'rad/s'}`;
  };
  $(id).addEventListener('input', update);
  update();
}
window.addEventListener('resize', resizeCanvas);
setInterval(teleopTick, 100);
setInterval(() => {
  if (Date.now() - state.obstacleAt > 1000) $('obstacle').textContent = '—';
}, 500);

resizeCanvas();
renderMode();
connect();
