/**
 * Process animations for the live 3D twin: load, haul, dump, crush, mill.
 */

import * as THREE from 'three';
import { DigitalTwinState, ShovelTwin, TruckTwin } from '../types/mining';

const TMP = new THREE.Vector3();
const TMP_Q = new THREE.Quaternion();

const DEST = {
  crusher: new THREE.Vector3(180, 34, -140),
  stockpile: new THREE.Vector3(230, 22, 80),
  waste: new THREE.Vector3(-220, 42, -180),
};

export interface ProcessFx {
  dust: ParticlePool;
  ore: ParticlePool;
  smoke: ParticlePool;
  beltOres: THREE.Mesh[];
  clock: number;
}

interface ParticlePool {
  points: THREE.Points;
  positions: Float32Array;
  velocities: Float32Array;
  ages: Float32Array;
  lives: Float32Array;
  count: number;
  cursor: number;
}

function createSoftDot() {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d')!;
  const gradient = ctx.createRadialGradient(32, 32, 1, 32, 32, 30);
  gradient.addColorStop(0, 'rgba(255,255,255,0.95)');
  gradient.addColorStop(0.35, 'rgba(255,255,255,0.45)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 64, 64);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function createPool(
  scene: THREE.Scene,
  count: number,
  color: number,
  size: number,
  opacity: number,
  blending: THREE.Blending = THREE.NormalBlending
): ParticlePool {
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    positions[i * 3 + 1] = -4000;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({
    map: createSoftDot(),
    color,
    size,
    transparent: true,
    opacity,
    depthWrite: false,
    blending,
    sizeAttenuation: true,
  });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  points.renderOrder = 2;
  scene.add(points);
  return {
    points,
    positions,
    velocities: new Float32Array(count * 3),
    ages: new Float32Array(count),
    lives: new Float32Array(count),
    count,
    cursor: 0,
  };
}

function spawn(
  pool: ParticlePool,
  x: number,
  y: number,
  z: number,
  vx: number,
  vy: number,
  vz: number,
  life: number
) {
  const i = pool.cursor % pool.count;
  pool.cursor += 1;
  pool.positions[i * 3] = x;
  pool.positions[i * 3 + 1] = y;
  pool.positions[i * 3 + 2] = z;
  pool.velocities[i * 3] = vx;
  pool.velocities[i * 3 + 1] = vy;
  pool.velocities[i * 3 + 2] = vz;
  pool.ages[i] = 0;
  pool.lives[i] = life;
}

function stepPool(pool: ParticlePool, dt: number, gravity: number, drag: number) {
  const pos = pool.positions;
  const vel = pool.velocities;
  for (let i = 0; i < pool.count; i++) {
    const life = pool.lives[i];
    if (life <= 0) continue;
    pool.ages[i] += dt;
    if (pool.ages[i] >= life || pos[i * 3 + 1] < -80) {
      pool.lives[i] = 0;
      pos[i * 3 + 1] = -4000;
      continue;
    }
    vel[i * 3] *= drag;
    vel[i * 3 + 1] = vel[i * 3 + 1] * drag + gravity * dt;
    vel[i * 3 + 2] *= drag;
    pos[i * 3] += vel[i * 3] * dt;
    pos[i * 3 + 1] += vel[i * 3 + 1] * dt;
    pos[i * 3 + 2] += vel[i * 3 + 2] * dt;
  }
  (pool.points.geometry.getAttribute('position') as THREE.BufferAttribute).needsUpdate = true;
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * THREE.MathUtils.clamp(t, 0, 1);
}

function smooth(t: number) {
  const u = THREE.MathUtils.clamp(t, 0, 1);
  return u * u * (3 - 2 * u);
}

export function createProcessFx(scene: THREE.Scene, plant: THREE.Group | null): ProcessFx {
  const fx: ProcessFx = {
    dust: createPool(scene, 420, 0xc4a574, 4.4, 0.38),
    ore: createPool(scene, 280, 0x7c3f12, 3.6, 0.78),
    smoke: createPool(scene, 220, 0xcbd5e1, 6.5, 0.28, THREE.AdditiveBlending),
    beltOres: [],
    clock: 0,
  };

  const conveyor = plant?.getObjectByName('conveyorGroup') as THREE.Group | undefined;
  if (conveyor) {
    const oreMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.95, flatShading: true });
    for (let i = 0; i < 14; i++) {
      const chunk = new THREE.Mesh(new THREE.DodecahedronGeometry(0.7 + (i % 3) * 0.18, 0), oreMat);
      chunk.name = 'beltOre';
      chunk.userData.t = i / 14;
      chunk.castShadow = true;
      conveyor.add(chunk);
      fx.beltOres.push(chunk);
    }
  }

  return fx;
}

