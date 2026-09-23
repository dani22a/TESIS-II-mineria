/**
 * Procedural meshes, materials and HTML labels for the MineTwin 3D pit.
 */

import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import {
  BlastPatternModel,
  DrillRigTwin,
  GeologicalBlock,
  RoadSegment,
  ShovelTwin,
  TruckTwin,
} from '../types/mining';
import { cycleStateLabel } from '../i18n/labels';

const rockTextureCache = new Map<string, THREE.CanvasTexture>();

export function cycleAccentHex(cycleState: TruckTwin['cycleState'], selected: boolean): number {
  if (selected) return 0xf59e0b;
  switch (cycleState) {
    case 'HAULING':
      return 0x10b981;
    case 'RETURNING':
    case 'EMPTY_TRAVEL':
      return 0x38bdf8;
    case 'LOADING':
    case 'SPOTTING':
      return 0xa855f7;
    case 'QUEUE_SHOVEL':
    case 'QUEUE_DESTINATION':
      return 0xf97316;
    case 'DUMPING':
      return 0xef4444;
    case 'MAINTENANCE':
      return 0xf43f5e;
    default:
      return 0x94a3b8;
  }
}

export function hexToCss(hex: number): string {
  return `#${hex.toString(16).padStart(6, '0')}`;
}

export function createHtmlLabel(
  title: string,
  meta: string | undefined,
  variant: 'asset' | 'zone' | 'bench'
): CSS2DObject {
  const el = document.createElement('div');
  el.className = `twin-label twin-label--${variant}`;
  if (variant === 'asset') {
    el.innerHTML = `<div class="twin-label__title"></div><div class="twin-label__meta"></div>`;
    (el.querySelector('.twin-label__title') as HTMLElement).textContent = title;
    (el.querySelector('.twin-label__meta') as HTMLElement).textContent = meta ?? '';
  } else {
    el.textContent = title;
  }
  const obj = new CSS2DObject(el);
  obj.center.set(0.5, 1);
  return obj;
}

export function updateAssetLabel(
  label: CSS2DObject,
  title: string,
  meta: string,
  selected: boolean,
  accentCss: string
) {
  const el = label.element;
  const titleEl = el.querySelector('.twin-label__title');
  const metaEl = el.querySelector('.twin-label__meta');
  if (titleEl) titleEl.textContent = title;
  if (metaEl) metaEl.textContent = meta;
  el.classList.toggle('twin-label--selected', selected);
  el.style.setProperty('--twin-accent', accentCss);
}

function hash01(i: number, seed: number) {
  return Math.abs(Math.sin(i * 12.9898 + seed * 78.233) * 43758.5453) % 1;
}

function createSoilTexture(palette: string[], seed = 1): THREE.CanvasTexture {
  const key = `${palette.join('|')}:${seed}`;
  const cached = rockTextureCache.get(key);
  if (cached) return cached;

  const size = 512;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = palette[0];
  ctx.fillRect(0, 0, size, size);

  for (let i = 0; i < 90; i++) {
    ctx.globalAlpha = 0.28 + hash01(i, seed) * 0.45;
    ctx.fillStyle = palette[1 + (i % Math.max(1, palette.length - 1))];
    const rx = 18 + hash01(i + 3, seed) * 78;
    ctx.beginPath();
    ctx.ellipse(
      hash01(i + 1, seed) * size,
      hash01(i + 2, seed) * size,
      rx,
      rx * (0.45 + hash01(i + 4, seed) * 0.7),
      hash01(i, seed) * Math.PI,
      0,
      Math.PI * 2
    );
    ctx.fill();
  }

  for (let i = 0; i < 36; i++) {
    ctx.globalAlpha = 0.18;
    ctx.strokeStyle = palette[i % palette.length];
    ctx.lineWidth = 3 + hash01(i, seed + 9) * 10;
    const y = hash01(i, seed + 1) * size;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.bezierCurveTo(size * 0.3, y + 16, size * 0.7, y - 14, size, y + 6);
    ctx.stroke();
  }

  ctx.globalAlpha = 1;
  for (let i = 0; i < 4200; i++) {
    ctx.fillStyle = hash01(i, seed) > 0.55 ? 'rgba(60,30,10,0.16)' : 'rgba(255,255,255,0.12)';
    ctx.fillRect(hash01(i, seed + 2) * size, hash01(i, seed + 3) * size, 1 + hash01(i, 4) * 4, 1 + hash01(i, 5) * 2);
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(3, 3);
  tex.anisotropy = 8;
  tex.colorSpace = THREE.SRGBColorSpace;
  rockTextureCache.set(key, tex);
  return tex;
}

function applySoilVertexColors(geometry: THREE.BufferGeometry, tones: number[], freq = 0.028) {
  const pos = geometry.attributes.position;
  const colors = new Float32Array(pos.count * 3);
  const cA = new THREE.Color(tones[0]);
  const cB = new THREE.Color(tones[1]);
  const cC = new THREE.Color(tones[2] ?? tones[0]);
  const tmp = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    const n1 = 0.5 + 0.5 * Math.sin(x * freq) * Math.cos(z * freq * 0.86);
    const n2 = 0.5 + 0.5 * Math.sin((x + z) * freq * 1.7 + y * 0.12);
    tmp.copy(cA).lerp(cB, n1).lerp(cC, n2 * 0.5);
    colors[i * 3] = tmp.r;
    colors[i * 3 + 1] = tmp.g;
    colors[i * 3 + 2] = tmp.b;
  }
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
}

