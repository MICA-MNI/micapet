// Report viewer — a surface coloured by a scalar map, hover reads the value
// at the picked vertex.
// Controls: drag to rotate, scroll or ←→ inflate/deflate, ↑↓ zoom,
// L lock, R reset, O opacity, M wireframe, Q toggle hover query, T table.

// ── Colormaps ──────────────────────────────────────────────────────────────
const CMAPS = {
  plasma:   [[13,8,135],[84,2,163],[139,10,165],[185,50,137],[219,92,104],[244,136,73],[254,188,43],[240,249,33]],
  viridis:  [[68,1,84],[72,40,120],[62,83,160],[49,104,142],[38,130,142],[31,158,137],[53,183,121],[110,206,88],[181,222,43],[253,231,37]],
  magma:    [[0,0,4],[28,16,68],[79,18,123],[129,37,129],[181,54,122],[229,89,100],[251,135,97],[254,194,140],[252,253,191]],
  RdBu_r:   [[33,102,172],[67,147,195],[146,197,222],[209,229,240],[247,247,247],[253,219,199],[239,138,98],[178,24,43]],
  coolwarm: [[59,76,192],[98,130,234],[141,176,254],[184,208,249],[221,220,220],[249,196,184],[244,154,123],[220,100,66],[180,4,38]],
  gray_r:   [[255,255,255],[0,0,0]],
  // jet (SUVR) and bwr (Z, AI) match the pipeline's own figures. jet is
  // sampled at 33 points, within 9/255 of matplotlib's definition.
  jet:      [[0,0,128],[0,0,164],[0,0,200],[0,0,236],[0,0,255],[0,32,255],[0,64,255],[0,96,255],[0,128,255],[0,159,255],[0,191,255],[0,223,252],[21,255,226],[46,255,201],[72,255,175],[98,255,149],[123,255,123],[149,255,98],[175,255,72],[201,255,46],[226,255,21],[252,240,0],[255,210,0],[255,181,0],[255,151,0],[255,122,0],[255,92,0],[255,63,0],[255,33,0],[236,4,0],[200,0,0],[164,0,0],[128,0,0]],
  bwr:      [[0,0,255],[255,255,255],[255,0,0]],
};
const CMAP_CYCLE_POS = ['jet', 'plasma', 'magma', 'viridis', 'gray_r'];
const CMAP_CYCLE_DIV = ['bwr', 'coolwarm', 'RdBu_r'];

// A map may name its own via `cmap`, applied once at load so that cycling
// with C still sticks when switching panels.
let currentCmapPos = 'jet';
let currentCmapDiv = 'bwr';
let currentCmap = 'jet';

function cmapRGB(t, name) {
  const lut = CMAPS[name] || CMAPS.plasma;
  t = Math.max(0, Math.min(1, t));
  const s = t * (lut.length - 1);
  const i = Math.min(Math.floor(s), lut.length - 2);
  const f = s - i;
  return lut[i].map((a, k) => Math.round(a + f * (lut[i+1][k] - a)));
}

// ── Colour range ──────────────────────────────────────────────────────────
// A map's payload vmin/vmax are its default range; dragging the colourbar
// scales both ends by the same factor, so a diverging map stays centred on
// zero.
const RANGE_MIN = 0.5, RANGE_MAX = 1.5;
const RANGE_DRAG_PX = 400;      // drag distance for the full 0.5 -> 1.5 sweep
// Maps naming the same `scale_group` share one factor, so a colour means the
// same value on the cortex and on the hippocampus however far the bar is
// dragged. Everything else is its own group.
const scaleGroup = PAYLOAD.maps.map((m, i) => m.scale_group || `#${i}`);
const rangeScale = {};

function scaleOf(idx) { return rangeScale[scaleGroup[idx]] ?? 1; }

function mapRange(idx) {
  const m = PAYLOAD.maps[idx], s = scaleOf(idx);
  return { vmin: m.vmin * s, vmax: m.vmax * s };
}

