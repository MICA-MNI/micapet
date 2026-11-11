// Volume section — a 3-view navigator over the sprite sheets rendered by
// petreport.py.
(function () {
const PAYLOAD = window.PETREPORT_VOLUME;
const VIEWS = ['axi', 'sag', 'cor'];

// Per view: the slice axis (sAx), the two in-plane axes (hAx horizontal, vAx
// vertical) and a flip for each. These must stay in lockstep with _tile() in
// petreport.py, or the crosshair lands in the wrong place. hFlip is true for
// axi/cor because those are rendered radiologically; flipping RADIOLOGICAL
// there means flipping them here.
const VIEW_CFG = {
  axi: { sAx: 2, hAx: 0, vAx: 1, hFlip: true, vFlip: true },
  sag: { sAx: 0, hAx: 1, vAx: 2, hFlip: true, vFlip: true },
  cor: { sAx: 1, hAx: 0, vAx: 2, hFlip: true, vFlip: true },
};
const CROSS_HALF = 36, CROSS_GAP = 4;

const dims = PAYLOAD.meta.dims;
const state = { ijk: dims.map(n => Math.floor(n / 2)) };
const V = {};
let pbarImg;

document.addEventListener('DOMContentLoaded', init);
if (document.readyState !== 'loading') init();

function init() {
  if (V.axi) return;                       // idempotent
  pbarImg = document.getElementById('iv-pbar');
  for (const v of VIEWS) V[v] = makeView(v);
  // The tab starts hidden, so its canvases have no layout size until first
  // shown. Re-fit whenever the container gains real dimensions.
  new ResizeObserver(() => { fitAll(); redraw(); })
    .observe(V.axi.canvas.closest('.iv-views'));
  pbarImg.src = 'data:image/webp;base64,' + PAYLOAD.pbar;
}

function makeView(v) {
  const m = PAYLOAD.meta.views[v];
  const canvas = document.getElementById('iv-canvas-' + v);
  const o = {
    canvas, ctx: canvas.getContext('2d'),
    tileW: m.tile_w, tileH: m.tile_h, cols: m.cols, rows: m.rows,
    nSlices: m.n_slices, img: new Image(),
  };
  canvas.width = m.tile_w; canvas.height = m.tile_h;
  o.img.onload = () => { fitAll(); redraw(); };
  o.img.src = 'data:image/webp;base64,' + PAYLOAD.sprites[v];
  bindPointer(v, o);
  canvas.addEventListener('wheel', e => onCanvasWheel(v, e), { passive: false });
  return o;
}

function clampIdx(i, n) { return Math.max(0, Math.min(n - 1, i)); }

// voxel index -> fraction across the tile, at the voxel CENTRE.
function frac(idx, n, flip) {
  const f = (idx + 0.5) / n;
  return flip ? 1 - f : f;
}
function unfrac(f, n, flip) {
  if (flip) f = 1 - f;
  return clampIdx(Math.floor(f * n), n);
}

function fitAll() {
  const container = V['axi'].canvas.closest('.iv-views');
  if (!container) return;
  const availW = container.clientWidth, availH = container.clientHeight;
  if (!availW || !availH) return;

  let totalTileW = 0, maxTileH = 0;
  for (const v of VIEWS) {
    const o = V[v];
    if (!o.tileW || !o.tileH) return;      // not laid out yet
    totalTileW += o.tileW;
    maxTileH = Math.max(maxTileH, o.tileH);
  }

  const GAP = 60;                          // matches the CSS flex gap
  const S_width = Math.max(0, availW - GAP * (VIEWS.length - 1)) / totalTileW;
  const S_height = availH / maxTileH;
  const S = Math.min(S_width, S_height) * 0.90;   // breathing room around the views
  if (!isFinite(S) || S <= 0) return;

  for (const v of VIEWS) {
    const o = V[v];
    o.canvas.style.width = Math.round(o.tileW * S) + 'px';
    o.canvas.style.height = Math.round(o.tileH * S) + 'px';
  }
}

function redraw() {
  for (const v of VIEWS) drawView(v);
}

function drawView(v) {
  const o = V[v], cfg = VIEW_CFG[v];
  if (!o.img.complete || !o.img.naturalWidth) return;
  const slice = clampIdx(state.ijk[cfg.sAx], o.nSlices);
  const r = Math.floor(slice / o.cols), c = slice % o.cols;
  o.ctx.clearRect(0, 0, o.tileW, o.tileH);
  o.ctx.drawImage(o.img, c * o.tileW, r * o.tileH, o.tileW, o.tileH,
                  0, 0, o.tileW, o.tileH);
  drawCrosshair(o, cfg);
}

function drawCrosshair(o, cfg) {
  const px = frac(state.ijk[cfg.hAx], dims[cfg.hAx], cfg.hFlip) * o.tileW;
  const py = frac(state.ijk[cfg.vAx], dims[cfg.vAx], cfg.vFlip) * o.tileH;
  const ctx = o.ctx;
  ctx.shadowBlur = 2;
  ctx.shadowColor = "rgba(255,255,255,0.8)";
  ctx.strokeStyle = '#10b981'; ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(px - CROSS_GAP - CROSS_HALF, py); ctx.lineTo(px - CROSS_GAP, py);
  ctx.moveTo(px + CROSS_GAP, py); ctx.lineTo(px + CROSS_GAP + CROSS_HALF, py);
  ctx.moveTo(px, py - CROSS_GAP - CROSS_HALF); ctx.lineTo(px, py - CROSS_GAP);
  ctx.moveTo(px, py + CROSS_GAP); ctx.lineTo(px, py + CROSS_GAP + CROSS_HALF);
  ctx.stroke();
  ctx.shadowBlur = 0;
}

function bindPointer(v, o) {
  const cfg = VIEW_CFG[v], canvas = o.canvas;
  const apply = (e) => {
    const r = canvas.getBoundingClientRect();
    const fx = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
    const fy = Math.max(0, Math.min(1, (e.clientY - r.top) / r.height));
    state.ijk[cfg.hAx] = unfrac(fx, dims[cfg.hAx], cfg.hFlip);
    state.ijk[cfg.vAx] = unfrac(fy, dims[cfg.vAx], cfg.vFlip);
    redraw();
  };
  canvas.addEventListener('pointerdown', (e) => {
    canvas.setPointerCapture(e.pointerId); apply(e);
  });
  canvas.addEventListener('pointermove', (e) => {
    if (canvas.hasPointerCapture(e.pointerId)) apply(e);
  });
  canvas.addEventListener('pointerup', (e) => canvas.releasePointerCapture(e.pointerId));
  canvas.addEventListener('pointercancel', (e) => canvas.releasePointerCapture(e.pointerId));
}

function onCanvasWheel(v, e) {
  e.preventDefault();
  const ax = VIEW_CFG[v].sAx;
  state.ijk[ax] = clampIdx(state.ijk[ax] + (e.deltaY > 0 ? 1 : -1), dims[ax]);
  redraw();
}

})();