function createSoilMaterial(palette: string[], seed: number) {
  return new THREE.MeshStandardMaterial({
    map: createSoilTexture(palette, seed),
    color: 0xffffff,
    vertexColors: true,
    roughness: 0.94,
    metalness: 0.03,
    flatShading: true,
  });
}

function placeZoneTag(parent: THREE.Object3D, title: string, x: number, y: number, z: number, variant: 'zone' | 'bench' = 'zone') {
  const tag = createHtmlLabel(title, undefined, variant);
  tag.position.set(x, y, z);
  parent.add(tag);
  return tag;
}

function createOpsCabin(): THREE.Group {
  const group = new THREE.Group();
  const paint = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.42 });
  const steel = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.4, roughness: 0.45 });
  const cabin = new THREE.Mesh(new THREE.BoxGeometry(16, 9, 12), paint);
  cabin.position.y = 5.2;
  cabin.castShadow = true;
  group.add(cabin);
  const roof = new THREE.Mesh(new THREE.BoxGeometry(18, 1, 14), steel);
  roof.position.y = 10;
  group.add(roof);
  const tower = new THREE.Mesh(new THREE.BoxGeometry(4, 14, 4), steel);
  tower.position.set(7, 14, 0);
  group.add(tower);
  const glass = new THREE.Mesh(
    new THREE.BoxGeometry(12, 3.2, 0.3),
    new THREE.MeshStandardMaterial({ color: 0x7dd3fc, emissive: 0x38bdf8, emissiveIntensity: 0.35 })
  );
  glass.position.set(0, 6.4, 6.2);
  group.add(glass);
  return group;
}

function createRoadGantry(): THREE.Group {
  const group = new THREE.Group();
  const yellow = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.4, metalness: 0.2 });
  const steel = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.5, roughness: 0.35 });
  [-11, 11].forEach((x) => {
    const post = new THREE.Mesh(new THREE.BoxGeometry(1.6, 18, 1.6), yellow);
    post.position.set(x, 9, 0);
    post.castShadow = true;
    group.add(post);
  });
  const beam = new THREE.Mesh(new THREE.BoxGeometry(24, 1.8, 1.8), yellow);
  beam.position.y = 18.2;
  group.add(beam);
  const deck = new THREE.Mesh(new THREE.BoxGeometry(26, 0.5, 10), steel);
  deck.position.y = 0.2;
  group.add(deck);
  return group;
}

function createLoadingPad(): THREE.Group {
  const group = new THREE.Group();
  const slab = new THREE.Mesh(
    new THREE.BoxGeometry(34, 0.6, 26),
    new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.8 })
  );
  slab.position.y = 0.3;
  slab.receiveShadow = true;
  group.add(slab);
  const muck = new THREE.Mesh(
    new THREE.SphereGeometry(10, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0x7c3f12, roughness: 0.97, flatShading: true })
  );
  muck.position.set(10, 0.3, 8);
  muck.scale.set(1.3, 0.7, 1.1);
  group.add(muck);
  return group;
}

function roughenRing(geometry: THREE.BufferGeometry, amount: number) {
  const pos = geometry.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    const n = Math.sin(x * 0.07) * Math.cos(z * 0.06) * amount;
    pos.setXYZ(i, x + n, y, z + n * 0.75);
  }
  pos.needsUpdate = true;
  geometry.computeVertexNormals();
}

function createSkyDome(): THREE.Mesh {
  const canvas = document.createElement('canvas');
  canvas.width = 4;
  canvas.height = 256;
  const ctx = canvas.getContext('2d')!;
  const gradient = ctx.createLinearGradient(0, 0, 0, 256);
  gradient.addColorStop(0, '#4fa3dc');
  gradient.addColorStop(0.38, '#7ec4f0');
  gradient.addColorStop(0.7, '#d2e9fb');
  gradient.addColorStop(1, '#f3ead2');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 4, 256);

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  const geo = new THREE.SphereGeometry(1600, 32, 20);
  const mat = new THREE.MeshBasicMaterial({
    map: tex,
    side: THREE.BackSide,
    fog: false,
    depthWrite: false,
  });
  return new THREE.Mesh(geo, mat);
}

function createDistantRidges(): THREE.Group {
  const group = new THREE.Group();
  const ridgeTones = [
    [0xcbb79a, 0xb39b78, 0x8d7d64],
    [0xd4b896, 0xb8875c, 0x9a6a40],
    [0xb7c09a, 0x9aa078, 0x7d8462],
  ];

  for (let i = 0; i < 10; i++) {
    const angle = (i / 10) * Math.PI * 2 + 0.2;
    const radius = 620 + (i % 3) * 40;
    const geo = new THREE.ConeGeometry(70 + (i % 4) * 18, 70 + (i % 5) * 22, 5);
    applySoilVertexColors(geo, ridgeTones[i % ridgeTones.length]);
    const mesh = new THREE.Mesh(
      geo,
      new THREE.MeshStandardMaterial({
        color: 0xffffff,
        vertexColors: true,
        roughness: 1,
        flatShading: true,
      })
    );
    mesh.position.set(Math.cos(angle) * radius, 18, Math.sin(angle) * radius);
    mesh.rotation.y = angle;
    group.add(mesh);
  }
  return group;
}

function createBeltTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 32;
  canvas.height = 256;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = '#1e293b';
  ctx.fillRect(0, 0, 32, 256);
  for (let y = 0; y < 256; y += 28) {
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, y, 32, 8);
    ctx.fillStyle = '#334155';
    ctx.fillRect(4, y + 10, 24, 10);
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(1, 10);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function addInvisibleHitBox(group: THREE.Group, w: number, h: number, d: number, y: number) {
  const geo = new THREE.BoxGeometry(w, h, d);
  const mat = new THREE.MeshBasicMaterial({ visible: false });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.y = y;
  group.add(mesh);
}

export function buildWorld(scene: THREE.Scene) {
  scene.add(createSkyDome());
  scene.add(createSunDisc());
  scene.add(createDistantRidges());
  buildPitBenches(scene);
  return buildProcessingPlant(scene);
}

function createSunDisc(): THREE.Mesh {
  const sun = new THREE.Mesh(
    new THREE.SphereGeometry(28, 16, 16),
    new THREE.MeshBasicMaterial({ color: 0xfff4c2, fog: false })
  );
  sun.position.set(420, 620, 240);
  return sun;
}

function buildPitBenches(scene: THREE.Scene) {
  const holeRadius = 20;
  const desertGeo = new THREE.RingGeometry(358, 720, 96, 8);
  desertGeo.rotateX(-Math.PI / 2);
  applySoilVertexColors(desertGeo, [0xd8c39a, 0xc4a87a, 0xb7c09a]);
  const desert = new THREE.Mesh(
    desertGeo,
    createSoilMaterial(['#d8c39a', '#c4a87a', '#b7c09a', '#e2d0ae', '#9a8b74'], 1)
  );
  desert.position.y = 14.05;
  desert.receiveShadow = true;
  scene.add(desert);

  const benches = [
    {
      innerR: 300,
      outerR: 360,
      y: 14,
      name: 'Banco 4000',
      palette: ['#cbb892', '#b39b78', '#9a8a70', '#ddd0b4', '#8d7d64'],
      tones: [0xcbb892, 0xb39b78, 0x9a8a70],
      wallPalette: ['#a89070', '#8b7358', '#c4a882', '#6e5b45'],
      wallTones: [0xa89070, 0x8b7358, 0x6e5b45],
    },
    {
      innerR: 240,
      outerR: 300,
      y: 10,
      name: 'Banco 3920',
      palette: ['#d2ae78', '#c4965c', '#e6c99a', '#a87c48', '#8f6a3c'],
      tones: [0xd2ae78, 0xc4965c, 0xa87c48],
      wallPalette: ['#b88650', '#9a6a3c', '#d4a86c', '#7a522c'],
      wallTones: [0xb88650, 0x9a6a3c, 0x7a522c],
    },
    {
      innerR: 170,
      outerR: 240,
      y: 5,
      name: 'Banco 3840',
      palette: ['#c47a42', '#a85c2c', '#e09a58', '#8b4518', '#d4894a'],
      tones: [0xc47a42, 0xa85c2c, 0xe09a58],
      wallPalette: ['#9c4e24', '#7a3818', '#c46a38', '#5c2c14'],
      wallTones: [0x9c4e24, 0x7a3818, 0x5c2c14],
    },
    {
      innerR: 100,
      outerR: 170,
      y: 0,
      name: 'Banco 3760',
      palette: ['#b07a48', '#8d5a32', '#d4a06a', '#6e4224', '#c48a54'],
      tones: [0xb07a48, 0x8d5a32, 0xd4a06a],
      wallPalette: ['#8a4e28', '#6a3418', '#b86a3c', '#4a2410'],
      wallTones: [0x8a4e28, 0x6a3418, 0x4a2410],
    },
    {
      innerR: holeRadius,
      outerR: 100,
      y: -4,
      name: 'Fondo 3680',
      palette: ['#cc7a32', '#a85a20', '#e89840', '#7a3c14', '#d48938'],
      tones: [0xcc7a32, 0xa85a20, 0xe89840],
      wallPalette: ['#6a2e12', '#4a1e0c', '#8b3d1c', '#2a1208'],
      wallTones: [0x6a2e12, 0x4a1e0c, 0x8b3d1c],
    },
  ];

  benches.forEach((bench, idx) => {
    const ringGeo = new THREE.RingGeometry(bench.innerR, bench.outerR, 96, 10);
    ringGeo.rotateX(-Math.PI / 2);
    roughenRing(ringGeo, 3.2);
    applySoilVertexColors(ringGeo, bench.tones, 0.032 + idx * 0.004);
    const ringMesh = new THREE.Mesh(ringGeo, createSoilMaterial(bench.palette, idx + 2));
    ringMesh.position.y = bench.y;
    ringMesh.receiveShadow = true;
    scene.add(ringMesh);

    if (bench.innerR > 4) {
      const bermGeo = new THREE.TorusGeometry(bench.innerR + 1.4, 0.85, 8, 80);
      bermGeo.rotateX(-Math.PI / 2);
      const berm = new THREE.Mesh(
        bermGeo,
        new THREE.MeshStandardMaterial({ color: bench.tones[1], roughness: 1 })
      );
      berm.position.y = bench.y + 0.5;
      berm.receiveShadow = true;
      scene.add(berm);
    }

    if (idx < benches.length - 1) {
      const next = benches[idx + 1];
      const wallGeo = new THREE.CylinderGeometry(bench.innerR, next.outerR, Math.max(0.8, bench.y - next.y), 80, 4, true);
      roughenRing(wallGeo, 2.4);
      applySoilVertexColors(wallGeo, bench.wallTones, 0.05);
      const wall = new THREE.Mesh(wallGeo, createSoilMaterial(bench.wallPalette, idx + 8));
      (wall.material as THREE.MeshStandardMaterial).side = THREE.DoubleSide;
      wall.position.y = (bench.y + next.y) / 2;
      wall.receiveShadow = true;
      wall.castShadow = true;
      scene.add(wall);
    }

    const angle = -0.35 + idx * 0.55;
    const bx = Math.cos(angle) * (bench.innerR + 28);
    const bz = Math.sin(angle) * (bench.innerR + 28);
    placeZoneTag(scene, bench.name, bx, bench.y + 14, bz, 'bench');
  });

  const wellDepth = 52;
  const wellGeo = new THREE.CylinderGeometry(holeRadius, 16, wellDepth, 64, 6, true);
  applySoilVertexColors(wellGeo, [0x4a2410, 0x2a1408, 0x6a3214], 0.08);
  const well = new THREE.Mesh(
    wellGeo,
    createSoilMaterial(['#4a2410', '#2a1408', '#6a3214', '#1a0c06', '#8b3d1c'], 20)
  );
  (well.material as THREE.MeshStandardMaterial).side = THREE.DoubleSide;
  well.position.y = -4 - wellDepth / 2;
  well.receiveShadow = true;
  scene.add(well);

  const wellFloorGeo = new THREE.CircleGeometry(16, 48);
  wellFloorGeo.rotateX(-Math.PI / 2);
  applySoilVertexColors(wellFloorGeo, [0x1a0c06, 0x2a1408, 0x3a1c0c], 0.2);
  const wellFloor = new THREE.Mesh(
    wellFloorGeo,
    new THREE.MeshStandardMaterial({ color: 0xffffff, vertexColors: true, roughness: 1 })
  );
  wellFloor.position.y = -4 - wellDepth;
  scene.add(wellFloor);

  const lipGeo = new THREE.TorusGeometry(holeRadius + 1.2, 1.1, 8, 48);
  lipGeo.rotateX(-Math.PI / 2);
  const lip = new THREE.Mesh(lipGeo, new THREE.MeshStandardMaterial({ color: 0x5c2c14, roughness: 1 }));
  lip.position.y = -3.4;
  scene.add(lip);

  const cabin = createOpsCabin();
  cabin.position.set(8, 14, 268);
  scene.add(cabin);
  placeZoneTag(scene, 'Pit vivo', 8, 38, 268);

  const pad = createLoadingPad();
  pad.position.set(52, 5, 102);
  scene.add(pad);
  placeZoneTag(scene, 'Palas', 52, 24, 102);

  const gantry = createRoadGantry();
  gantry.position.set(148, 8, 48);
  gantry.rotation.y = -0.6;
  scene.add(gantry);
  placeZoneTag(scene, 'Caminos de acarreo', 148, 32, 48);

  placeZoneTag(scene, 'Hueco del pit', 0, 10, holeRadius + 8);
}