function drawColorbar() {
  const mapData = PAYLOAD.maps[activeMapIdx];
  const canvas = document.getElementById('colorbar-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  document.getElementById('colorbar-title').textContent = mapData.cb_label;

  canvas.width = 14; canvas.style.width = '14px';
  const w = canvas.width, h = canvas.height;
  const [c0, c1] = mapData.cmap_span;
  for (let y = 0; y < h; y++) {
    const [r,g,b] = cmapRGB(c0 + (1 - y/(h-1)) * (c1 - c0), currentCmap);
    ctx.fillStyle = `rgb(${r},${g},${b})`;
    ctx.fillRect(0, y, w, 1);
  }
  const fmt = v => {
    if (v === 0) return '0';
    if (Math.abs(v) < 0.01) return v.toExponential(1);
    return Math.abs(v) < 10 ? v.toFixed(2) : v.toFixed(1);
  };
  const { vmin, vmax } = mapRange(activeMapIdx);
  document.getElementById('cb-min').textContent = fmt(vmin);
  document.getElementById('cb-max').textContent = fmt(vmax);

  // Optional per-map reading note: one line per entry, each {text, cls}.
  const note = document.getElementById('cb-note');
  if (note) {
    const lines = mapData.cb_note || [];
    note.textContent = '';
    lines.forEach(line => {
      const div = document.createElement('div');
      div.textContent = line.text;
      if (line.cls) div.className = line.cls;
      note.appendChild(div);
    });
    note.style.display = lines.length ? 'block' : 'none';
  }
}

// ── State ────────────────────────────────────────────────────────────────
let sceneL, cameraL, rendererL, controlsL, meshL = null, wireL = null;
let sceneR, cameraR, rendererR, controlsR, meshR = null, wireR = null;
let viewLocked = true;
let lastMovedSide = 'L';
let cortexOpacity = 1.0;
let wireframeVisible = true;
const REDUCED_OPACITY = 0.30;

// Morph position is kept per mesh, not per panel: the cortical panels inflate
// together so two maps stay comparable, while the hippocampus keeps its own.
let morphT = 0.0;
const morphByMesh = {};
let hoveredSide = null;
let hoveredVertexIdx = -1;
let hoveredRoi = -1;
let hoverEnabled = false;    // 'Q' toggles the hover/click query system

const H_W = window.innerWidth / 2;
const H_H = window.innerHeight;
const CAM_DIST = 500;     // far enough that the whole mid surface fits with margin
const NO_PARCEL_RGB = [148, 148, 148];   // medium grey for unassigned vertices
const NO_DATA_RGB = [82, 82, 82];        // neutral no-data for thresholded-away vertices

const raycaster = new THREE.Raycaster();

// ── Decoders ─────────────────────────────────────────────────────────────
function b64ToBytes(b64) {
  const bin = atob(b64);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return u8;
}
const b64ToUint16  = b => new Uint16Array(b64ToBytes(b).buffer);

// Half-float (float16) → Float32Array. Geometry ships as float16 to halve its
// size; the ~0.06 mm precision is far below the vertex spacing.
function halfToFloat(h) {
  const s = (h & 0x8000) >> 15, e = (h & 0x7c00) >> 10, f = h & 0x03ff;
  if (e === 0)    return (s ? -1 : 1) * Math.pow(2, -14) * (f / 1024);
  if (e === 0x1f) return f ? NaN : (s ? -Infinity : Infinity);
  return (s ? -1 : 1) * Math.pow(2, e - 15) * (1 + f / 1024);
}
function b64ToFloat16(b) {
  const u16 = new Uint16Array(b64ToBytes(b).buffer);
  const out = new Float32Array(u16.length);
  for (let i = 0; i < u16.length; i++) out[i] = halfToFloat(u16[i]);
  return out;
}

// ── Decode meshes: one set per geometry, 3 surface states per hemi ───────
// A map names the mesh it is drawn on; switchMap rebuilds when that changes.
const SURFACE_KINDS = ['mid', 'inflated', 'sphere'];
const meshData = {};
Object.keys(PAYLOAD.meshes).forEach(name => {
meshData[name] = {};
['lh', 'rh'].forEach(h => {
  const m = PAYLOAD.meshes[name][h];
  const surfaces = {};
  SURFACE_KINDS.forEach(kind => {
    surfaces[kind] = {
      positions: b64ToFloat16(m.surfaces[kind].positions),
      normals:   b64ToFloat16(m.surfaces[kind].normals),
    };
  });
  // Centre each state on the origin so OrbitControls rotates about the
  // visual centre whatever morphT is.
  const nv = m.n_verts;
  SURFACE_KINDS.forEach(kind => {
    const p = surfaces[kind].positions;
    let cx = 0, cy = 0, cz = 0;
    for (let i = 0; i < nv; i++) { cx += p[i*3]; cy += p[i*3+1]; cz += p[i*3+2]; }
    cx /= nv; cy /= nv; cz /= nv;
    for (let i = 0; i < nv; i++) { p[i*3] -= cx; p[i*3+1] -= cy; p[i*3+2] -= cz; }
  });
  meshData[name][h] = {
    faces:    b64ToUint16(m.faces),
    n_verts:  nv,
    surfaces: surfaces,
    cortex:   b64ToBytes(m.cortex),          // 1 = cortex, 0 = medial wall
    // Yale-696 parcel per vertex; -1 = medial wall or unassigned.
    vertex_to_roi: new Int16Array(b64ToBytes(m.vertex_to_roi).buffer),
  };
});
});

// The mesh set and per-hemi data the active panel is drawn on.
function activeMeshSet() { return PAYLOAD.meshes[PAYLOAD.maps[activeMapIdx].mesh]; }
function activeMesh(hemiKey) { return meshData[PAYLOAD.maps[activeMapIdx].mesh][hemiKey]; }
function camDist() { return activeMeshSet().cam_dist || CAM_DIST; }

// Map values arrive as float16 base64 (NaN = no-data) — decode once to Float32.
PAYLOAD.maps.forEach(m => {
  m.lh = b64ToFloat16(m.lh);
  m.rh = b64ToFloat16(m.rh);
});

// Seed the two colormap slots from the payload once, so C keeps its effect
// when the reader moves between panels.
(() => {
  const pos = PAYLOAD.maps.find(m => m.cmap && m.cmap_type !== 'diverging');
  const div = PAYLOAD.maps.find(m => m.cmap && m.cmap_type === 'diverging');
  if (pos && CMAPS[pos.cmap]) currentCmapPos = currentCmap = pos.cmap;
  if (div && CMAPS[div.cmap]) currentCmapDiv = div.cmap;
})();

let activeMapIdx = 0;
let currentMeshName = null;
function switchMap(idx) {
  if (idx < 0) idx = PAYLOAD.maps.length - 1;
  if (idx >= PAYLOAD.maps.length) idx = 0;
  morphByMesh[PAYLOAD.maps[activeMapIdx].mesh] = morphT;
  activeMapIdx = idx;
  morphT = morphByMesh[PAYLOAD.maps[idx].mesh] || 0.0;

  const mapData = PAYLOAD.maps[activeMapIdx];
  currentCmap = mapData.cmap_type === 'diverging' ? currentCmapDiv : currentCmapPos;

  document.getElementById('map-label-main').textContent = mapData.label || "";
  const subEl = document.getElementById('map-label-sub');
  subEl.textContent = '';
  (mapData.sub_label || '').split('\n').forEach((line, i, arr) => {
    subEl.appendChild(document.createTextNode(line));
    if (i < arr.length - 1) subEl.appendChild(document.createElement('br'));
  });

  const btns = document.querySelectorAll('.nav-btn');
  btns.forEach((b, i) => {
    if (i === activeMapIdx) b.classList.add('active');
    else b.classList.remove('active');
  });

  drawColorbar();

  // A panel on a different geometry needs the meshes rebuilt and the camera
  // reframed, not just new vertex colours.
  if (mapData.mesh !== currentMeshName) {
    currentMeshName = mapData.mesh;
    rebuildMeshes();
  } else {
    if (meshL) recolorMesh('lh', meshL);
    if (meshR) recolorMesh('rh', meshR);
  }

  const tooltip = document.getElementById('tooltip');
  if (tooltip && tooltip.style.display === 'block' && hoveredSide !== null) {
    tooltip.innerHTML = buildHoverHtml(hoveredRoi, hoveredSide, hoveredVertexIdx);
  }
}

// ── Per-vertex colours from scalar map + colormap ─────────────────────────
function buildVertexColors(hemiKey) {
  const md   = activeMesh(hemiKey);
  const nv   = md.n_verts;
  const mapData = PAYLOAD.maps[activeMapIdx];
  const vals = mapData[hemiKey];
  const { vmin, vmax } = mapRange(activeMapIdx);
  const [c0, c1] = mapData.cmap_span;

  const colors = new Float32Array(nv * 4);
  for (let i = 0; i < nv; i++) {
    let r, g, b;
    if (!md.cortex[i]) {
      r = NO_PARCEL_RGB[0]/255; g = NO_PARCEL_RGB[1]/255; b = NO_PARCEL_RGB[2]/255;
    } else if (isNoDataValue(vals[i])) {
      r = NO_DATA_RGB[0]/255; g = NO_DATA_RGB[1]/255; b = NO_DATA_RGB[2]/255;
    } else {
      const t = vmax > vmin ? (vals[i] - vmin) / (vmax - vmin) : 0;
      const [R,G,B] = cmapRGB(c0 + t * (c1 - c0), currentCmap);
      r = R/255; g = G/255; b = B/255;
    }
    colors[i*4]=r; colors[i*4+1]=g; colors[i*4+2]=b; colors[i*4+3]=1.0;
  }
  return colors;
}

function isNoDataValue(v) {
  return v === null || !Number.isFinite(v);
}

function recolorMesh(hemiKey, mesh) {
  const colors = buildVertexColors(hemiKey);
  const attr = mesh.geometry.attributes.color;   // RGBA
  for (let i = 0; i < colors.length; i++) attr.array[i] = colors[i];
  attr.needsUpdate = true;
}

function rebuildMeshes() {
  [[sceneL, meshL, wireL], [sceneR, meshR, wireR]].forEach(([scene, mesh, wire]) => {
    if (!mesh) return;
    scene.remove(mesh); scene.remove(wire);
    mesh.geometry.dispose(); mesh.material.dispose(); wire.material.dispose();
  });
  const builtL = buildMesh('lh'), builtR = buildMesh('rh');
  meshL = builtL.mesh; wireL = builtL.wire; meshL.userData.hemiKey = 'lh';
  meshR = builtR.mesh; wireR = builtR.wire; meshR.userData.hemiKey = 'rh';
  sceneL.add(meshL); sceneL.add(wireL);
  sceneR.add(meshR); sceneR.add(wireR);
  applyOpacity();
  applyMorph();
  resetCameras();
  hideTooltip();
}

// Each mesh set carries the distance that frames it; the hippocampus would be
// a speck at the distance that frames a cortex.
function resetCameras() {
  const set = activeMeshSet(), d = camDist();
  [['lh', cameraL, controlsL], ['rh', cameraR, controlsR]].forEach(([h, cam, ctl]) => {
    const view = set[h].view;
    // OrbitControls decays its damped sphericalDelta but never clears it, and
    // the residue lands on top of the pose set below — so a reset ends
    // somewhere different every press. One update with damping off zeroes it.
    const damping = ctl.enableDamping;
    ctl.enableDamping = false;
    ctl.update();
    cam.position.set(view.eye[0] * d, view.eye[1] * d, view.eye[2] * d);
    cam.up.set(view.up[0], view.up[1], view.up[2]);
    ctl.target.set(0, 0, 0); ctl.update();
    ctl.enableDamping = damping;
  });
}

// ── Three.js setup ───────────────────────────────────────────────────────
function setupScene(containerId, isLeft) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(25, H_W / H_H, 0.1, 5000);
  camera.position.set(isLeft ? -CAM_DIST : CAM_DIST, 0, 0);
  camera.up.set(0, 0, 1);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setSize(H_W, H_H);
  renderer.setPixelRatio(Math.max(window.devicePixelRatio, 2));
  document.getElementById(containerId).appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const headlamp = new THREE.PointLight(0xffffff, 0.8);
  headlamp.position.set(0, 0, 0);
  camera.add(headlamp);
  scene.add(camera);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.enableZoom = false;     // scroll wheel → inflate/deflate
  controls.enablePan  = false;     // free right-click for tooltip pinning

  return { scene, camera, renderer, controls };
}

