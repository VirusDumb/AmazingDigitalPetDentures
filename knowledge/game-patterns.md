# Game Patterns for Single-File HTML Games

Lean browser-native patterns for generated games. Use one `.html` file. Use raw Canvas 2D, or three.js by CDN importmap for 3D. No build step, multiple files, backend runtime, alternate engines, multiplayer stacks, distribution notes, or architecture essays.

## Single Game Loop

Use exactly one `requestAnimationFrame` loop. Clamp delta-time so tab switches do not launch entities through walls.

```javascript
let lastTime = performance.now();

function update(dt) {
  // dt is seconds. Move with pixels-per-second values:
  player.x += player.vx * dt;
  player.y += player.vy * dt;
}

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  // draw background, world, actors, particles, HUD in that order
}

function loop(now) {
  const dt = Math.min((now - lastTime) / 1000, 0.05);
  lastTime = now;
  update(dt);
  render();
  requestAnimationFrame(loop);
}

requestAnimationFrame(loop);
```

Fixed timestep only when physics must be deterministic:

```javascript
const STEP = 1 / 60;
let previous = performance.now();
let accumulator = 0;

function frame(now) {
  accumulator += Math.min((now - previous) / 1000, 0.1);
  previous = now;
  while (accumulator >= STEP) {
    update(STEP);
    accumulator -= STEP;
  }
  render();
  requestAnimationFrame(frame);
}

requestAnimationFrame(frame);
```

## Canvas Setup and DPR Resize

CSS size controls layout. Backing-store size uses device pixels to avoid blur.

```javascript
const canvas = document.querySelector("canvas");
const ctx = canvas.getContext("2d");

function resizeCanvas() {
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.round(rect.width * dpr);
  canvas.height = Math.round(rect.height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  game.width = rect.width;
  game.height = rect.height;
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
```

Minimal single-file shell:

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; }
    canvas { display: block; width: 100vw; height: 100vh; background: #0b1020; }
  </style>
</head>
<body>
  <canvas></canvas>
  <script>
    const game = {};
    const canvas = document.querySelector("canvas");
    const ctx = canvas.getContext("2d");
  </script>
</body>
</html>
```

## Canvas Draw Essentials

Clear every frame. Draw back-to-front. Use `save()`/`restore()` around transforms.

```javascript
ctx.clearRect(0, 0, game.width, game.height);

ctx.fillStyle = "#68d391";
ctx.fillRect(platform.x, platform.y, platform.w, platform.h);

ctx.strokeStyle = "#ffffff";
ctx.strokeRect(goal.x, goal.y, goal.w, goal.h);

ctx.save();
ctx.translate(player.x + player.w / 2, player.y + player.h / 2);
ctx.rotate(player.angle);
ctx.fillStyle = "#ffd166";
ctx.fillRect(-player.w / 2, -player.h / 2, player.w, player.h);
ctx.restore();
```

## Draw Images and Spritesheets

Use `drawImage` for whole images or source rectangles from a spritesheet.

```javascript
const image = new Image();
image.src = "data:image/png;base64,PUT_BASE64_HERE";

function drawSprite(entity) {
  ctx.drawImage(image, entity.x, entity.y, entity.w, entity.h);
}

function drawFrame(sheet, frame, x, y, w, h) {
  const sx = frame * w;
  ctx.drawImage(sheet, sx, 0, w, h, x, y, w, h);
}
```

## Keyboard Held-State Map

Track held keys with `keydown` and `keyup`. Read the map in `update`.

```javascript
const keys = Object.create(null);

function setKey(e, down) {
  keys[e.code] = down;
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space"].includes(e.code)) {
    e.preventDefault();
  }
}

window.addEventListener("keydown", (e) => setKey(e, true));
window.addEventListener("keyup", (e) => setKey(e, false));

function readMovement() {
  const x = (keys.ArrowRight || keys.KeyD ? 1 : 0) - (keys.ArrowLeft || keys.KeyA ? 1 : 0);
  const y = (keys.ArrowDown || keys.KeyS ? 1 : 0) - (keys.ArrowUp || keys.KeyW ? 1 : 0);
  return { x, y };
}
```

## Mouse Position

Convert viewport coordinates to canvas CSS-pixel coordinates.

```javascript
const mouse = { x: 0, y: 0, down: false };

canvas.addEventListener("mousemove", (e) => {
  const rect = canvas.getBoundingClientRect();
  mouse.x = e.clientX - rect.left;
  mouse.y = e.clientY - rect.top;
});
canvas.addEventListener("mousedown", () => { mouse.down = true; });
canvas.addEventListener("mouseup", () => { mouse.down = false; });
```

## Touch Basics

Use passive `false` so `preventDefault()` works and the page does not scroll.

```javascript
const touch = { active: false, x: 0, y: 0 };