function buildProcessingPlant(scene: THREE.Scene): THREE.Group {
  const plantGroup = new THREE.Group();
  plantGroup.name = 'processingPlant';

  const concrete = new THREE.MeshStandardMaterial({ color: 0xb7c4d4, roughness: 0.58, metalness: 0.12 });
  const steel = new THREE.MeshStandardMaterial({ color: 0x8b98ab, roughness: 0.4, metalness: 0.4 });
  const accent = new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.32, metalness: 0.35 });
  const roof = new THREE.MeshStandardMaterial({ color: 0x7b8ea6, roughness: 0.5, metalness: 0.18 });

  const crusher = new THREE.Mesh(new THREE.BoxGeometry(32, 22, 38), concrete);
  crusher.position.set(180, 23, -140);
  crusher.castShadow = true;
  crusher.receiveShadow = true;
  crusher.userData = { assetId: 'CR-01', assetType: 'CRUSHER' };
  plantGroup.add(crusher);

  const crusherRoof = new THREE.Mesh(new THREE.BoxGeometry(36, 1.6, 42), roof);
  crusherRoof.position.set(180, 34.4, -140);
  crusherRoof.userData = { assetId: 'CR-01', assetType: 'CRUSHER' };
  plantGroup.add(crusherRoof);

  for (let i = 0; i < 4; i++) {
    const window = new THREE.Mesh(
      new THREE.BoxGeometry(3.2, 2.4, 0.3),
      new THREE.MeshStandardMaterial({ color: 0xfbbf24, emissive: 0xf59e0b, emissiveIntensity: 0.55 })
    );
    window.name = 'crusherWindow';
    window.position.set(166 + i * 7.2, 24, -120.8);
    window.userData = { assetId: 'CR-01', assetType: 'CRUSHER' };
    plantGroup.add(window);
  }

  const hopper = new THREE.Mesh(new THREE.CylinderGeometry(12, 4.2, 12, 16), accent);
  hopper.name = 'crusherHopper';
  hopper.position.set(180, 36, -140);
  hopper.userData = { assetId: 'CR-01', assetType: 'CRUSHER' };
  hopper.castShadow = true;
  plantGroup.add(hopper);

  const mantle = new THREE.Mesh(
    new THREE.ConeGeometry(3.4, 10, 12),
    new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.72, roughness: 0.28 })
  );
  mantle.name = 'crusherMantle';
  mantle.position.set(180, 31.5, -140);
  mantle.userData = { assetId: 'CR-01', assetType: 'CRUSHER' };
  plantGroup.add(mantle);

  const dumpRamp = new THREE.Mesh(new THREE.BoxGeometry(14, 1.6, 28), steel);
  dumpRamp.position.set(160, 20, -140);
  dumpRamp.rotation.z = -0.38;
  dumpRamp.castShadow = true;
  plantGroup.add(dumpRamp);

  const legGeo = new THREE.BoxGeometry(1.4, 16, 1.4);
  [
    [170, 8, -128],
    [190, 8, -128],
    [170, 8, -152],
    [190, 8, -152],
  ].forEach(([x, y, z]) => {
    const leg = new THREE.Mesh(legGeo, steel);
    leg.position.set(x, y, z);
    leg.castShadow = true;
    plantGroup.add(leg);
  });

  const conveyorGroup = new THREE.Group();
  conveyorGroup.name = 'conveyorGroup';
  conveyorGroup.position.set(215, 16, -40);
  conveyorGroup.rotation.set(0.18, -0.45, 0);

  const conveyor = new THREE.Mesh(new THREE.BoxGeometry(6, 1.6, 150), steel);
  conveyor.castShadow = true;
  conveyorGroup.add(conveyor);

  const belt = new THREE.Mesh(
    new THREE.BoxGeometry(4.4, 0.35, 148),
    new THREE.MeshStandardMaterial({ map: createBeltTexture(), roughness: 0.72, metalness: 0.05 })
  );
  belt.name = 'conveyorBelt';
  belt.position.y = 1;
  conveyorGroup.add(belt);
  plantGroup.add(conveyorGroup);

  const stock = new THREE.Mesh(
    new THREE.SphereGeometry(32, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0x92400e, roughness: 0.98, flatShading: true })
  );
  stock.position.set(230, 11, 80);
  stock.scale.set(1.25, 0.85, 1.15);
  stock.castShadow = true;
  stock.receiveShadow = true;
  stock.userData = { assetId: 'SP-01', assetType: 'STOCKPILE' };
  plantGroup.add(stock);

  const dumpMat = new THREE.MeshStandardMaterial({ color: 0x57534e, roughness: 0.96, flatShading: true });
  [22, 16, 11, 7].forEach((h, i) => {
    const terrace = new THREE.Mesh(new THREE.CylinderGeometry(36 - i * 6, 42 - i * 5, h, 12), dumpMat);
    terrace.position.set(-220, 14 + i * 7, -180);
    terrace.castShadow = true;
    terrace.receiveShadow = true;
    plantGroup.add(terrace);
  });

  const mill = new THREE.Mesh(new THREE.BoxGeometry(52, 24, 64), roof);
  mill.position.set(280, 22, -160);
  mill.castShadow = true;
  mill.userData = { assetId: 'ML-01', assetType: 'MILL' };
  plantGroup.add(mill);

  const sag = new THREE.Mesh(
    new THREE.CylinderGeometry(11, 11, 24, 24),
    new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.65, roughness: 0.28 })
  );
  sag.name = 'sagMill';
  sag.rotation.z = Math.PI / 2;
  sag.position.set(262, 18, -160);
  sag.castShadow = true;
  plantGroup.add(sag);

  const stack = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 3.2, 36, 12), steel);
  stack.name = 'millStack';
  stack.position.set(298, 40, -178);
  stack.castShadow = true;
  plantGroup.add(stack);

  const tankMat = new THREE.MeshStandardMaterial({ color: 0xcbd5e1, metalness: 0.45, roughness: 0.35 });
  [0, 16].forEach((ox) => {
    const tank = new THREE.Mesh(new THREE.CylinderGeometry(6, 6, 16, 16), tankMat);
    tank.position.set(304 + ox, 16, -138);
    tank.castShadow = true;
    plantGroup.add(tank);
  });

  placeZoneTag(plantGroup, 'Chancador CR-01', 180, 48, -140);
  placeZoneTag(plantGroup, 'Planta', 280, 50, -160);
  placeZoneTag(plantGroup, 'Acopio ROM', 230, 42, 80);
  placeZoneTag(plantGroup, 'Botadero', -220, 52, -180);

  scene.add(plantGroup);
  return plantGroup;
}