function buildMesh(hemiKey) {
  const md = activeMesh(hemiKey);
  const positions = new Float32Array(md.surfaces.mid.positions);
  const normals   = new Float32Array(md.surfaces.mid.normals);
  const colors    = buildVertexColors(hemiKey);

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geo.setAttribute('normal',   new THREE.BufferAttribute(normals, 3));
  geo.setAttribute('color',    new THREE.BufferAttribute(colors, 4));
  geo.setIndex(new THREE.BufferAttribute(md.faces, 1));

  const mat = new THREE.MeshPhongMaterial({
    vertexColors: true,
    specular: 0x080808, shininess: 8,
    flatShading: false, side: THREE.DoubleSide,
    transparent: true, opacity: 1.0,
  });
  const mesh = new THREE.Mesh(geo, mat);

  // Wireframe overlay shares the same geometry — toggled with M.
  const wireMat = new THREE.MeshBasicMaterial({
    wireframe: true, color: 0x333333, transparent: true, opacity: 0.15,
  });
  const wire = new THREE.Mesh(geo, wireMat);
  wire.userData.isWireframe = true;
  wire.visible = wireframeVisible;

  return { mesh, wire };
}

// ── Init ─────────────────────────────────────────────────────────────────
function init() {
  const tL = setupScene('container-left', true);
  sceneL = tL.scene; cameraL = tL.camera; rendererL = tL.renderer; controlsL = tL.controls;
  const tR = setupScene('container-right', false);
  sceneR = tR.scene; cameraR = tR.camera; rendererR = tR.renderer; controlsR = tR.controls;

  controlsL.addEventListener('change', () => { lastMovedSide = 'L'; });
  controlsR.addEventListener('change', () => { lastMovedSide = 'R'; });

  currentMeshName = PAYLOAD.maps[0].mesh;
  const builtL = buildMesh('lh');
  const builtR = buildMesh('rh');
  meshL = builtL.mesh; wireL = builtL.wire; meshL.userData.hemiKey = 'lh';
  meshR = builtR.mesh; wireR = builtR.wire; meshR.userData.hemiKey = 'rh';
  sceneL.add(meshL); sceneL.add(wireL);
  sceneR.add(meshR); sceneR.add(wireR);

  window.addEventListener('resize', onResize);
  window.addEventListener('keydown', onKeyDown);
  window.addEventListener('wheel', onWheel, { passive: true });
  window.addEventListener('mousemove', onMouseMove);
  installColorbarDrag();

  document.getElementById('loading').style.display = 'none';

  // Shown even for a single map, so the surface section keeps the same
  // chrome as the rest of the report.
  const navMenu = document.getElementById('nav-menu');
  if (navMenu) {
    PAYLOAD.maps.forEach((mapData, i) => {
      const btn = document.createElement('div');
      btn.className = 'nav-btn';
      btn.textContent = mapData.nav_label || mapData.label || `Map ${i+1}`;
      btn.onclick = () => switchMap(i);
      navMenu.appendChild(btn);
    });
  }

  switchMap(0);
  resetCameras();

  animate();
}