function destinationOf(truck: TruckTwin): THREE.Vector3 {
  if (truck.destinationType === 'STOCKPILE') return DEST.stockpile;
  if (truck.destinationType === 'WASTE_DUMP') return DEST.waste;
  return DEST.crusher;
}

function animateShovel(group: THREE.Group, shovel: ShovelTwin, time: number, fx: ProcessFx) {
  const upper = group.getObjectByName('upperCab');
  const boom = group.getObjectByName('boomPivot');
  const stick = group.getObjectByName('stickPivot');
  const bucket = group.getObjectByName('bucketPivot');
  const ore = group.getObjectByName('bucketOre');
  if (!upper || !boom || !stick || !bucket) return;

  const loading = shovel.operatingState === 'OPERATIONAL' && Boolean(shovel.currentTruckLoadingId);
  const idle = shovel.operatingState !== 'OPERATIONAL';
  const cycle = 8.6;
  const phase = loading ? (time % cycle) / cycle : (time * 0.08) % 1;

  let swing = 0;
  let boomX = -0.42;
  let stickX = 0.55;
  let bucketX = 0.15;
  let showOre = false;

  if (idle) {
    swing = Math.sin(time * 0.15) * 0.08;
  } else if (!loading) {
    swing = Math.sin(time * 0.32) * 0.22;
    boomX = -0.4 + Math.sin(time * 0.21) * 0.06;
  } else if (phase < 0.2) {
    const u = smooth(phase / 0.2);
    swing = lerp(0.7, -0.42, u);
    boomX = lerp(-0.22, -0.92, u);
    stickX = lerp(0.25, 1.05, u);
    bucketX = lerp(0.05, 0.85, u);
  } else if (phase < 0.38) {
    const u = smooth((phase - 0.2) / 0.18);
    swing = -0.42;
    boomX = lerp(-0.92, -0.72, u);
    stickX = lerp(1.05, 0.78, u);
    bucketX = lerp(0.85, -0.55, u);
    showOre = u > 0.35;
    if (u < 0.7) {
      group.getWorldPosition(TMP);
      spawn(
        fx.dust,
        TMP.x + Math.sin(time * 9) * 4,
        TMP.y + 4,
        TMP.z + 18 + Math.cos(time * 7) * 3,
        (Math.random() - 0.5) * 6,
        4 + Math.random() * 6,
        (Math.random() - 0.5) * 6,
        0.7 + Math.random() * 0.5
      );
    }
  } else if (phase < 0.62) {
    const u = smooth((phase - 0.38) / 0.24);
    swing = lerp(-0.42, 0.92, u);
    boomX = lerp(-0.72, -0.18, u);
    stickX = lerp(0.78, 0.28, u);
    bucketX = -0.4;
    showOre = true;
  } else if (phase < 0.8) {
    const u = smooth((phase - 0.62) / 0.18);
    swing = 0.92;
    boomX = -0.12;
    stickX = 0.18;
    bucketX = lerp(-0.4, 1.15, u);
    showOre = u < 0.45;
    if (u > 0.15 && u < 0.7) {
      bucket.getWorldPosition(TMP);
      spawn(
        fx.ore,
        TMP.x + (Math.random() - 0.5) * 2.4,
        TMP.y - 1.2,
        TMP.z + (Math.random() - 0.5) * 2.4,
        (Math.random() - 0.5) * 3,
        -6 - Math.random() * 4,
        (Math.random() - 0.5) * 3,
        0.7
      );
    }
  } else {
    const u = smooth((phase - 0.8) / 0.2);
    swing = lerp(0.92, 0.7, u);
    boomX = lerp(-0.12, -0.22, u);
    stickX = lerp(0.18, 0.25, u);
    bucketX = lerp(1.15, 0.05, u);
  }

  upper.rotation.y = swing;
  boom.rotation.x = boomX;
  stick.rotation.x = stickX;
  bucket.rotation.x = bucketX;
  if (ore) ore.visible = showOre;
}