export function createTruckMesh(truck: TruckTwin): THREE.Group {
  const group = new THREE.Group();
  group.userData = { assetId: truck.id, assetType: 'TRUCK' };

  const body = new THREE.Group();
  body.name = 'truckBody';
  group.add(body);

  const chassisMat = new THREE.MeshStandardMaterial({ color: 0x111827, metalness: 0.55, roughness: 0.38 });
  const chassis = new THREE.Mesh(new THREE.BoxGeometry(5.2, 1.5, 10.2), chassisMat);
  chassis.position.y = 1.7;
  chassis.castShadow = true;
  body.add(chassis);

  const bumper = new THREE.Mesh(
    new THREE.BoxGeometry(5.0, 0.8, 0.7),
    new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.4, roughness: 0.5 })
  );
  bumper.position.set(0, 1.5, 5.2);
  body.add(bumper);

  const hood = new THREE.Mesh(
    new THREE.BoxGeometry(3.6, 1.3, 3.2),
    new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.42, metalness: 0.12 })
  );
  hood.position.set(0, 2.85, 3.4);
  hood.castShadow = true;
  body.add(hood);

  const cab = new THREE.Mesh(
    new THREE.BoxGeometry(2.1, 2.0, 2.4),
    new THREE.MeshStandardMaterial({ color: 0xfbbf24, roughness: 0.38 })
  );
  cab.position.set(-1.35, 3.45, 2.5);
  cab.castShadow = true;
  body.add(cab);

  const glass = new THREE.Mesh(
    new THREE.BoxGeometry(1.8, 1.0, 0.15),
    new THREE.MeshStandardMaterial({ color: 0x7dd3fc, roughness: 0.05, metalness: 0.2, transparent: true, opacity: 0.85 })
  );
  glass.position.set(-1.35, 3.65, 3.72);
  body.add(glass);

  const exhaust = new THREE.Mesh(
    new THREE.CylinderGeometry(0.18, 0.22, 2.4, 8),
    new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.8, roughness: 0.25 })
  );
  exhaust.name = 'exhaust';
  exhaust.position.set(1.8, 3.6, 2.8);
  body.add(exhaust);

  [ -1.6, 1.6 ].forEach((x) => {
    const light = new THREE.Mesh(
      new THREE.BoxGeometry(0.55, 0.35, 0.2),
      new THREE.MeshStandardMaterial({ color: 0xfef3c7, emissive: 0xfde68a, emissiveIntensity: 0.9 })
    );
    light.position.set(x, 2.05, 5.45);
    body.add(light);
  });

  const dumpBedGroup = new THREE.Group();
  dumpBedGroup.name = 'dumpBed';
  dumpBedGroup.position.set(0, 2.45, -1.9);

  const bedMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.48, metalness: 0.18 });
  const bed = new THREE.Mesh(new THREE.BoxGeometry(4.8, 0.35, 7.4), bedMat);
  bed.position.set(0, 0.4, 1.7);
  bed.castShadow = true;
  dumpBedGroup.add(bed);

  const wallL = new THREE.Mesh(new THREE.BoxGeometry(0.22, 2.1, 7.4), bedMat);
  wallL.position.set(-2.3, 1.35, 1.7);
  dumpBedGroup.add(wallL);
  const wallR = wallL.clone();
  wallR.position.x = 2.3;
  dumpBedGroup.add(wallR);
  const wallRear = new THREE.Mesh(new THREE.BoxGeometry(4.8, 2.1, 0.22), bedMat);
  wallRear.position.set(0, 1.35, -2.0);
  dumpBedGroup.add(wallRear);

  const oreFill = new THREE.Mesh(
    new THREE.BoxGeometry(4.2, 1.3, 6.4),
    new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.95, flatShading: true })
  );
  oreFill.name = 'oreFill';
  oreFill.position.set(0, 1.2, 1.7);
  dumpBedGroup.add(oreFill);
  group.add(dumpBedGroup);

  const tireGeo = new THREE.CylinderGeometry(1.35, 1.35, 0.95, 18);
  tireGeo.rotateZ(Math.PI / 2);
  const tireMat = new THREE.MeshStandardMaterial({ color: 0x0b1220, roughness: 0.92 });
  const rimMat = new THREE.MeshStandardMaterial({ color: 0xcbd5e1, metalness: 0.7, roughness: 0.3 });
  const tireOffsets = [
    [-2.55, 1.35, 2.7],
    [2.55, 1.35, 2.7],
    [-2.55, 1.35, -1.3],
    [2.55, 1.35, -1.3],
    [-2.55, 1.35, -3.25],
    [2.55, 1.35, -3.25],
  ];
  tireOffsets.forEach(([tx, ty, tz]) => {
    const wheel = new THREE.Group();
    wheel.name = 'wheel';
    wheel.position.set(tx, ty, tz);
    const tire = new THREE.Mesh(tireGeo, tireMat);
    tire.castShadow = true;
    wheel.add(tire);
    const rim = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 1.0, 12), rimMat);
    rim.rotation.z = Math.PI / 2;
    wheel.add(rim);
    group.add(wheel);
  });

  const ringGeo = new THREE.RingGeometry(3.8, 4.7, 32);
  ringGeo.rotateX(-Math.PI / 2);
  const ringMat = new THREE.MeshBasicMaterial({
    color: 0x10b981,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.9,
  });
  const ringMesh = new THREE.Mesh(ringGeo, ringMat);
  ringMesh.name = 'statusRing';
  ringMesh.position.y = 0.12;
  group.add(ringMesh);

  const label = createHtmlLabel(truck.id, cycleStateLabel(truck.cycleState), 'asset');
  label.position.set(0, 9.2, 0);
  label.name = 'assetLabel';
  group.add(label);
  group.userData.label = label;

  addInvisibleHitBox(group, 7, 8, 12, 3.2);
  group.scale.setScalar(1.9);
  return group;
}

