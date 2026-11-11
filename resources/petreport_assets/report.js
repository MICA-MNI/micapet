// Report shell behaviour: canvas scaling, section nav, edit/save, snapshot
// and fullscreen.

function scaleCanvas() {
  const canvas = document.getElementById('report-canvas');
  if (!canvas) return;
  const BASE_W = 1600;
  const BASE_H = 900;
  // Small padding so the canvas does not touch the edge of the screen.
  const availW = window.innerWidth - 32;
  const availH = window.innerHeight - 32;
  const scale = Math.min(availW / BASE_W, availH / BASE_H);
  canvas.style.transform = `scale(${scale})`;
}

const REPORT_EDIT_PASSWORD = {{EDIT_PASSCODE}};

function setEditMode(isEditing) {
  document.body.classList.toggle('edit-mode', isEditing);
  document.body.classList.toggle('view-mode', !isEditing);
  document.querySelectorAll('[contenteditable]').forEach(el => {
    el.setAttribute('contenteditable', isEditing ? 'true' : 'false');
  });
}

function installReportUnlock() {
  const overlay = document.getElementById('unlock-overlay');
  const input = document.getElementById('unlock-input');
  const editBtn = document.getElementById('edit-report-btn');
  
  if (!overlay || !input || !editBtn) return;

  editBtn.addEventListener('click', () => {
    overlay.classList.add('active');
    input.value = '';
    setTimeout(() => input.focus(), 50);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const val = input.value.trim();
      if (val === REPORT_EDIT_PASSWORD) {
        setEditMode(true);
      }
      overlay.classList.remove('active');
    } else if (e.key === 'Escape') {
      e.preventDefault();
      overlay.classList.remove('active');
    }
  });
  
  overlay.addEventListener('mousedown', (e) => {
    if (e.target === overlay) {
      overlay.classList.remove('active');
    }
  });
}

function showSection(name) {
  document.querySelectorAll('.report-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('sec-' + name).classList.add('active');
  document.querySelector('.nav-btn[data-target="' + name + '"]').classList.add('active');
  if (name === 'surface') {
    const frame = document.getElementById('surface-frame');
    if (frame) frame.focus();
  }
}
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => showSection(btn.dataset.target));
});

function clipboardPlainText(e) {
  const data = e.clipboardData || window.clipboardData;
  if (!data) return '';
  const text = data.getData('text/plain');
  if (text) return text;
  const html = data.getData('text/html');
  if (!html) return '';
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  return tmp.innerText || tmp.textContent || '';
}

function installPlainTextPaste() {
  document.addEventListener('paste', (e) => {
    const target = e.target && e.target.closest
      ? e.target.closest('[contenteditable]')
      : null;
    if (!target || target.getAttribute('contenteditable') !== 'true') return;
    e.preventDefault();
    const text = clipboardPlainText(e);
    document.execCommand('insertText', false, text);
  });
}