function animateTruck(group: THREE.Group, truck: TruckTwin, dt: number, time: number, fx: ProcessFx, paused: boolean) {
  const moving =
    !paused &&
    (truck.cycleState === 'HAULING' || truck.cycleState === 'RETURNING' || truck.cycleState === 'EMPTY_TRAVEL');
  const speed = moving ? Math.max(8, truck.speed) : 0;
  const spin = ((speed * 1000) / 3600 / 1.35) * dt;
  if (!group.userData.wheels) {
    const wheels: THREE.Object3D[] = [];
    group.traverse((child) => {
      if (child.name === 'wheel') wheels.push(child);
    });
    group.userData.wheels = wheels;
  }
  (group.userData.wheels as THREE.Object3D[]).forEach((wheel) => {
    wheel.rotation.x += spin;
  });

  const chassis = group.getObjectByName('truckBody');
  if (chassis) {
    chassis.position.y = moving ? Math.sin(time * 18 + truck.id.length) * 0.08 : 0;
  }

  const dumpBed = group.getObjectByName('dumpBed');
  if (dumpBed) {
    const dumping = truck.cycleState === 'DUMPING';
    const raise = dumping ? lerp(0, 1, Math.min(1, truck.routeProgress * 2.2)) : 0;
    dumpBed.rotation.x = THREE.MathUtils.damp(dumpBed.rotation.x, dumping ? -0.72 * raise : 0, 6.5, dt);
  }

  const oreFill = group.getObjectByName('oreFill');
  if (oreFill) {
    const load = truck.payloadCapacity > 0 ? truck.payloadCurrent / truck.payloadCapacity : 0;
    if (truck.cycleState === 'DUMPING') {
      const left = Math.max(0, 1 - truck.routeProgress);
      oreFill.visible = left > 0.08;
      oreFill.scale.set(1, Math.max(0.12, left), 1);
      oreFill.position.y = 0.5 + left * 0.7;
    } else if (truck.cycleState === 'LOADING') {
      oreFill.visible = load > 0.06;
      oreFill.scale.set(1, Math.max(0.12, load), 1);
      oreFill.position.y = 0.5 + load * 0.7;
    } else {
      oreFill.visible = load > 0.08;
      oreFill.scale.set(1, Math.max(0.12, load), 1);
      oreFill.position.y = 0.5 + load * 0.7;
    }
  }

  if (moving && Math.random() < 0.55) {
    TMP.set(0, 0.4, -5.4).applyQuaternion(group.quaternion).add(group.position);
    spawn(
      fx.dust,
      TMP.x + (Math.random() - 0.5) * 2.2,
      TMP.y,
      TMP.z + (Math.random() - 0.5) * 2.2,
      (Math.random() - 0.5) * 2,
      1.2 + Math.random() * 2.4,
      (Math.random() - 0.5) * 2,
      0.55 + Math.random() * 0.4
    );
  }

  if (!paused && truck.engineState !== 'OFF' && Math.random() < 0.22) {
    const exhaust = group.getObjectByName('exhaust');
    if (exhaust) {
      exhaust.getWorldPosition(TMP);
      spawn(
        fx.smoke,
        TMP.x,
        TMP.y + 1.2,
        TMP.z,
        (Math.random() - 0.5) * 0.6,
        2.4 + Math.random() * 1.6,
        (Math.random() - 0.5) * 0.6,
        0.9
      );
    }
  }

  if (!paused && truck.cycleState === 'DUMPING') {
    if (dumpBed) {
      dumpBed.getWorldPosition(TMP);
      dumpBed.getWorldQuaternion(TMP_Q);
      const rear = new THREE.Vector3(0, 1.2, -3.2).applyQuaternion(TMP_Q);
      TMP.add(rear);
    }
    const dest = destinationOf(truck);
    const toward = dest.clone().sub(TMP).normalize();
    spawn(
      fx.ore,
      TMP.x + (Math.random() - 0.5) * 1.6,
      TMP.y,
      TMP.z + (Math.random() - 0.5) * 1.6,
      toward.x * 4 + (Math.random() - 0.5) * 2,
      -8 - Math.random() * 6,
      toward.z * 4 + (Math.random() - 0.5) * 2,
      1.1
    );
    spawn(
      fx.dust,
      TMP.x,
      TMP.y,
      TMP.z,
      (Math.random() - 0.5) * 5,
      3 + Math.random() * 4,
      (Math.random() - 0.5) * 5,
      0.8
    );
  }
}