export function createShovelMesh(shovel: ShovelTwin): THREE.Group {
  const group = new THREE.Group();
  group.userData = { assetId: shovel.id, assetType: 'SHOVEL' };

  const trackMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.82, metalness: 0.2 });
  const leftTrack = new THREE.Mesh(new THREE.BoxGeometry(3.2, 2.4, 13), trackMat);
  leftTrack.position.set(-4.2, 1.2, 0);
  leftTrack.castShadow = true;
  group.add(leftTrack);
  const rightTrack = leftTrack.clone();
  rightTrack.position.x = 4.2;
  group.add(rightTrack);

  const deck = new THREE.Mesh(
    new THREE.BoxGeometry(10.4, 1.2, 12.4),
    new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.55, metalness: 0.3 })
  );
  deck.position.y = 2.5;
  deck.castShadow = true;
  group.add(deck);

  const upperCab = new THREE.Group();
  upperCab.name = 'upperCab';
  upperCab.position.y = 3.1;

  const house = new THREE.Mesh(
    new THREE.BoxGeometry(9.4, 6.8, 10.5),
    new THREE.MeshStandardMaterial({ color: 0xeab308, roughness: 0.42, metalness: 0.12 })
  );
  house.position.set(0, 3.4, -1.4);
  house.castShadow = true;
  upperCab.add(house);

  const cabGlass = new THREE.Mesh(
    new THREE.BoxGeometry(4.6, 2.2, 0.2),
    new THREE.MeshStandardMaterial({ color: 0x7dd3fc, transparent: true, opacity: 0.8, roughness: 0.1 })
  );
  cabGlass.position.set(0, 4.6, 3.9);
  upperCab.add(cabGlass);

  const boomMat = new THREE.MeshStandardMaterial({ color: 0xca8a04, metalness: 0.45, roughness: 0.35 });
  const stickMat = new THREE.MeshStandardMaterial({ color: 0xa16207, metalness: 0.5, roughness: 0.32 });
  const bucketMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.62, roughness: 0.28 });

  const boomPivot = new THREE.Group();
  boomPivot.name = 'boomPivot';
  boomPivot.position.set(0, 6.6, 1.2);
  boomPivot.rotation.x = -0.42;
  const boom = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.4, 17), boomMat);
  boom.position.set(0, 0, 8.5);
  boom.castShadow = true;
  boomPivot.add(boom);

  const stickPivot = new THREE.Group();
  stickPivot.name = 'stickPivot';
  stickPivot.position.set(0, 0, 16.4);
  stickPivot.rotation.x = 0.55;
  const handle = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.0, 12), stickMat);
  handle.position.set(0, 0, 6);
  handle.castShadow = true;
  stickPivot.add(handle);

  const bucketPivot = new THREE.Group();
  bucketPivot.name = 'bucketPivot';
  bucketPivot.position.set(0, 0, 12);
  const bucket = new THREE.Mesh(new THREE.BoxGeometry(5.2, 3.6, 4.2), bucketMat);
  bucket.position.set(0, -1.1, 1.5);
  bucket.castShadow = true;
  bucketPivot.add(bucket);

  for (let i = -2; i <= 2; i++) {
    const tooth = new THREE.Mesh(
      new THREE.ConeGeometry(0.35, 1.1, 6),
      new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.7 })
    );
    tooth.rotation.x = Math.PI / 2;
    tooth.position.set(i * 0.95, -2.4, 3.4);
    bucketPivot.add(tooth);
  }

  const bucketOre = new THREE.Mesh(
    new THREE.SphereGeometry(2.1, 8, 6),
    new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.97, flatShading: true })
  );
  bucketOre.name = 'bucketOre';
  bucketOre.position.set(0, -0.2, 1.4);
  bucketOre.visible = false;
  bucketPivot.add(bucketOre);

  stickPivot.add(bucketPivot);
  boomPivot.add(stickPivot);
  upperCab.add(boomPivot);

  group.add(upperCab);

  const muck = new THREE.Mesh(
    new THREE.SphereGeometry(13, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0x713f12, roughness: 0.97, flatShading: true })
  );
  muck.position.set(0, 0.2, 20);
  muck.scale.set(1.25, 0.55, 1.1);
  muck.receiveShadow = true;
  group.add(muck);

  const ringGeo = new THREE.RingGeometry(8.5, 10.2, 40);
  ringGeo.rotateX(-Math.PI / 2);
  const ring = new THREE.Mesh(
    ringGeo,
    new THREE.MeshBasicMaterial({ color: 0xf59e0b, side: THREE.DoubleSide, transparent: true, opacity: 0.55 })
  );
  ring.name = 'statusRing';
  ring.position.y = 0.15;
  group.add(ring);

  const shortName = shovel.name.split('(')[0].trim();
  const label = createHtmlLabel(shortName, `${shovel.productivityTph} t/h`, 'asset');
  label.position.set(0, 16.5, 0);
  label.name = 'assetLabel';
  group.add(label);
  group.userData.label = label;

  addInvisibleHitBox(group, 16, 18, 24, 8);
  group.scale.setScalar(2.15);
  return group;
}