function updateTouch(e) {
  const t = e.touches[0] || e.changedTouches[0];
  const rect = canvas.getBoundingClientRect();
  touch.active = e.type !== "touchend" && e.type !== "touchcancel";
  touch.x = t.clientX - rect.left;
  touch.y = t.clientY - rect.top;
  e.preventDefault();
}

canvas.addEventListener("touchstart", updateTouch, { passive: false });
canvas.addEventListener("touchmove", updateTouch, { passive: false });
canvas.addEventListener("touchend", updateTouch, { passive: false });
canvas.addEventListener("touchcancel", updateTouch, { passive: false });
```

## Pointer Lock Mouse-Look

Request lock from a click. Use `movementX/Y` while locked.

```javascript
const look = { yaw: 0, pitch: 0 };

canvas.addEventListener("click", () => canvas.requestPointerLock());

document.addEventListener("mousemove", (e) => {
  if (document.pointerLockElement !== canvas) return;
  look.yaw += e.movementX * 0.002;
  look.pitch = clamp(look.pitch + e.movementY * 0.002, -1.3, 1.3);
});
```

## Collision Functions

Rects use top-left `x,y,w,h`. Circles use center `x,y,r`.

```javascript
function rectsOverlap(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

function circlesOverlap(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  const r = a.r + b.r;
  return dx * dx + dy * dy <= r * r;
}

function pointInRect(px, py, r) {
  return px >= r.x && px <= r.x + r.w && py >= r.y && py <= r.y + r.h;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
```

## Resolve AABB Overlap

For player vs solid block. Move the dynamic rect out along the shallowest axis.

```javascript
function resolveRect(dynamic, solid) {
  if (!rectsOverlap(dynamic, solid)) return { x: 0, y: 0 };

  const left = dynamic.x + dynamic.w - solid.x;
  const right = solid.x + solid.w - dynamic.x;
  const top = dynamic.y + dynamic.h - solid.y;
  const bottom = solid.y + solid.h - dynamic.y;
  const moveX = left < right ? -left : right;
  const moveY = top < bottom ? -top : bottom;

  if (Math.abs(moveX) < Math.abs(moveY)) {
    dynamic.x += moveX;
    dynamic.vx = 0;
    return { x: moveX, y: 0 };
  }
  dynamic.y += moveY;
  dynamic.vy = 0;
  return { x: 0, y: moveY };
}
```

## Physics Basics

Velocity is pixels per second. Acceleration changes velocity. Friction damps velocity.

```javascript
function applyPhysics(e, dt) {
  e.vx += e.ax * dt;
  e.vy += e.ay * dt;
  e.vy += 1400 * dt;          // gravity
  e.vx *= Math.pow(0.0005, dt); // friction tuned per second
  e.vx = clamp(e.vx, -320, 320);
  e.vy = clamp(e.vy, -900, 900);
  e.x += e.vx * dt;
  e.y += e.vy * dt;
}

function jump(e) {
  if (e.onGround) {
    e.vy = -620;
    e.onGround = false;
  }
}
```

## Entity Structs

Keep objects small and predictable.

```javascript
function makeEntity(x, y, w, h) {
  return {
    x, y, w, h,
    vx: 0, vy: 0,
    ax: 0, ay: 0,
    hp: 1,
    onGround: false,
    frame: 0,
    frameTime: 0
  };
}

function animate(entity, dt, frameCount, fps) {
  entity.frameTime += dt;
  if (entity.frameTime >= 1 / fps) {
    entity.frame = (entity.frame + 1) % frameCount;
    entity.frameTime = 0;
  }
}
```

## HUD Text on Canvas

Draw HUD last so it stays above the game.

```javascript
function drawHud() {
  ctx.save();
  ctx.font = "16px system-ui, sans-serif";
  ctx.textBaseline = "top";
  ctx.fillStyle = "white";
  ctx.strokeStyle = "black";
  ctx.lineWidth = 4;
  const text = "Score: " + score + "  Time: " + Math.ceil(timeLeft);
  ctx.strokeText(text, 12, 12);
  ctx.fillText(text, 12, 12);
  ctx.restore();
}
```

## Tilemap Draw and Collision

Use a 2D array. `0` is empty, `1` is solid. Convert world pixels to tile coordinates with `Math.floor`.

```javascript
const TILE = 32;
const map = [
  [1, 1, 1, 1, 1, 1],
  [1, 0, 0, 0, 0, 1],
  [1, 0, 1, 0, 2, 1],
  [1, 1, 1, 1, 1, 1]
];

function tileAtPixel(x, y) {
  const col = Math.floor(x / TILE);
  const row = Math.floor(y / TILE);
  return map[row]?.[col] ?? 1;
}

function isSolidAt(x, y) {
  return tileAtPixel(x, y) === 1;
}

function drawMap() {
  for (let row = 0; row < map.length; row++) {
    for (let col = 0; col < map[row].length; col++) {
      if (map[row][col] === 0) continue;
      ctx.fillStyle = map[row][col] === 1 ? "#2d3748" : "#f6e05e";
      ctx.fillRect(col * TILE, row * TILE, TILE, TILE);
    }
  }
}
```

## Tile Collision for a Rect

Check the four corners after movement.

```javascript
function rectHitsSolid(e) {
  return (
    isSolidAt(e.x, e.y) ||
    isSolidAt(e.x + e.w, e.y) ||
    isSolidAt(e.x, e.y + e.h) ||
    isSolidAt(e.x + e.w, e.y + e.h)
  );
}
```

## Simple Audio Beep

Create or resume audio only after a click/tap/key press.

```javascript
let audioCtx;

function getAudio() {
  audioCtx ||= new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === "suspended") audioCtx.resume();
  return audioCtx;
}

function beep(freq = 440, duration = 0.08, type = "square") {
  const ac = getAudio();
  const osc = ac.createOscillator();
  const gain = ac.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.08, ac.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + duration);
  osc.connect(gain).connect(ac.destination);
  osc.start();
  osc.stop(ac.currentTime + duration);
}
```

## Load and Play a Sample

Use data URLs or remote URLs that allow loading. Create a fresh source per play.

```javascript
async function loadSample(url) {
  const ac = getAudio();
  const response = await fetch(url);
  const bytes = await response.arrayBuffer();
  return ac.decodeAudioData(bytes);
}