function onResize() {
  const w = window.innerWidth / 2, h = window.innerHeight;
  const dpr = Math.max(window.devicePixelRatio, 2);
  [{c: cameraL, r: rendererL}, {c: cameraR, r: rendererR}].forEach(({c, r}) => {
    c.aspect = w / h; c.updateProjectionMatrix();
    r.setPixelRatio(dpr); r.setSize(w, h);
  });
}

// Drag the colourbar to rescale: up widens the range, down saturates it,
// clamped to RANGE_MIN..RANGE_MAX of the default. Double-click restores it.
function installColorbarDrag() {
  const wrap = document.getElementById('colorbar-wrap');
  if (!wrap) return;
  let startY = 0, startScale = 1;

  function setScale(next) {
    if (next === scaleOf(activeMapIdx)) return;
    rangeScale[scaleGroup[activeMapIdx]] = next;
    drawColorbar();
    if (meshL) recolorMesh('lh', meshL);
    if (meshR) recolorMesh('rh', meshR);
  }

  wrap.addEventListener('pointerdown', (e) => {
    startY = e.clientY;
    startScale = scaleOf(activeMapIdx);
    wrap.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  wrap.addEventListener('pointermove', (e) => {
    if (!wrap.hasPointerCapture(e.pointerId)) return;
    setScale(Math.max(RANGE_MIN, Math.min(RANGE_MAX,
      startScale + (startY - e.clientY) / RANGE_DRAG_PX)));
  });
  wrap.addEventListener('dblclick', () => setScale(1));
  const release = (e) => {
    if (wrap.hasPointerCapture(e.pointerId)) wrap.releasePointerCapture(e.pointerId);
  };
  wrap.addEventListener('pointerup', release);
  wrap.addEventListener('pointercancel', release);
}

function onKeyDown(e) {
  // Single-letter shortcuts must not fire while the reader is typing in the
  // table's filter box.
  const t = e.target;
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;

  const k = e.key;
  if (k === 'ArrowUp')   { cameraL.position.multiplyScalar(0.9); cameraR.position.multiplyScalar(0.9); }
  if (k === 'ArrowDown') { cameraL.position.multiplyScalar(1.1); cameraR.position.multiplyScalar(1.1); }
  if (k === 'ArrowLeft') {
    morphT = Math.min(2, morphT + 0.1);
    applyMorph();
  }
  if (k === 'ArrowRight') {
    morphT = Math.max(0, morphT - 0.1);
    applyMorph();
  }
  if (k === 'l' || k === 'L') viewLocked = !viewLocked;
  if (k === 'r' || k === 'R') {
    resetCameras();
    morphT = 0; applyMorph();
  }
  if (k === 'h' || k === 'H') {
    const modal = document.getElementById('help-modal');
    if (modal) modal.style.display = (modal.style.display === 'flex') ? 'none' : 'flex';
  }
  if (k === 'o' || k === 'O') {
    cortexOpacity = (cortexOpacity >= 0.99) ? REDUCED_OPACITY : 1.0;
    applyOpacity();
  }
  if (k === 'm' || k === 'M') {
    wireframeVisible = !wireframeVisible;
    if (wireL) wireL.visible = wireframeVisible;
    if (wireR) wireR.visible = wireframeVisible;
  }
  if (k === 'q' || k === 'Q') {
    hoverEnabled = !hoverEnabled;
    if (!hoverEnabled) hideTooltip();
  }
  if (k === ']') { switchMap(activeMapIdx + 1); }
  if (k === '[') { switchMap(activeMapIdx - 1); }
  if (k === 'c' || k === 'C') {
    const mapData = PAYLOAD.maps[activeMapIdx];
    if (mapData.cmap_type === 'diverging') {
      const ci = CMAP_CYCLE_DIV.indexOf(currentCmapDiv);
      currentCmapDiv = CMAP_CYCLE_DIV[(ci + 1) % CMAP_CYCLE_DIV.length];
      currentCmap = currentCmapDiv;
    } else {
      const ci = CMAP_CYCLE_POS.indexOf(currentCmapPos);
      currentCmapPos = CMAP_CYCLE_POS[(ci + 1) % CMAP_CYCLE_POS.length];
      currentCmap = currentCmapPos;
    }
    drawColorbar();
    if (meshL) recolorMesh('lh', meshL);
    if (meshR) recolorMesh('rh', meshR);
  }
}

function applyOpacity() {
  [meshL, meshR].forEach(mesh => {
    if (!mesh) return;
    const m = mesh.material;
    m.transparent = cortexOpacity < 1.0;
    m.opacity = cortexOpacity;
    m.depthWrite = cortexOpacity >= 1.0;
    m.needsUpdate = true;
  });
}

// ── Morph (mid ↔ inflated ↔ sphere) ──────────────────────────────────────
function onWheel(e) {
  // Scrolling inside an overlay scrolls that overlay rather than inflating
  // the brain underneath it.
  const target = e.target;
  if (target && target.closest &&
      (target.closest('#tooltip') || target.closest('#table-panel'))) return;
  const delta = Math.sign(e.deltaY) * -0.05;
  const next = Math.max(0, Math.min(2, morphT + delta));
  if (next !== morphT) {
    morphT = next;
    applyMorph();
  }
}

function applyMorph() {
  [meshL, meshR].forEach(mesh => {
    if (!mesh) return;
    const md = activeMesh(mesh.userData.hemiKey);
    let p0, p1, n0, n1, t;
    if (morphT <= 1.0) {
      p0 = md.surfaces.mid.positions;       p1 = md.surfaces.inflated.positions;
      n0 = md.surfaces.mid.normals;         n1 = md.surfaces.inflated.normals;
      t = morphT;
    } else {
      p0 = md.surfaces.inflated.positions;  p1 = md.surfaces.sphere.positions;
      n0 = md.surfaces.inflated.normals;    n1 = md.surfaces.sphere.normals;
      t = morphT - 1.0;
    }
    const pos = mesh.geometry.attributes.position.array;
    const nrm = mesh.geometry.attributes.normal.array;
    const N = pos.length;
    for (let i = 0; i < N; i++) {
      pos[i] = p0[i] * (1 - t) + p1[i] * t;
      nrm[i] = n0[i] * (1 - t) + n1[i] * t;
    }
    mesh.geometry.attributes.position.needsUpdate = true;
    mesh.geometry.attributes.normal.needsUpdate = true;
  });
}

// ── Tooltip helpers ──────────────────────────────────────────────────────
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Decimals scaled to the map's range: 2 suits SUVR and Z, but would quantise
// asymmetry (±0.25) too coarsely.
function fmtVal(v, vmin, vmax) {
  return v.toFixed((vmax - vmin) < 1 ? 3 : 2);
}

function buildHoverHtml(roi, side, vertexIdx) {
  const name = PAYLOAD.roi_names[roi] || '';
  const mapData = PAYLOAD.maps[activeMapIdx];
  const mv = mapData[side === 'R' ? 'rh' : 'lh'];
  let valStr = '';
  if (vertexIdx >= 0 && vertexIdx < mv.length && !isNoDataValue(mv[vertexIdx])) {
    const { vmin, vmax } = mapRange(activeMapIdx);
    valStr = `<div class="tooltip-map-val">${escapeHtml(mapData.cb_label)}: ` +
             `${fmtVal(mv[vertexIdx], vmin, vmax)}</div>`;
  }
  return `<div class="tooltip-header"><strong>${escapeHtml(name)}</strong></div>${valStr}`;
}

// Viewport margins — clear nav-menu (top ~55px) and help-bar (bottom ~35px).
const TIP_MARGIN_TOP    = 60;
const TIP_MARGIN_BOTTOM = 38;
const TIP_MARGIN_SIDE   =  8;

// Hover tooltip: simple cursor offset, no arrow nub.
const TIP_HOVER_OFFSET = 18;
function placeTooltipAtCursor(tooltip, clientX, clientY) {
  const w = tooltip.offsetWidth, h = tooltip.offsetHeight;
  const W = window.innerWidth,   H = window.innerHeight;
  let x = clientX + TIP_HOVER_OFFSET;
  let y = clientY + TIP_HOVER_OFFSET;
  if (x + w > W - TIP_MARGIN_SIDE) x = clientX - TIP_HOVER_OFFSET - w;
  x = Math.max(TIP_MARGIN_SIDE,   Math.min(W - w - TIP_MARGIN_SIDE,   x));
  y = Math.max(TIP_MARGIN_TOP,    Math.min(H - h - TIP_MARGIN_BOTTOM, y));
  tooltip.style.left = x + 'px';
  tooltip.style.top  = y + 'px';
}

function pickRoiAt(clientX, clientY) {
  // Returns { vertexIdx, roi, side } or null. Snaps to whichever of the three
  // face vertices is closest to the hit point; face[0] can be 5-15 mm off.
  const isLeft = clientX < window.innerWidth / 2;
  const rcCamera = isLeft ? cameraL : cameraR;
  const targetMesh = isLeft ? meshL : meshR;
  const containerId = isLeft ? 'container-left' : 'container-right';
  const rect = document.getElementById(containerId).getBoundingClientRect();
  const mx = ((clientX - rect.left) / rect.width) * 2 - 1;
  const my = -((clientY - rect.top) / rect.height) * 2 + 1;
  if (!targetMesh) return null;
  raycaster.setFromCamera(new THREE.Vector2(mx, my), rcCamera);
  const hits = raycaster.intersectObject(targetMesh, true);
  if (hits.length === 0) return null;
  const faceIdx = hits[0].faceIndex;
  if (faceIdx == null) return null;
  const indexAttr = targetMesh.geometry.index;
  const face = [
    indexAttr.array[faceIdx * 3],
    indexAttr.array[faceIdx * 3 + 1],
    indexAttr.array[faceIdx * 3 + 2],
  ];
  const hitLocal = targetMesh.worldToLocal(hits[0].point.clone());
  const posArr = targetMesh.geometry.attributes.position.array;
  let pickedVert = face[0];
  let bestD2 = Infinity;
  for (const vi of face) {
    const dx = posArr[vi*3]   - hitLocal.x;
    const dy = posArr[vi*3+1] - hitLocal.y;
    const dz = posArr[vi*3+2] - hitLocal.z;
    const d2 = dx*dx + dy*dy + dz*dz;
    if (d2 < bestD2) { bestD2 = d2; pickedVert = vi; }
  }
  const md = activeMesh(targetMesh.userData.hemiKey);
  const roi = md.vertex_to_roi[pickedVert];
  if (roi < 0) return null;                  // medial wall / unassigned
  return { vertexIdx: pickedVert, roi: roi, side: isLeft ? 'L' : 'R' };
}

function onMouseMove(e) {
  const tooltip = document.getElementById('tooltip');
  if (!hoverEnabled) return;
  const hit = pickRoiAt(e.clientX, e.clientY);
  if (!hit) { hideTooltip(); return; }
  // Rebuild on every vertex change: the tooltip carries a per-vertex value,
  // so guarding on the parcel would freeze the number.
  if (hit.vertexIdx !== hoveredVertexIdx || hit.side !== hoveredSide) {
    hoveredSide = hit.side;
    hoveredVertexIdx = hit.vertexIdx;
    hoveredRoi = hit.roi;
    tooltip.innerHTML = buildHoverHtml(hit.roi, hit.side, hit.vertexIdx);
  }
  tooltip.style.display = 'block';
  placeTooltipAtCursor(tooltip, e.clientX, e.clientY);
}

function hideTooltip() {
  const tooltip = document.getElementById('tooltip');
  if (tooltip) tooltip.style.display = 'none';
  hoveredSide = null;
  hoveredVertexIdx = -1;
  hoveredRoi = -1;
}

// The axis the locked pair mirrors in: the one their default views oppose each
// other in — x for the lateral cortex views, y for the hippocampal sheets,
// which are seen from opposite sides of their own plane. Reading it off the
// payload keeps a freshly reset pair exactly where resetCameras() put it.
function mirrorSigns() {
  const set = activeMeshSet();
  const a = set.lh.view.eye, b = set.rh.view.eye;
  return [a[0] * b[0] < 0 ? -1 : 1,
          a[1] * b[1] < 0 ? -1 : 1,
          a[2] * b[2] < 0 ? -1 : 1];
}

// ── Animate (with locked camera mirror) ──────────────────────────────────
function animate() {
  requestAnimationFrame(animate);
  if (controlsL) controlsL.update();
  if (controlsR) controlsR.update();

  if (viewLocked && cameraL && cameraR) {
    const s = mirrorSigns();
    if (lastMovedSide === 'L') {
      const p = cameraL.position;
      cameraR.position.set(s[0] * p.x, s[1] * p.y, s[2] * p.z);
      cameraR.up.copy(cameraL.up);
      controlsR.target.set(0, 0, 0); controlsR.update();
    } else {
      const p = cameraR.position;
      cameraL.position.set(s[0] * p.x, s[1] * p.y, s[2] * p.z);
      cameraL.up.copy(cameraR.up);
      controlsL.target.set(0, 0, 0); controlsL.update();
    }
  }

  if (sceneL && cameraL) rendererL.render(sceneL, cameraL);
  if (sceneR && cameraR) rendererR.render(sceneR, cameraR);
}

function snapshotCssPx(value, fallback) {
  const n = Number.parseFloat(value);
  return Number.isFinite(n) ? n : fallback;
}

function snapshotFont(style) {
  const weight = style.fontWeight || '400';
  const size = style.fontSize || '16px';
  const family = style.fontFamily || 'sans-serif';
  return `${weight} ${size} ${family}`;
}

function snapshotRoundedRect(ctx, x, y, w, h, r) {
  if (ctx.roundRect) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
    ctx.fill();
    return;
  }
  ctx.fillRect(x, y, w, h);
}

function drawSnapshotTextElement(ctx, el, fallbackColor) {
  if (!el) return;
  const rect = el.getBoundingClientRect();
  if (!rect.width && !rect.height) return;
  const style = window.getComputedStyle(el);
  const lines = (el.innerText || el.textContent || '').split('\n').filter(Boolean);
  if (lines.length === 0) return;
  const fontSize = snapshotCssPx(style.fontSize, 16);
  const lineHeight = snapshotCssPx(style.lineHeight, fontSize * 1.5);
  ctx.save();
  ctx.font = snapshotFont(style);
  ctx.fillStyle = style.color || fallbackColor || '#64748b';
  ctx.textAlign = style.textAlign === 'center' ? 'center' : 'left';
  ctx.textBaseline = 'top';
  const x = ctx.textAlign === 'center' ? rect.left + rect.width / 2 : rect.left;
  let y = rect.top;
  lines.forEach(line => {
    ctx.fillText(line, x, y);
    y += lineHeight;
  });
  ctx.restore();
}

function drawSnapshotNav(ctx) {
  document.querySelectorAll('#nav-menu .nav-btn').forEach(btn => {
    const rect = btn.getBoundingClientRect();
    const style = window.getComputedStyle(btn);
    const active = btn.classList.contains('active');
    ctx.save();
    if (active) {
      ctx.fillStyle = getComputedStyle(document.documentElement)
        .getPropertyValue('--accent-soft').trim() || '#f4e9f8';
      snapshotRoundedRect(ctx, rect.left, rect.top, rect.width, rect.height, 12);
    }
    ctx.font = snapshotFont(style);
    ctx.fillStyle = active
      ? (getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#470A68')
      : (style.color || '#64748b');
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(btn.textContent || '', rect.left + rect.width / 2, rect.top + rect.height / 2);
    ctx.restore();
  });
}

function drawSnapshotSurfaceOverlays(ctx) {
  drawSnapshotNav(ctx);
  drawSnapshotTextElement(ctx, document.getElementById('map-label-sub'), '#64748b');
  drawSnapshotTextElement(ctx, document.getElementById('colorbar-title'), '#64748b');
  drawSnapshotTextElement(ctx, document.getElementById('cb-max'), '#64748b');
  drawSnapshotTextElement(ctx, document.getElementById('cb-min'), '#64748b');
  const cb = document.getElementById('colorbar-canvas');
  if (cb) {
    const rect = cb.getBoundingClientRect();
    ctx.drawImage(cb, rect.left, rect.top, rect.width, rect.height);
  }
  drawSnapshotTextElement(ctx, document.querySelector('.help-bar span'), '#94a3b8');
}

// Draw the open tooltip onto the snapshot: styled HTML, so it is rasterised
// with html2canvas and pasted at its on-screen position. Best-effort — a
// tooltip failure must not fail the snapshot.
async function drawSnapshotTooltip(ctx) {
  const tip = document.getElementById('tooltip');
  if (!tip || tip.style.display !== 'block') return;
  if (typeof html2canvas !== 'function') return;
  const rect = tip.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  try {
    const tc = await html2canvas(tip, { backgroundColor: null, scale: 2, logging: false });
    ctx.drawImage(tc, rect.left, rect.top, rect.width, rect.height);
  } catch (e) { /* keep the rest of the snapshot */ }
}

async function buildSurfaceSnapshotDataUrl() {
  if (rendererL && sceneL && cameraL) rendererL.render(sceneL, cameraL);
  if (rendererR && sceneR && cameraR) rendererR.render(sceneR, cameraR);

  const dpr = Math.max(window.devicePixelRatio || 1, 2);
  const w = window.innerWidth;
  const h = window.innerHeight;
  const out = document.createElement('canvas');
  out.width = Math.round(w * dpr);
  out.height = Math.round(h * dpr);
  const ctx = out.getContext('2d');
  ctx.scale(dpr, dpr);
  ctx.fillStyle = getComputedStyle(document.body).backgroundColor || '#ffffff';
  ctx.fillRect(0, 0, w, h);
  if (rendererL) ctx.drawImage(rendererL.domElement, 0, 0, w / 2, h);
  if (rendererR) ctx.drawImage(rendererR.domElement, w / 2, 0, w / 2, h);
  drawSnapshotSurfaceOverlays(ctx);
  await drawSnapshotTooltip(ctx);
  return out.toDataURL('image/png');
}

window.petreportSurfaceSnapshot = function() {
  return new Promise(resolve => {
    requestAnimationFrame(() => {
      buildSurfaceSnapshotDataUrl().then(resolve).catch(() => resolve(null));
    });
  });
};

init();