export function createDrillMesh(drill: DrillRigTwin): THREE.Group {
  const group = new THREE.Group();
  group.userData = { assetId: drill.id, assetType: 'DRILL' };

  const base = new THREE.Mesh(
    new THREE.BoxGeometry(6.4, 1.8, 8.4),
    new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.7 })
  );
  base.position.y = 0.9;
  base.castShadow = true;
  group.add(base);

  const cab = new THREE.Mesh(
    new THREE.BoxGeometry(3.4, 2.7, 4.2),
    new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.4 })
  );
  cab.position.set(-0.8, 2.9, -1.2);
  cab.castShadow = true;
  group.add(cab);

  const mast = new THREE.Mesh(
    new THREE.BoxGeometry(1.5, 18.4, 1.8),
    new THREE.MeshStandardMaterial({ color: 0xe0f2fe, metalness: 0.62, roughness: 0.28 })
  );
  mast.position.set(0, 10.2, 2.3);
  mast.castShadow = true;
  group.add(mast);

  const rod = new THREE.Mesh(
    new THREE.CylinderGeometry(0.28, 0.28, 14.0, 10),
    new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.85 })
  );
  rod.name = 'drillRod';
  rod.position.set(0, 6.0, 2.3);
  group.add(rod);

  const bit = new THREE.Mesh(
    new THREE.CylinderGeometry(0.55, 0.22, 1.6, 8),
    new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.8, roughness: 0.25 })
  );
  bit.name = 'drillBit';
  bit.position.set(0, -0.4, 2.3);
  group.add(bit);

  const label = createHtmlLabel(drill.id, 'Perforadora', 'asset');
  label.position.set(0, 21, 0);
  label.name = 'assetLabel';
  group.add(label);
  group.userData.label = label;

  addInvisibleHitBox(group, 8, 20, 10, 8);
  group.scale.setScalar(1.7);
  return group;
}