function playSample(buffer, volume = 0.4) {
  const ac = getAudio();
  const source = ac.createBufferSource();
  const gain = ac.createGain();
  source.buffer = buffer;
  gain.gain.value = volume;
  source.connect(gain).connect(ac.destination);
  source.start();
}
```

## Three.js Minimal Single-File Boilerplate

Canonical 3D start: CDN importmap, scene, camera, renderer, light, one mesh, resize, movement, orbit-style camera. Runs in a plain `.html` file.

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; background: #0b1020; }
    canvas { display: block; }
  </style>
  <script type="importmap">
    {
      "imports": {
        "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
        "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
      }
    }
  </script>
</head>
<body>
  <script type="module">
    import * as THREE from "three";
    import { OrbitControls } from "three/addons/controls/OrbitControls.js";

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1020);

    const camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.1, 1000);
    camera.position.set(0, 2, 6);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setSize(innerWidth, innerHeight);
    document.body.appendChild(renderer.domElement);

    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(3, 5, 4);
    scene.add(light);
    scene.add(new THREE.AmbientLight(0xffffff, 0.35));

    const player = new THREE.Mesh(
      new THREE.BoxGeometry(1, 1, 1),
      new THREE.MeshStandardMaterial({ color: 0x66e3ff, roughness: 0.45 })
    );
    scene.add(player);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(20, 20),
      new THREE.MeshStandardMaterial({ color: 0x233044 })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.6;
    scene.add(floor);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    const keys = Object.create(null);
    addEventListener("keydown", (e) => { keys[e.code] = true; });
    addEventListener("keyup", (e) => { keys[e.code] = false; });

    addEventListener("resize", () => {
      camera.aspect = innerWidth / innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(innerWidth, innerHeight);
    });

    let last = performance.now();
    function loop(now) {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;

      const speed = 3 * dt;
      if (keys.KeyW || keys.ArrowUp) player.position.z -= speed;
      if (keys.KeyS || keys.ArrowDown) player.position.z += speed;
      if (keys.KeyA || keys.ArrowLeft) player.position.x -= speed;
      if (keys.KeyD || keys.ArrowRight) player.position.x += speed;
      player.rotation.y += dt;

      controls.target.copy(player.position);
      controls.update();
      renderer.render(scene, camera);
      requestAnimationFrame(loop);
    }

    requestAnimationFrame(loop);
  </script>
</body>
</html>
```

## Cleanup Listeners

When restarting a generated game in the same page, remove old listeners and cancel old loops.

```javascript
const cleanup = [];
let rafId = 0;

function on(target, type, handler, options) {
  target.addEventListener(type, handler, options);
  cleanup.push(() => target.removeEventListener(type, handler, options));
}

function stopGame() {
  cancelAnimationFrame(rafId);
  while (cleanup.length) cleanup.pop()();
}
```

## GOTCHAS

- One game loop only. Do not start both `setInterval` and `requestAnimationFrame`.
- Do not redeclare top-level `const canvas`, `const ctx`, `const scene`, etc. inside the same script.
- Canvas must be DPR-aware: CSS pixels for logic, backing pixels for sharp rendering.
- Always clear the canvas each frame unless trails are intentional.
- Draw order matters: background, map, entities, particles, HUD.
- Clamp delta-time spikes after tab switches or debugger pauses.
- Audio must start from a user gesture in many browsers.
- three.js CDN module imports need a correct `type="importmap"` plus `type="module"`.
- Use simple AABB/circle collision first. Skip polygon collision, broad-phase trees, and heavy physics unless the game truly needs them.
- Clean up listeners and animation frames before replacing/restarting a game.