function animateDrill(group: THREE.Group, time: number, operational: boolean, fx: ProcessFx) {
  const rod = group.getObjectByName('drillRod');
  const bit = group.getObjectByName('drillBit');
  if (rod) {
    const stroke = operational ? 1.15 : 0.15;
    rod.position.y = 6.0 + Math.sin(time * (operational ? 7.2 : 1.2)) * stroke;
  }
  if (bit) {
    bit.rotation.y += operational ? 0.42 : 0.04;
  }
  if (operational) {
    group.getWorldPosition(TMP);
    spawn(
      fx.dust,
      TMP.x + (Math.random() - 0.5) * 1.4,
      TMP.y + 0.6,
      TMP.z + 3.8 + (Math.random() - 0.5),
      (Math.random() - 0.5) * 2,
      3 + Math.random() * 3,
      (Math.random() - 0.5) * 2,
      0.5
    );
  }
}

function animatePlant(plant: THREE.Group, state: DigitalTwinState, dt: number, time: number, fx: ProcessFx, paused: boolean) {
  const mill = plant.getObjectByName('sagMill');
  if (mill) mill.rotation.x += (paused ? 0.35 : 1.6) * dt;

  const mantle = plant.getObjectByName('crusherMantle');
  if (mantle) mantle.rotation.y += (paused ? 0.4 : 2.4) * dt;

  const hopper = plant.getObjectByName('crusherHopper');
  if (hopper) {
    const shake = state.trucks.some((t) => t.cycleState === 'DUMPING' && t.destinationType === 'CRUSHER') ? 0.18 : 0.04;
    hopper.position.x = 180 + Math.sin(time * 28) * shake;
    hopper.position.z = -140 + Math.cos(time * 22) * shake * 0.6;
  }

  plant.traverse((child) => {
    if (child.name === 'crusherWindow' && child instanceof THREE.Mesh) {
      const mat = child.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 0.4 + 0.35 * (0.5 + 0.5 * Math.sin(time * 5 + child.position.x));
    }
  });

  const belt = plant.getObjectByName('conveyorBelt') as THREE.Mesh | undefined;
  if (belt) {
    const mat = belt.material as THREE.MeshStandardMaterial;
    if (mat.map) {
      mat.map.offset.y = (mat.map.offset.y - dt * 0.42) % 1;
    }
  }

  const conveyor = plant.getObjectByName('conveyorGroup');
  fx.beltOres.forEach((chunk) => {
    chunk.userData.t = (chunk.userData.t + dt * 0.085) % 1;
    const t = chunk.userData.t as number;
    chunk.position.set((Math.sin(t * 18) * 0.35), 1.35, -72 + t * 144);
    chunk.rotation.x += dt * 1.8;
    chunk.rotation.z += dt * 1.1;
    chunk.visible = Boolean(conveyor);
  });

  const dumpingAtCrusher = state.trucks.some((t) => t.cycleState === 'DUMPING' && t.destinationType === 'CRUSHER');
  if (dumpingAtCrusher) {
    spawn(
      fx.ore,
      176 + (Math.random() - 0.5) * 6,
      40 + Math.random() * 4,
      -140 + (Math.random() - 0.5) * 6,
      (Math.random() - 0.5) * 2,
      -10 - Math.random() * 6,
      (Math.random() - 0.5) * 2,
      0.9
    );
    spawn(
      fx.dust,
      180,
      38,
      -140,
      (Math.random() - 0.5) * 8,
      6 + Math.random() * 5,
      (Math.random() - 0.5) * 8,
      1.1
    );
  }

  spawn(
    fx.smoke,
    298 + (Math.random() - 0.5) * 1.2,
    58,
    -178 + (Math.random() - 0.5) * 1.2,
    (Math.random() - 0.5) * 0.8,
    5 + Math.random() * 3,
    (Math.random() - 0.5) * 0.8,
    2.4
  );

  if (state.trucks.some((t) => t.cycleState === 'DUMPING' && t.destinationType === 'STOCKPILE')) {
    spawn(
      fx.ore,
      DEST.stockpile.x + (Math.random() - 0.5) * 8,
      DEST.stockpile.y + 10,
      DEST.stockpile.z + (Math.random() - 0.5) * 8,
      (Math.random() - 0.5) * 3,
      -7,
      (Math.random() - 0.5) * 3,
      1
    );
  }
  if (state.trucks.some((t) => t.cycleState === 'DUMPING' && t.destinationType === 'WASTE_DUMP')) {
    spawn(
      fx.dust,
      DEST.waste.x + (Math.random() - 0.5) * 10,
      DEST.waste.y + 6,
      DEST.waste.z + (Math.random() - 0.5) * 10,
      (Math.random() - 0.5) * 6,
      4,
      (Math.random() - 0.5) * 6,
      1.2
    );
  }
}