export function createBlastPatternMesh(pattern: BlastPatternModel): THREE.Group {
  const group = new THREE.Group();
  group.userData = { assetId: pattern.id, assetType: 'BLAST' };

  pattern.holes.forEach((hole) => {
    const color = hole.isLoaded ? 0xef4444 : hole.isDrilled ? 0x10b981 : 0xf59e0b;
    const holeMesh = new THREE.Mesh(
      new THREE.CylinderGeometry(0.55, 0.55, 1.6, 10),
      new THREE.MeshBasicMaterial({ color })
    );
    holeMesh.position.set(hole.x, hole.y + 0.85, hole.z);
    group.add(holeMesh);
  });

  return group;
}

export function createBlockModelMesh(blocks: GeologicalBlock[]): THREE.Group {
  const group = new THREE.Group();
  const boxGeo = new THREE.BoxGeometry(12, 5, 12);

  blocks.forEach((block) => {
    if (block.isMined) return;
    let hexColor = 0x64748b;
    if (block.classification === 'ORE') {
      hexColor = block.cuGrade > 1.2 ? 0xa855f7 : block.cuGrade > 0.8 ? 0xef4444 : 0xf59e0b;
    } else if (block.classification === 'LOW_GRADE') {
      hexColor = 0xeab308;
    }
    const mesh = new THREE.Mesh(
      boxGeo,
      new THREE.MeshStandardMaterial({
        color: hexColor,
        transparent: true,
        opacity: 0.62,
        roughness: 0.8,
      })
    );
    mesh.position.set(block.x, block.y + 2.5, block.z);
    mesh.userData = { assetId: block.id, assetType: 'BLOCK' };
    group.add(mesh);
  });

  return group;
}

export function createRoadMesh(road: RoadSegment, isTrafficHeatmap: boolean): THREE.Group {
  const group = new THREE.Group();
  const points = road.waypoints.map((wp) => new THREE.Vector3(wp.x, wp.y + 0.22, wp.z));

  if (points.length >= 2) {
    const curve = new THREE.CatmullRomCurve3(points);

    let color = 0x8b93a1;
    if (isTrafficHeatmap) {
      color = road.currentTrafficCount > 4 ? 0xef4444 : road.currentTrafficCount > 2 ? 0xf59e0b : 0x10b981;
    }

    const roadGeo = new THREE.TubeGeometry(curve, 56, 8.2, 8, false);
    const roadMesh = new THREE.Mesh(
      roadGeo,
      new THREE.MeshStandardMaterial({
        color,
        roughness: 0.88,
        metalness: 0.04,
      })
    );
    roadMesh.receiveShadow = true;
    group.add(roadMesh);

    const lineGeo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(60));
    const line = new THREE.Line(
      lineGeo,
      new THREE.LineDashedMaterial({ color: 0xfacc15, dashSize: 5, gapSize: 3 })
    );
    line.computeLineDistances();
    line.position.y = 0.2;
    group.add(line);
  }

  return group;
}
