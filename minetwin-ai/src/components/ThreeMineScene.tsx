/**
 * MineTwin AI - 3D Operational Digital Twin Canvas
 * Open-pit benches, haul fleet, shovels, plant and interactive camera.
 */

import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js';
import { DigitalTwinState } from '../types/mining';
import { cycleStateLabel } from '../i18n/labels';
import {
  buildWorld,
  createBlastPatternMesh,
  createBlockModelMesh,
  createDrillMesh,
  createRoadMesh,
  createShovelMesh,
  createTruckMesh,
  cycleAccentHex,
  hexToCss,
  updateAssetLabel,
} from './mineSceneBuilders';
import { animateProcess, createProcessFx, disposeProcessFx, ProcessFx } from './mineSceneAnimations';

interface ThreeMineSceneProps {
  state: DigitalTwinState;
  onSelectAsset: (id: string, type: 'TRUCK' | 'SHOVEL' | 'DRILL' | 'BLAST' | 'CRUSHER' | 'BLOCK' | 'ROAD') => void;
}

export const ThreeMineScene: React.FC<ThreeMineSceneProps> = ({ state, onSelectAsset }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const labelMountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const labelRendererRef = useRef<CSS2DRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const plantGroupRef = useRef<THREE.Group | null>(null);
  const onSelectAssetRef = useRef(onSelectAsset);
  const selectedIdRef = useRef<string | null>(state.selectedAssetId);

  const truckMeshesRef = useRef<Map<string, THREE.Group>>(new Map());
  const shovelMeshesRef = useRef<Map<string, THREE.Group>>(new Map());
  const drillMeshesRef = useRef<Map<string, THREE.Group>>(new Map());
  const blockMeshesGroupRef = useRef<THREE.Group | null>(null);
  const blastMeshesGroupRef = useRef<THREE.Group | null>(null);
  const roadLinesGroupRef = useRef<THREE.Group | null>(null);
  const lastRoadKeyRef = useRef('');
  const lastBlastKeyRef = useRef('');
  const lastBlockKeyRef = useRef('');
  const lastAppliedFocusRef = useRef(state.cameraFocus);
  const stateRef = useRef(state);
  const processFxRef = useRef<ProcessFx | null>(null);

  const isDraggingRef = useRef(false);
  const dragModeRef = useRef<'orbit' | 'pan' | null>(null);
  const previousMousePositionRef = useRef({ x: 0, y: 0 });
  const mouseDownPosRef = useRef({ x: 0, y: 0 });
  const cameraTargetRef = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0));
  const cameraDistanceRef = useRef(380);
  const cameraAngleThetaRef = useRef(Math.PI / 4);
  const cameraAnglePhiRef = useRef(Math.PI / 3.5);
  const keysRef = useRef({
    w: false,
    a: false,
    s: false,
    d: false,
    q: false,
    e: false,
    shift: false,
  });

  onSelectAssetRef.current = onSelectAsset;
  selectedIdRef.current = state.selectedAssetId;
  stateRef.current = state;

  useEffect(() => {
    const container = mountRef.current;
    const labelContainer = labelMountRef.current;
    if (!container || !labelContainer) return;

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x9ec9ef);
    scene.fog = new THREE.Fog(0xd7e7f4, 620, 1900);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(46, width / height, 1, 3200);
    camera.position.set(220, 240, 280);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.55;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(0x9ec9ef, 1);
    renderer.domElement.style.display = 'block';
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    container.replaceChildren(renderer.domElement);
    rendererRef.current = renderer;

    const labelRenderer = new CSS2DRenderer();
    labelRenderer.setSize(width, height);
    labelRenderer.domElement.style.position = 'absolute';
    labelRenderer.domElement.style.inset = '0';
    labelRenderer.domElement.style.pointerEvents = 'none';
    labelContainer.replaceChildren(labelRenderer.domElement);
    labelRendererRef.current = labelRenderer;

    scene.add(new THREE.AmbientLight(0xfff7ea, 1.25));
    const sunLight = new THREE.DirectionalLight(0xfff4d2, 2.35);
    sunLight.position.set(320, 520, 180);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.set(2048, 2048);
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 1200;
    const d = 420;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    sunLight.shadow.bias = -0.00018;
    sunLight.shadow.normalBias = 0.04;
    scene.add(sunLight);
    scene.add(new THREE.HemisphereLight(0xd8ecff, 0xe2c89a, 0.95));
    const fill = new THREE.DirectionalLight(0xffffff, 0.65);
    fill.position.set(-260, 220, -180);
    scene.add(fill);

    plantGroupRef.current = buildWorld(scene);
    processFxRef.current = createProcessFx(scene, plantGroupRef.current);

    const roadsGroup = new THREE.Group();
    scene.add(roadsGroup);
    roadLinesGroupRef.current = roadsGroup;

    const blocksGroup = new THREE.Group();
    scene.add(blocksGroup);
    blockMeshesGroupRef.current = blocksGroup;

    const blastGroup = new THREE.Group();
    scene.add(blastGroup);
    blastMeshesGroupRef.current = blastGroup;

    const panTarget = (alongRight: number, alongForward: number, alongUp = 0) => {
      const cam = cameraRef.current;
      const target = cameraTargetRef.current;
      if (!cam) return;
      const forward = new THREE.Vector3();
      cam.getWorldDirection(forward);
      forward.y = 0;
      if (forward.lengthSq() < 0.0001) {
        const theta = cameraAngleThetaRef.current;
        forward.set(Math.sin(theta), 0, Math.cos(theta));
      } else {
        forward.normalize();
      }
      const right = new THREE.Vector3(forward.z, 0, -forward.x);
      target.addScaledVector(right, alongRight);
      target.addScaledVector(forward, alongForward);
      target.y += alongUp;
      target.x = THREE.MathUtils.clamp(target.x, -520, 520);
      target.y = THREE.MathUtils.clamp(target.y, -50, 140);
      target.z = THREE.MathUtils.clamp(target.z, -520, 520);
    };

    const handleMouseDown = (e: MouseEvent) => {
      if (e.button === 1) e.preventDefault();
      isDraggingRef.current = true;
      previousMousePositionRef.current = { x: e.clientX, y: e.clientY };
      mouseDownPosRef.current = { x: e.clientX, y: e.clientY };
      if (e.button === 1 || e.button === 2 || (e.button === 0 && e.shiftKey)) {
        dragModeRef.current = 'pan';
        renderer.domElement.style.cursor = 'grabbing';
      } else if (e.button === 0) {
        dragModeRef.current = 'orbit';
        renderer.domElement.style.cursor = 'grabbing';
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current || !dragModeRef.current) return;
      const deltaX = e.clientX - previousMousePositionRef.current.x;
      const deltaY = e.clientY - previousMousePositionRef.current.y;
      const panScale = cameraDistanceRef.current * 0.0024;

      if (dragModeRef.current === 'orbit') {
        cameraAngleThetaRef.current -= deltaX * 0.005;
        cameraAnglePhiRef.current = Math.max(0.08, Math.min(Math.PI / 2.05, cameraAnglePhiRef.current - deltaY * 0.005));
      } else {
        panTarget(-deltaX * panScale, deltaY * panScale);
      }

      previousMousePositionRef.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseUp = () => {
      isDraggingRef.current = false;
      dragModeRef.current = null;
      renderer.domElement.style.cursor = 'grab';
    };

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      cameraDistanceRef.current = Math.max(28, Math.min(900, cameraDistanceRef.current + e.deltaY * 0.35));
    };

    const isTypingTarget = (el: EventTarget | null) => {
      if (!(el instanceof HTMLElement)) return false;
      const tag = el.tagName;
      return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return;
      const key = e.key.toLowerCase();
      const keys = keysRef.current;
      if (key === 'w' || key === 'arrowup') keys.w = true;
      if (key === 'a' || key === 'arrowleft') keys.a = true;
      if (key === 's' || key === 'arrowdown') keys.s = true;
      if (key === 'd' || key === 'arrowright') keys.d = true;
      if (key === 'q') keys.q = true;
      if (key === 'e') keys.e = true;
      if (e.key === 'Shift') keys.shift = true;
      if (['w', 'a', 's', 'd', 'q', 'e', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) {
        e.preventDefault();
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      const keys = keysRef.current;
      if (key === 'w' || key === 'arrowup') keys.w = false;
      if (key === 'a' || key === 'arrowleft') keys.a = false;
      if (key === 's' || key === 'arrowdown') keys.s = false;
      if (key === 'd' || key === 'arrowright') keys.d = false;
      if (key === 'q') keys.q = false;
      if (key === 'e') keys.e = false;
      if (e.key === 'Shift') keys.shift = false;
    };

    const handleContextMenu = (e: MouseEvent) => e.preventDefault();

    const handleClick = (e: MouseEvent) => {
      if (Math.hypot(e.clientX - mouseDownPosRef.current.x, e.clientY - mouseDownPosRef.current.y) > 6) return;
      const rect = renderer.domElement.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);

      const pickables: THREE.Object3D[] = [];
      truckMeshesRef.current.forEach((grp) => pickables.push(grp));
      shovelMeshesRef.current.forEach((grp) => pickables.push(grp));
      drillMeshesRef.current.forEach((grp) => pickables.push(grp));
      if (plantGroupRef.current) pickables.push(plantGroupRef.current);

      const intersects = raycaster.intersectObjects(pickables, true);
      if (intersects.length > 0) {
        let current: THREE.Object3D | null = intersects[0].object;
        while (current && !current.userData?.assetId && current.parent) {
          current = current.parent;
        }
        if (current && current.userData?.assetId) {
          onSelectAssetRef.current(current.userData.assetId, current.userData.assetType);
        }
      }
    };

    const domElem = renderer.domElement;
    domElem.style.cursor = 'grab';
    domElem.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    domElem.addEventListener('wheel', handleWheel, { passive: false });
    domElem.addEventListener('contextmenu', handleContextMenu);
    domElem.addEventListener('click', handleClick);

    const handleResize = () => {
      if (!container || !rendererRef.current || !cameraRef.current || !labelRendererRef.current) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
      labelRendererRef.current.setSize(w, h);
    };
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    let animationFrameId: number;
    let lastTick = performance.now();
    const renderLoop = () => {
      animationFrameId = requestAnimationFrame(renderLoop);
      const now = performance.now();
      const dt = Math.min(0.05, (now - lastTick) / 1000);
      lastTick = now;
      const cam = cameraRef.current;
      if (cam) {
        const keys = keysRef.current;
        if (keys.w || keys.a || keys.s || keys.d || keys.q || keys.e) {
          const speed = cameraDistanceRef.current * (keys.shift ? 1.8 : 0.85);
          const step = speed * dt;
          panTarget(
            (Number(keys.d) - Number(keys.a)) * step,
            (Number(keys.w) - Number(keys.s)) * step,
            (Number(keys.e) - Number(keys.q)) * step * 0.7
          );
        }

        const theta = cameraAngleThetaRef.current;
        const phi = cameraAnglePhiRef.current;
        const r = cameraDistanceRef.current;
        const target = cameraTargetRef.current;
        cam.position.x = target.x + r * Math.sin(phi) * Math.sin(theta);
        cam.position.y = target.y + r * Math.cos(phi);
        cam.position.z = target.z + r * Math.sin(phi) * Math.cos(theta);
        cam.lookAt(target);

        const pulse = 1 + Math.sin(performance.now() * 0.004) * 0.08;
        const applyPulse = (grp: THREE.Group) => {
          const halo = grp.getObjectByName('statusRing');
          if (!halo) return;
          if (grp.userData.assetId === selectedIdRef.current) {
            halo.scale.set(pulse, 1, pulse);
          }
        };
        truckMeshesRef.current.forEach(applyPulse);
        shovelMeshesRef.current.forEach(applyPulse);

        const hideFarLabels = (grp: THREE.Group, nearLimit: number) => {
          const label = grp.getObjectByName('assetLabel');
          if (!label) return;
          const selected = grp.userData.assetId === selectedIdRef.current;
          const dist = cam.position.distanceTo(grp.position);
          label.visible = grp.visible && (selected || dist < nearLimit);
        };
        truckMeshesRef.current.forEach((grp) => hideFarLabels(grp, 820));
        shovelMeshesRef.current.forEach((grp) => hideFarLabels(grp, 820));
        drillMeshesRef.current.forEach((grp) => hideFarLabels(grp, 820));

        if (processFxRef.current) {
          animateProcess(
            processFxRef.current,
            dt,
            stateRef.current,
            truckMeshesRef.current,
            shovelMeshesRef.current,
            drillMeshesRef.current,
            plantGroupRef.current
          );
        }
      }

      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
        labelRendererRef.current?.render(sceneRef.current, cameraRef.current);
      }
    };
    renderLoop();

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      domElem.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      domElem.removeEventListener('wheel', handleWheel);
      domElem.removeEventListener('contextmenu', handleContextMenu);
      domElem.removeEventListener('click', handleClick);
      renderer.dispose();
      labelRenderer.domElement.remove();
      if (processFxRef.current) {
        disposeProcessFx(processFxRef.current);
        processFxRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    if (state.cameraFocus !== lastAppliedFocusRef.current) {
      lastAppliedFocusRef.current = state.cameraFocus;
      if (state.cameraFocus === 'SHOVEL_1') {
        cameraTargetRef.current.set(45, 4.8, 90);
        cameraDistanceRef.current = 140;
      } else if (state.cameraFocus === 'SHOVEL_2') {
        cameraTargetRef.current.set(-25, -2.4, -15);
        cameraDistanceRef.current = 130;
      } else if (state.cameraFocus === 'CRUSHER') {
        cameraTargetRef.current.set(180, 12, -140);
        cameraDistanceRef.current = 120;
      } else if (state.cameraFocus === 'DRILL_PAD') {
        cameraTargetRef.current.set(85, 5.0, 60);
        cameraDistanceRef.current = 110;
      } else if (state.cameraFocus === 'GLOBAL_PIT') {
        cameraTargetRef.current.set(0, 0, 0);
        cameraDistanceRef.current = 380;
      }
    }

    state.trucks.forEach((truck) => {
      let truckGroup = truckMeshesRef.current.get(truck.id);
      if (!truckGroup) {
        truckGroup = createTruckMesh(truck);
        scene.add(truckGroup);
        truckMeshesRef.current.set(truck.id, truckGroup);
      }

      truckGroup.position.set(truck.position.x, truck.position.y + 1.2, truck.position.z);
      truckGroup.rotation.y = (truck.heading * Math.PI) / 180;
      truckGroup.visible = state.visibleLayers.equipment;

      const selected = truck.id === state.selectedAssetId;
      const accent = cycleAccentHex(truck.cycleState, selected);
      const halo = truckGroup.getObjectByName('statusRing') as THREE.Mesh | undefined;
      if (halo && halo.material) {
        const mat = halo.material as THREE.MeshBasicMaterial;
        mat.color.setHex(accent);
        if (!selected) halo.scale.set(1, 1, 1);
      }

      const label = truckGroup.userData.label;
      if (label) {
        updateAssetLabel(
          label,
          truck.id,
          `${cycleStateLabel(truck.cycleState)} · ${Math.round(truck.speed)} km/h`,
          selected,
          hexToCss(accent)
        );
      }

      if (state.cameraFocus === 'CHASE_TRUCK' && state.chaseTruckId === truck.id) {
        cameraTargetRef.current.copy(truckGroup.position);
      }
    });

    state.shovels.forEach((shovel) => {
      let shovelGroup = shovelMeshesRef.current.get(shovel.id);
      if (!shovelGroup) {
        shovelGroup = createShovelMesh(shovel);
        scene.add(shovelGroup);
        shovelMeshesRef.current.set(shovel.id, shovelGroup);
      }
      shovelGroup.position.set(shovel.position.x, shovel.position.y + 1.5, shovel.position.z);
      shovelGroup.visible = state.visibleLayers.equipment;

      const selected = shovel.id === state.selectedAssetId;
      const halo = shovelGroup.getObjectByName('statusRing') as THREE.Mesh | undefined;
      if (halo && halo.material) {
        const mat = halo.material as THREE.MeshBasicMaterial;
        mat.color.setHex(selected ? 0xf59e0b : 0xfacc15);
        mat.opacity = selected ? 0.9 : 0.5;
      }
      const label = shovelGroup.userData.label;
      if (label) {
        const queue = shovel.truckQueue.length;
        updateAssetLabel(
          label,
          shovel.name.split('(')[0].trim(),
          `${shovel.productivityTph} t/h · cola ${queue}`,
          selected,
          selected ? '#f59e0b' : '#facc15'
        );
      }
    });

    state.drills.forEach((drill) => {
      let drillGroup = drillMeshesRef.current.get(drill.id);
      if (!drillGroup) {
        drillGroup = createDrillMesh(drill);
        scene.add(drillGroup);
        drillMeshesRef.current.set(drill.id, drillGroup);
      }
      drillGroup.position.set(drill.position.x, drill.position.y + 1.2, drill.position.z);
      drillGroup.visible = state.visibleLayers.equipment;
      const label = drillGroup.userData.label;
      if (label) {
        updateAssetLabel(
          label,
          drill.id,
          `Perforadora · ${drill.drilledHolesCount}/${drill.totalHolesInPattern}`,
          drill.id === state.selectedAssetId,
          '#38bdf8'
        );
      }
    });

    if (blastMeshesGroupRef.current) {
      const blastKey = `${state.visibleLayers.blastPatterns}:${state.blastPatterns.map((p) => p.id + p.status).join('|')}`;
      if (blastKey !== lastBlastKeyRef.current) {
        lastBlastKeyRef.current = blastKey;
        blastMeshesGroupRef.current.clear();
        if (state.visibleLayers.blastPatterns) {
          state.blastPatterns.forEach((pattern) => {
            blastMeshesGroupRef.current?.add(createBlastPatternMesh(pattern));
          });
        }
      }
    }

    if (blockMeshesGroupRef.current) {
      const blockKey = `${state.visibleLayers.blockModelGeology}:${state.blocks.length}`;
      if (blockKey !== lastBlockKeyRef.current) {
        lastBlockKeyRef.current = blockKey;
        blockMeshesGroupRef.current.clear();
        if (state.visibleLayers.blockModelGeology) {
          blockMeshesGroupRef.current.add(createBlockModelMesh(state.blocks));
        }
      }
    }

    if (roadLinesGroupRef.current) {
      const roadKey = `${state.visibleLayers.haulRoads}:${state.visibleLayers.trafficHeatmap}:${state.roads.map((r) => r.currentTrafficCount).join(',')}`;
      if (roadKey !== lastRoadKeyRef.current) {
        lastRoadKeyRef.current = roadKey;
        roadLinesGroupRef.current.clear();
        if (state.visibleLayers.haulRoads) {
          state.roads.forEach((road) => {
            roadLinesGroupRef.current?.add(createRoadMesh(road, state.visibleLayers.trafficHeatmap));
          });
        }
      }
    }
  }, [state]);

  const lookAt = (x: number, y: number, z: number, distance: number, theta?: number, phi?: number) => {
    cameraTargetRef.current.set(x, y, z);
    cameraDistanceRef.current = distance;
    if (theta !== undefined) cameraAngleThetaRef.current = theta;
    if (phi !== undefined) cameraAnglePhiRef.current = phi;
  };

  return (
    <div className="relative w-full h-full select-none overflow-hidden">
      <div className="absolute inset-0" ref={mountRef} />
      <div className="absolute inset-0 z-[1] pointer-events-none" ref={labelMountRef} />

      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2 max-w-[min(100%,42rem)]">
        <div className="flex flex-wrap items-center gap-2 bg-slate-900/82 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-700/60 shadow-xl text-xs">
          <span className="inline-flex items-center gap-1.5 text-emerald-300 font-bold uppercase tracking-wider text-[10px] mr-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Estado vivo
          </span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400 font-semibold uppercase tracking-wider text-[10px]">Cámaras</span>
          <button
            onClick={() => lookAt(0, 0, 0, 380, Math.PI / 4, Math.PI / 3.5)}
            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-md font-medium transition border border-slate-700"
          >
            Pit general
          </button>
          <button
            onClick={() => lookAt(45, 4.8, 90, 130)}
            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-md font-medium transition border border-slate-700"
          >
            Pala EX-01
          </button>
          <button
            onClick={() => lookAt(-25, -2.4, -15, 120)}
            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-md font-medium transition border border-slate-700"
          >
            Pala EX-02
          </button>
          <button
            onClick={() => lookAt(180, 12, -140, 110)}
            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-sky-300 rounded-md font-medium transition border border-slate-700"
          >
            Chancador
          </button>
          <button
            onClick={() => lookAt(85, 5.0, 60, 100)}
            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-emerald-300 rounded-md font-medium transition border border-slate-700"
          >
            Tronadura
          </button>
        </div>
        <div className="bg-slate-900/84 backdrop-blur-md px-3 py-2.5 rounded-xl border border-slate-700/60 shadow-xl text-[11px] text-slate-300 space-y-1.5 w-fit">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Cómo leer el mapa</div>
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            <LegendDot color="bg-emerald-400" label="Acarreo cargado" />
            <LegendDot color="bg-sky-400" label="Vacío / retorno" />
            <LegendDot color="bg-violet-400" label="En carga" />
            <LegendDot color="bg-orange-400" label="En cola" />
            <LegendDot color="bg-rose-400" label="Descarga" />
            <LegendDot color="bg-amber-400" label="Seleccionado" />
          </div>
        </div>
      </div>

      <div className="absolute bottom-4 right-4 z-10 bg-slate-900/84 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-700/60 shadow-xl text-[11px] text-slate-400 flex flex-wrap items-center gap-x-3 gap-y-1 max-w-md">
        <span>Click izq: orbitar</span>
        <span>Click der / rueda: desplazar</span>
        <span>WASD: mover</span>
        <span>Q / E: subir y bajar</span>
        <span>Rueda: zoom</span>
        <span>Click: inspeccionar</span>
      </div>
    </div>
  );
};

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`w-2 h-2 rounded-full ${color}`} />
      {label}
    </span>
  );
}