function saveReport() {
  const clone = document.documentElement.cloneNode(true);
  
  // Drop trailing empty lines and <br>.
  clone.querySelectorAll('.clinical-edit').forEach(el => {
    let html = el.innerHTML;
    html = html.replace(/(<br\s*\/?>|\s|&nbsp;)+$/gi, '');
    html = html.replace(/(<div>(<br\s*\/?>|\s|&nbsp;)*<\/div>)+$/gi, '');
    el.innerHTML = html;
  });

  clone.querySelector('body').classList.remove('edit-mode');
  clone.querySelector('body').classList.add('view-mode');
  clone.querySelectorAll('[contenteditable]').forEach(el => el.setAttribute('contenteditable', 'false'));
  clone.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
  const doc = '<!DOCTYPE html>\n' + clone.outerHTML;
  const blob = new Blob([doc], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const saveBase = "{{SAVE_BASENAME}}";
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const stamp = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
    + `_${pad(d.getHours())}${pad(d.getMinutes())}`;
  a.href = url;
  a.download = saveBase + '_' + stamp + '.html';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function editableRoot(target) {
  return target && target.closest
    ? target.closest('.clinical-edit[contenteditable="true"]')
    : null;
}

function installRichTextEditing() {
  document.addEventListener('keydown', (e) => {
    const el = editableRoot(e.target);
    if (!el) return;
    const mod = e.metaKey || e.ctrlKey;
    if (mod && (e.key === 'b' || e.key === 'B')) {
      e.preventDefault();
      document.body.classList.add('exec-bold-fix');
      void document.body.offsetHeight; // force layout
      document.execCommand('styleWithCSS', false, false);
      document.execCommand('bold', false, null);
      document.body.classList.remove('exec-bold-fix');
      return;
    }
    if (mod && (e.key === 'i' || e.key === 'I')) {
      e.preventDefault();
      document.execCommand('styleWithCSS', false, false);
      document.execCommand('italic', false, null);
      return;
    }
    if (mod && (e.key === '=' || e.key === '+' || e.key === '-' || e.key === '0')) {
      e.preventDefault();
      let currentSize = parseFloat(el.style.fontSize) || 1.0;
      if (e.key === '=' || e.key === '+') currentSize += 0.05;
      if (e.key === '-') currentSize -= 0.05;
      if (e.key === '0') currentSize = 1.0;
      el.style.fontSize = currentSize.toFixed(2) + 'em';
      return;
    }
    if (e.key === ' ') {
      const sel = window.getSelection();
      if (!sel.rangeCount) return;
      const range = sel.getRangeAt(0);
      const node = range.startContainer;
      if (node.nodeType === 3 && node.textContent.slice(0, range.startOffset) === '-') {
        e.preventDefault();
        range.setStart(node, range.startOffset - 1);
        sel.removeAllRanges();
        sel.addRange(range);
        document.execCommand('delete');
        document.execCommand('insertUnorderedList');
      }
    }
  });
}

installPlainTextPaste();
installRichTextEditing();

window.addEventListener('resize', scaleCanvas);
scaleCanvas();
setEditMode(false);
installReportUnlock();
document.getElementById('save-report-btn').addEventListener('click', saveReport);

function getSurfaceSnapshotDataUrl() {
  const surfaceSection = document.getElementById('sec-surface');
  const frame = document.getElementById('surface-frame');
  if (!surfaceSection || !surfaceSection.classList.contains('active') || !frame) {
    return Promise.resolve(null);
  }
  // Reaching into the surface iframe is blocked on a file:// page, where it
  // gets its own origin. Fail soft: the surface area renders blank and the
  // rest of the snapshot still works.
  try {
    const win = frame.contentWindow;
    if (!win || typeof win.petreportSurfaceSnapshot !== 'function') return Promise.resolve(null);
    return Promise.resolve(win.petreportSurfaceSnapshot());
  } catch (e) {
    return Promise.resolve(null);
  }
}

document.getElementById('snapshot-btn').addEventListener('click', async () => {
  try {
    const reportCanvas = document.getElementById('report-canvas');
    if (!reportCanvas) return;
    const surfaceSnapshot = await getSurfaceSnapshotDataUrl();
    const canvas = await html2canvas(reportCanvas, {
      backgroundColor: '#ffffff',
      scale: 2,
      useCORS: true,
      onclone: (doc) => {
        const clonedReportCanvas = doc.getElementById('report-canvas');
        if (clonedReportCanvas) {
          clonedReportCanvas.style.transform = 'none';
          clonedReportCanvas.style.boxShadow = 'none';
        }
        // html2canvas cannot render an iframe, so swap the viewer for the
        // captured image, or a blank placeholder if capture failed.
        const clonedFrame = doc.getElementById('surface-frame');
        if (clonedFrame && clonedFrame.parentNode) {
          let replacement;
          if (surfaceSnapshot) {
            replacement = doc.createElement('img');
            replacement.src = surfaceSnapshot;
            replacement.alt = 'Surface snapshot';
            replacement.style.objectFit = 'cover';
          } else {
            replacement = doc.createElement('div');
          }
          replacement.style.width = '100%';
          replacement.style.height = '100%';
          replacement.style.display = 'block';
          replacement.style.border = '0';
          replacement.style.background = '#ffffff';
          clonedFrame.replaceWith(replacement);
        }
      },
    });
    const link = document.createElement('a');
    const subj = document.querySelector('.report-subject').textContent.trim() || 'report';
    link.download = `report-${subj}-snapshot.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  } catch (e) {
    console.error(e);
    alert("Snapshot failed. See console.");
  }
});

function toggleFullscreen() {
  const el = document.documentElement;
  const fsEl = document.fullscreenElement || document.webkitFullscreenElement;
  if (!fsEl) {
    (el.requestFullscreen || el.webkitRequestFullscreen).call(el);
  } else {
    (document.exitFullscreen || document.webkitExitFullscreen).call(document);
  }
}
document.getElementById('fullscreen-btn').addEventListener('click', toggleFullscreen);
