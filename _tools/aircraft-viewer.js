// Source for assets/js/aircraft-viewer.min.js. Rebuild with:
//   npm install three@0.187.0 esbuild
//   NODE_PATH=node_modules npx esbuild _tools/aircraft-viewer.js --bundle --minify \
//     --format=iife --target=es2019 --outfile=assets/js/aircraft-viewer.min.js
import {
  BufferAttribute,
  BufferGeometry,
  DirectionalLight,
  HemisphereLight,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshStandardMaterial,
  PerspectiveCamera,
  Scene,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const AIRFRAME_COLOR = 0xd9dee5;
const OUTLINE_COLOR = 0x2c333c;
const FIELD_OF_VIEW = 28;
const FRAME_MARGIN = 1.15;

// Azimuth and elevation in degrees. The model keeps OpenVSP axes:
// +X aft, +Y right wing, +Z up, so azimuth 180 looks at the nose.
const VIEWS = {
  perspective: { az: -142, el: 24 },
  top: { az: -90, el: 89.9 },
  side: { az: -90, el: 0 },
  front: { az: 180, el: 0 },
};

const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function decodeModel(meta, buffer) {
  const nv = meta.vertexCount;
  const ni = meta.indexCount;
  const nl = meta.lineIndexCount;
  if (buffer.byteLength !== nv * 12 + ni * 2 + nl * 2) throw new Error('Model file size mismatch');

  let offset = 0;
  const packed = new Uint16Array(buffer, offset, nv * 3);
  offset += nv * 6;
  const normals = new Int16Array(buffer, offset, nv * 3);
  offset += nv * 6;
  const indices = new Uint16Array(buffer, offset, ni);
  offset += ni * 2;
  const lineIndices = new Uint16Array(buffer, offset, nl);

  const { min, max } = meta.bounds;
  const center = [0, 1, 2].map((a) => (min[a] + max[a]) / 2);
  const scale = meta.quantizationSpan / 65535;
  const positions = new Float32Array(nv * 3);
  for (let i = 0; i < nv * 3; i += 3) {
    for (let a = 0; a < 3; a += 1) positions[i + a] = min[a] + packed[i + a] * scale - center[a];
  }

  const size = [max[0] - min[0], max[1] - min[1], max[2] - min[2]].sort((a, b) => b - a);
  const radius = Math.hypot(...size) / 2;
  return { positions, normals, indices, lineIndices, radius, size };
}

function buildScene(meta, model, surfaceButtons) {
  const scene = new Scene();
  scene.add(new HemisphereLight(0xffffff, 0xa4aab3, 2.1));

  const positionAttribute = new BufferAttribute(model.positions, 3);
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', positionAttribute);
  geometry.setAttribute('normal', new BufferAttribute(model.normals, 3, true));
  geometry.setIndex(new BufferAttribute(model.indices, 1));

  const materialFor = (color) => new MeshStandardMaterial({
    color,
    metalness: 0.05,
    roughness: 0.62,
    polygonOffset: true,
    polygonOffsetFactor: 1,
    polygonOffsetUnits: 1,
  });

  const materials = [];
  const surfaceMaterials = {};
  Object.entries(meta.surfaces).forEach(([name, range], i) => {
    const material = materialFor(AIRFRAME_COLOR);
    materials.push(material);
    surfaceMaterials[name] = material;
    geometry.addGroup(range.start, range.count, i);
  });
  surfaceButtons.forEach((button) => {
    surfaceMaterials[button.dataset.surface].color.set(button.dataset.color);
  });
  scene.add(new Mesh(geometry, materials));

  const lines = new BufferGeometry();
  lines.setAttribute('position', positionAttribute);
  lines.setIndex(new BufferAttribute(model.lineIndices, 1));
  scene.add(new LineSegments(lines, new LineBasicMaterial({
    color: OUTLINE_COLOR,
    transparent: true,
    opacity: 0.55,
  })));

  return { scene, surfaceMaterials };
}

async function startViewer(figure) {
  const stage = figure.querySelector('.aircraft-viewer-stage');
  const status = figure.querySelector('.aircraft-viewer-status');
  const controlsPanel = figure.querySelector('.aircraft-viewer-controls');
  const viewButtons = [...figure.querySelectorAll('[data-view]')];
  const surfaceButtons = [...figure.querySelectorAll('[data-surface]')];
  const base = figure.dataset.model;

  const [metaResponse, modelResponse] = await Promise.all([fetch(`${base}.json`), fetch(`${base}.bin`)]);
  if (!metaResponse.ok || !modelResponse.ok) throw new Error('Model files could not be loaded');
  const meta = await metaResponse.json();
  const model = decodeModel(meta, await modelResponse.arrayBuffer());

  const renderer = new WebGLRenderer({ antialias: true, alpha: true });
  const canvas = renderer.domElement;
  canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', 'Rotatable 3D model of the aircraft with its pitch-trim surfaces highlighted');
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  const { scene, surfaceMaterials } = buildScene(meta, model, surfaceButtons);
  const camera = new PerspectiveCamera(FIELD_OF_VIEW, 1.6, 1, model.radius * 12);
  camera.up.set(0, 0, 1);
  const keyLight = new DirectionalLight(0xffffff, 1.5);
  keyLight.position.set(0.3, 0.5, 1);
  camera.add(keyLight);
  camera.add(keyLight.target);
  keyLight.target.position.set(0, 0, -1);
  scene.add(camera);

  const controls = new OrbitControls(camera, canvas);
  controls.enablePan = false;
  controls.enableZoom = false;
  controls.enableDamping = true;
  controls.dampingFactor = 0.12;

  let fittedDistance = 1;
  let zoomed = false;
  let flight = null;
  let frame = 0;

  const placeCamera = (az, el, distance) => {
    const a = az * Math.PI / 180;
    const e = el * Math.PI / 180;
    camera.position.set(
      distance * Math.cos(e) * Math.cos(a),
      distance * Math.cos(e) * Math.sin(a),
      distance * Math.sin(e),
    );
    camera.lookAt(0, 0, 0);
  };

  const cameraAngles = () => {
    const { x, y, z } = camera.position;
    const distance = Math.hypot(x, y, z);
    return { az: Math.atan2(y, x) * 180 / Math.PI, el: Math.asin(z / distance) * 180 / Math.PI, distance };
  };

  const fit = () => {
    const halfVertical = (camera.fov * Math.PI) / 360;
    const halfHorizontal = Math.atan(Math.tan(halfVertical) * camera.aspect);
    // Frame the two longest dimensions, whichever way the camera is pointing.
    fittedDistance = FRAME_MARGIN * Math.max(
      model.size[0] / 2 / Math.tan(halfHorizontal),
      model.size[1] / 2 / Math.tan(halfVertical),
    );
    controls.minDistance = fittedDistance * 0.35;
    controls.maxDistance = fittedDistance * 1.6;
  };

  const tick = (time) => {
    frame = 0;
    if (flight) {
      const t = Math.min((time - flight.start) / flight.duration, 1);
      const ease = t * t * (3 - 2 * t);
      placeCamera(
        flight.from.az + flight.deltaAz * ease,
        flight.from.el + (flight.to.el - flight.from.el) * ease,
        flight.from.distance + (flight.to.distance - flight.from.distance) * ease,
      );
      if (t === 1) flight = null;
    }
    const damping = controls.update();
    renderer.render(scene, camera);
    if (flight || damping) requestRender();
  };

  function requestRender() {
    if (!frame) frame = requestAnimationFrame(tick);
  }

  const resize = () => {
    const { width, height } = stage.getBoundingClientRect();
    if (!width || !height) return;
    const { az, el, distance } = cameraAngles();
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    const previous = fittedDistance;
    fit();
    placeCamera(az, el, zoomed ? distance * fittedDistance / previous : fittedDistance);
    requestRender();
  };

  const setPressed = (activeName) => {
    viewButtons.forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.view === activeName));
    });
  };

  const flyTo = (name) => {
    const to = { ...VIEWS[name], distance: fittedDistance };
    zoomed = false;
    setPressed(name);
    if (reducedMotion()) {
      flight = null;
      placeCamera(to.az, to.el, to.distance);
      requestRender();
      return;
    }
    const from = cameraAngles();
    const deltaAz = ((to.az - from.az + 540) % 360) - 180;
    flight = { from, to, deltaAz, start: performance.now(), duration: 650 };
    requestRender();
  };

  viewButtons.forEach((button) => {
    button.addEventListener('click', () => flyTo(button.dataset.view));
  });

  surfaceButtons.forEach((button) => {
    button.querySelector('.swatch').style.backgroundColor = button.dataset.color;
    button.addEventListener('click', () => {
      const on = button.getAttribute('aria-pressed') !== 'true';
      button.setAttribute('aria-pressed', String(on));
      surfaceMaterials[button.dataset.surface].color.set(on ? button.dataset.color : AIRFRAME_COLOR);
      requestRender();
    });
  });

  controls.addEventListener('change', requestRender);
  controls.addEventListener('start', () => {
    flight = null;
    setPressed('');
  });

  // Scrolling stays with the page until the model has been clicked, so the
  // viewer cannot trap someone reading past it.
  stage.addEventListener('pointerdown', () => { controls.enableZoom = true; }, true);
  stage.addEventListener('pointerleave', () => { controls.enableZoom = false; });
  canvas.addEventListener('wheel', () => {
    if (controls.enableZoom) { zoomed = true; setPressed(''); }
  }, { passive: true });

  stage.appendChild(canvas);
  fit();
  placeCamera(VIEWS.perspective.az, VIEWS.perspective.el, fittedDistance);
  new ResizeObserver(resize).observe(stage);
  resize();
  status.hidden = true;
  controlsPanel.hidden = false;
  requestRender();
}

function initViewer(figure) {
  const showFallback = (error) => {
    console.error('Aircraft viewer:', error);
    figure.querySelector('.aircraft-viewer-status').hidden = true;
    figure.querySelector('.aircraft-viewer-fallback').hidden = false;
    figure.querySelector('figcaption').hidden = true;
  };
  const start = () => startViewer(figure).catch(showFallback);

  if (!('IntersectionObserver' in window)) {
    start();
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      observer.disconnect();
      start();
    }
  }, { rootMargin: '400px' });
  observer.observe(figure);
}

document.querySelectorAll('.aircraft-viewer').forEach(initViewer);