export function animateProcess(
  fx: ProcessFx,
  dt: number,
  state: DigitalTwinState,
  trucks: Map<string, THREE.Group>,
  shovels: Map<string, THREE.Group>,
  drills: Map<string, THREE.Group>,
  plant: THREE.Group | null
) {
  const paused = state.isPaused || !state.isSimulating;
  const motionDt = paused ? 0 : dt * Math.max(0.35, Math.min(3, state.simSpeedMultiplier || 1));
  if (!paused) fx.clock += motionDt;
  const time = fx.clock;

  state.trucks.forEach((truck) => {
    const group = trucks.get(truck.id);
    if (group && group.visible) animateTruck(group, truck, motionDt, time, fx, paused);
  });

  state.shovels.forEach((shovel) => {
    const group = shovels.get(shovel.id);
    if (group && group.visible) animateShovel(group, shovel, time, fx);
  });

  state.drills.forEach((drill) => {
    const group = drills.get(drill.id);
    if (group && group.visible) {
      animateDrill(group, time, !paused && drill.operatingState === 'OPERATIONAL', fx);
    }
  });

  if (plant) animatePlant(plant, state, paused ? dt * 0.25 : dt, time, fx, paused);

  stepPool(fx.dust, dt, -3.2, 0.96);
  stepPool(fx.ore, dt, -22, 0.99);
  stepPool(fx.smoke, dt, 1.8, 0.985);
}

export function disposeProcessFx(fx: ProcessFx) {
  [fx.dust, fx.ore, fx.smoke].forEach((pool) => {
    pool.points.geometry.dispose();
    const mat = pool.points.material as THREE.PointsMaterial;
    mat.map?.dispose();
    mat.dispose();
    pool.points.parent?.remove(pool.points);
  });
}
