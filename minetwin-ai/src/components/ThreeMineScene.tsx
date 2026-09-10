/**
 * MineTwin AI - 3D Operational Digital Twin Canvas
 * Rendered using Three.js with realistic open-pit benches, animated haul truck fleets,
 * electric rope shovels, drill rigs, blast patterns, voxel block model, and interactive camera.
 */

import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { DigitalTwinState } from '../types/mining';

interface ThreeMineSceneProps {
  state: DigitalTwinState;
  onSelectAsset: (id: string, type: 'TRUCK' | 'SHOVEL' | 'DRILL' | 'BLAST' | 'CRUSHER' | 'BLOCK' | 'ROAD') => void;
}

export const ThreeMineScene: React.FC<ThreeMineSceneProps> = ({ state, onSelectAsset }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);

  // Mesh registries for fast updates
  const truckMeshesRef = useRef<Map<string, THREE.Group>>(new Map());
  const shovelMeshesRef = useRef<Map<string, THREE.Group>>(new Map());
  const drillMeshesRef = useRef<Map<string, THREE.Group>>(new Map());
  const blockMeshesGroupRef = useRef<THREE.Group | null>(null);
  const blastMeshesGroupRef = useRef<THREE.Group | null>(null);
  const roadLinesGroupRef = useRef<THREE.Group | null>(null);

  // Camera animation state
  const isDraggingRef = useRef(false);
  const previousMousePositionRef = useRef({ x: 0, y: 0 });
  const cameraTargetRef = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0));
  const cameraDistanceRef = useRef(380);
  const cameraAngleThetaRef = useRef(Math.PI / 4); // azimuth
  const cameraAnglePhiRef = useRef(Math.PI / 3.5); // elevation

  // Initialize Three.js Scene
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    // 1. Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090d16); // Deep industrial navy dark
    scene.fog = new THREE.FogExp2(0x090d16, 0.0012);
    sceneRef.current = scene;

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 3000);
    camera.position.set(220, 240, 280);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // 3. Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Lighting setup
    const ambientLight = new THREE.AmbientLight(0xdde8f8, 0.7);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfff4e0, 1.4);
    sunLight.position.set(300, 450, 200);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 1000;
    const d = 350;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    scene.add(sunLight);

    const hemiLight = new THREE.HemisphereLight(0x7090b0, 0x302518, 0.5);
    scene.add(hemiLight);

    // 5. Build Open Pit Terraces Geometry
    buildPitBenches(scene);

    // 6. Build Processing Plant, Crusher Hopper, Conveyors, Stockpiles
    buildProcessingPlant(scene);

    // 7. Groups for dynamic layers
    const roadsGroup = new THREE.Group();
    scene.add(roadsGroup);
    roadLinesGroupRef.current = roadsGroup;

    const blocksGroup = new THREE.Group();
    scene.add(blocksGroup);
    blockMeshesGroupRef.current = blocksGroup;

    const blastGroup = new THREE.Group();
    scene.add(blastGroup);
    blastMeshesGroupRef.current = blastGroup;

    // 8. Event Listeners for Orbit & Zoom
    const handleMouseDown = (e: MouseEvent) => {
      isDraggingRef.current = true;
      previousMousePositionRef.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const deltaX = e.clientX - previousMousePositionRef.current.x;
      const deltaY = e.clientY - previousMousePositionRef.current.y;

      if (e.buttons === 1) {
        // Orbit
        cameraAngleThetaRef.current -= deltaX * 0.005;
        cameraAnglePhiRef.current = Math.max(0.1, Math.min(Math.PI / 2.1, cameraAnglePhiRef.current - deltaY * 0.005));
      } else if (e.buttons === 2) {
        // Pan
        const forward = new THREE.Vector3();
        camera.getWorldDirection(forward);
        const right = new THREE.Vector3().crossVectors(forward, camera.up).normalize();
        cameraTargetRef.current.addScaledVector(right, -deltaX * 0.4);
        cameraTargetRef.current.y += deltaY * 0.4;
      }

      previousMousePositionRef.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseUp = () => {
      isDraggingRef.current = false;
    };

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      cameraDistanceRef.current = Math.max(40, Math.min(750, cameraDistanceRef.current + e.deltaY * 0.35));
    };

    const handleContextMenu = (e: MouseEvent) => e.preventDefault();

    // Raycast clicking
    const handleClick = (e: MouseEvent) => {
      if (Math.abs(e.clientX - previousMousePositionRef.current.x) > 5) return; // ignore drags
      const rect = renderer.domElement.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);

      const truckObjects: THREE.Object3D[] = [];
      truckMeshesRef.current.forEach((grp) => truckObjects.push(grp));
      const shovelObjects: THREE.Object3D[] = [];
      shovelMeshesRef.current.forEach((grp) => shovelObjects.push(grp));
      const drillObjects: THREE.Object3D[] = [];
      drillMeshesRef.current.forEach((grp) => drillObjects.push(grp));

      const intersects = raycaster.intersectObjects([...truckObjects, ...shovelObjects, ...drillObjects], true);
      if (intersects.length > 0) {
        let current: THREE.Object3D | null = intersects[0].object;
        while (current && !current.userData?.assetId && current.parent) {
          current = current.parent;
        }
        if (current && current.userData?.assetId) {
          onSelectAsset(current.userData.assetId, current.userData.assetType);
        }
      }
    };

    const domElem = renderer.domElement;
    domElem.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    domElem.addEventListener('wheel', handleWheel, { passive: false });
    domElem.addEventListener('contextmenu', handleContextMenu);
    domElem.addEventListener('click', handleClick);

    // Resize observer
    const handleResize = () => {
      if (!container || !rendererRef.current || !cameraRef.current) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    };
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // Animation Loop
    let animationFrameId: number;
    const renderLoop = () => {
      animationFrameId = requestAnimationFrame(renderLoop);

      // Camera position update based on spherical coordinates
      const cam = cameraRef.current;
      if (cam) {
        const theta = cameraAngleThetaRef.current;
        const phi = cameraAnglePhiRef.current;
        const r = cameraDistanceRef.current;
        const target = cameraTargetRef.current;

        cam.position.x = target.x + r * Math.sin(phi) * Math.sin(theta);
        cam.position.y = target.y + r * Math.cos(phi);
        cam.position.z = target.z + r * Math.sin(phi) * Math.cos(theta);
        cam.lookAt(target);
      }

      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
    };
    renderLoop();

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      domElem.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      domElem.removeEventListener('wheel', handleWheel);
      domElem.removeEventListener('contextmenu', handleContextMenu);
      domElem.removeEventListener('click', handleClick);
      renderer.dispose();
    };
  }, []);

  // Update dynamic entities on state change
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    // 1. Update Camera Focus Target
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

    // 2. Sync Haul Trucks
    state.trucks.forEach((truck) => {
      let truckGroup = truckMeshesRef.current.get(truck.id);
      if (!truckGroup) {
        truckGroup = createTruckMesh(truck);
        scene.add(truckGroup);
        truckMeshesRef.current.set(truck.id, truckGroup);
      }

      // Update position & rotation
      truckGroup.position.set(truck.position.x, truck.position.y + 1.2, truck.position.z);
      truckGroup.rotation.y = (truck.heading * Math.PI) / 180;
      truckGroup.visible = state.visibleLayers.equipment;

      // Update dump bed tilt if dumping
      const dumpBed = truckGroup.getObjectByName('dumpBed');
      if (dumpBed) {
        if (truck.cycleState === 'DUMPING') {
          dumpBed.rotation.x = -Math.PI / 4.5;
        } else {
          dumpBed.rotation.x = 0;
        }
      }

      // Update halo color based on cycle state
      const halo = truckGroup.getObjectByName('statusRing') as THREE.Mesh;
      if (halo && halo.material) {
        const mat = halo.material as THREE.MeshBasicMaterial;
        if (truck.id === state.selectedAssetId) {
          mat.color.setHex(0xf59e0b); // Highlight selected
          halo.scale.set(1.4, 1.4, 1.4);
        } else {
          halo.scale.set(1.0, 1.0, 1.0);
          switch (truck.cycleState) {
            case 'HAULING':
              mat.color.setHex(0x10b981); // Green loaded
              break;
            case 'RETURNING':
            case 'EMPTY_TRAVEL':
              mat.color.setHex(0x38bdf8); // Sky blue empty
              break;
            case 'LOADING':
              mat.color.setHex(0xa855f7); // Purple loading
              break;
            case 'QUEUE_SHOVEL':
            case 'QUEUE_DESTINATION':
              mat.color.setHex(0xf97316); // Orange queue
              break;
            case 'DUMPING':
              mat.color.setHex(0xef4444); // Red dumping
              break;
            default:
              mat.color.setHex(0x94a3b8);
          }
        }
      }

      // If chase camera on this truck
      if (state.cameraFocus === 'CHASE_TRUCK' && state.chaseTruckId === truck.id) {
        cameraTargetRef.current.copy(truckGroup.position);
      }
    });

    // 3. Sync Shovels
    state.shovels.forEach((shovel) => {
      let shovelGroup = shovelMeshesRef.current.get(shovel.id);
      if (!shovelGroup) {
        shovelGroup = createShovelMesh(shovel);
        scene.add(shovelGroup);
        shovelMeshesRef.current.set(shovel.id, shovelGroup);
      }
      shovelGroup.position.set(shovel.position.x, shovel.position.y + 1.5, shovel.position.z);
      shovelGroup.visible = state.visibleLayers.equipment;

      // Animate shovel upper body digging oscillation
      const upperCab = shovelGroup.getObjectByName('upperCab');
      if (upperCab && shovel.operatingState === 'OPERATIONAL') {
        upperCab.rotation.y = Math.sin(state.simTimeSeconds * 0.8) * 0.35;
      }
    });

    // 4. Sync Drill Rigs
    state.drills.forEach((drill) => {
      let drillGroup = drillMeshesRef.current.get(drill.id);
      if (!drillGroup) {
        drillGroup = createDrillMesh(drill);
        scene.add(drillGroup);
        drillMeshesRef.current.set(drill.id, drillGroup);
      }
      drillGroup.position.set(drill.position.x, drill.position.y + 1.2, drill.position.z);
      drillGroup.visible = state.visibleLayers.equipment;
    });

    // 5. Sync Blast Patterns Layer
    if (blastMeshesGroupRef.current) {
      blastMeshesGroupRef.current.clear();
      if (state.visibleLayers.blastPatterns) {
        state.blastPatterns.forEach((pattern) => {
          const patGroup = createBlastPatternMesh(pattern);
          blastMeshesGroupRef.current?.add(patGroup);
        });
      }
    }

    // 6. Sync Block Model Geology Layer
    if (blockMeshesGroupRef.current) {
      blockMeshesGroupRef.current.clear();
      if (state.visibleLayers.blockModelGeology) {
        const blocksMesh = createBlockModelMesh(state.blocks);
        blockMeshesGroupRef.current.add(blocksMesh);
      }
    }

    // 7. Sync Road Lines Layer
    if (roadLinesGroupRef.current) {
      roadLinesGroupRef.current.clear();
      if (state.visibleLayers.haulRoads) {
        state.roads.forEach((road) => {
          const roadMesh = createRoadMesh(road, state.visibleLayers.trafficHeatmap);
          roadLinesGroupRef.current?.add(roadMesh);
        });
      }
    }
  }, [state]);

  return (
    <div className="relative w-full h-full select-none overflow-hidden" ref={mountRef}>
      {/* 3D View Controls HUD Overlay */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-2 bg-slate-900/80 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-700/60 shadow-xl text-xs">
        <span className="text-slate-400 font-semibold uppercase tracking-wider text-[10px] mr-1">Cámaras:</span>
        <button
          onClick={() => {
            cameraTargetRef.current.set(0, 0, 0);
            cameraDistanceRef.current = 380;
            cameraAngleThetaRef.current = Math.PI / 4;
            cameraAnglePhiRef.current = Math.PI / 3.5;
          }}
          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-md font-medium transition flex items-center gap-1 border border-slate-700"
        >
          🌐 Pit General
        </button>
        <button
          onClick={() => {
            cameraTargetRef.current.set(45, 4.8, 90);
            cameraDistanceRef.current = 130;
          }}
          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded-md font-medium transition flex items-center gap-1 border border-slate-700"
        >
          ⛏️ Pala EX-01 (B3840)
        </button>
        <button
          onClick={() => {
            cameraTargetRef.current.set(-25, -2.4, -15);
            cameraDistanceRef.current = 120;
          }}
          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded-md font-medium transition flex items-center gap-1 border border-slate-700"
        >
          ⛏️ Pala EX-02 (Fondo B3680)
        </button>
        <button
          onClick={() => {
            cameraTargetRef.current.set(180, 12, -140);
            cameraDistanceRef.current = 110;
          }}
          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-sky-400 rounded-md font-medium transition flex items-center gap-1 border border-slate-700"
        >
          🏭 Chancador CR-01
        </button>
        <button
          onClick={() => {
            cameraTargetRef.current.set(85, 5.0, 60);
            cameraDistanceRef.current = 100;
          }}
          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-emerald-400 rounded-md font-medium transition flex items-center gap-1 border border-slate-700"
        >
          💥 Tronadura #104
        </button>
      </div>

      {/* Navigation Helper Indicator */}
      <div className="absolute bottom-4 right-4 z-10 bg-slate-900/80 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-700/60 shadow-xl text-[11px] text-slate-400 flex items-center gap-3">
        <span>🖱️ <b>Click Izq:</b> Orbitar</span>
        <span>🖱️ <b>Click Der:</b> Desplazar</span>
        <span>🔍 <b>Rueda:</b> Zoom</span>
        <span>🎯 <b>Click Activo:</b> Inspeccionar</span>
      </div>
    </div>
  );
};

// ==========================================
// 3D PROCEDURAL GENERATORS & MESH BUILDERS
// ==========================================

function buildPitBenches(scene: THREE.Scene) {
  // Stepped open-pit concentric amphitheater benches
  const benches = [
    { innerR: 300, outerR: 360, height: 14, y: 14, color: 0x3f3d3b }, // Surface rim 4000
    { innerR: 240, outerR: 300, height: 10, y: 10, color: 0x524e4a }, // Bench 3920
    { innerR: 170, outerR: 240, height: 5, y: 5, color: 0x6e655f }, // Bench 3840
    { innerR: 100, outerR: 170, height: 0, y: 0, color: 0x7c7365 }, // Bench 3760
    { innerR: 0, outerR: 100, height: -4, y: -4, color: 0x8d6b4f }, // Pit bottom 3680
  ];

  benches.forEach((b, idx) => {
    // Top flat berm
    const ringGeo = new THREE.RingGeometry(b.innerR, b.outerR, 48);
    ringGeo.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshStandardMaterial({
      color: b.color,
      roughness: 0.9,
      metalness: 0.1,
      flatShading: true,
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.position.y = b.y;
    ringMesh.receiveShadow = true;
    scene.add(ringMesh);

    // Bench slope wall
    if (idx < benches.length - 1) {
      const nextB = benches[idx + 1];
      const wallGeo = new THREE.CylinderGeometry(b.innerR, nextB.outerR, b.y - nextB.y, 48, 1, true);
      const wallMat = new THREE.MeshStandardMaterial({
        color: b.color + 0x111111,
        roughness: 0.95,
        flatShading: true,
      });
      const wallMesh = new THREE.Mesh(wallGeo, wallMat);
      wallMesh.position.y = (b.y + nextB.y) / 2;
      wallMesh.receiveShadow = true;
      scene.add(wallMesh);
    }
  });

  // Base ground grid
  const grid = new THREE.GridHelper(800, 40, 0x1e293b, 0x0f172a);
  grid.position.y = -4.5;
  scene.add(grid);
}

function buildProcessingPlant(scene: THREE.Scene) {
  const plantGroup = new THREE.Group();

  // 1. Primary Crusher Building (CR-01) at {x: 180, y: 12, z: -140}
  const crusherBuildingGeo = new THREE.BoxGeometry(22, 14, 28);
  const concreteMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.7 });
  const crusherMesh = new THREE.Mesh(crusherBuildingGeo, concreteMat);
  crusherMesh.position.set(180, 19, -140);
  crusherMesh.castShadow = true;
  crusherMesh.receiveShadow = true;
  crusherMesh.userData = { assetId: 'CR-01', assetType: 'CRUSHER' };
  plantGroup.add(crusherMesh);

  // Crusher dump hopper funnel
  const hopperGeo = new THREE.CylinderGeometry(8, 3, 7, 16);
  const steelMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.6, roughness: 0.4 });
  const hopperMesh = new THREE.Mesh(hopperGeo, steelMat);
  hopperMesh.position.set(180, 24, -140);
  hopperMesh.userData = { assetId: 'CR-01', assetType: 'CRUSHER' };
  plantGroup.add(hopperMesh);

  // 2. Overland Conveyor Belt to Stockpile
  const conveyorGeo = new THREE.CylinderGeometry(1.2, 1.2, 140, 8);
  conveyorGeo.rotateZ(Math.PI / 3.8);
  const conveyorMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.5 });
  const conveyorMesh = new THREE.Mesh(conveyorGeo, conveyorMat);
  conveyorMesh.position.set(215, 18, -30);
  conveyorMesh.rotation.y = -Math.PI / 6;
  plantGroup.add(conveyorMesh);

  // 3. Stockpile SP-01 Cone at {x: 230, y: 11, z: 80}
  const stockGeo = new THREE.ConeGeometry(26, 18, 24);
  const oreMat = new THREE.MeshStandardMaterial({ color: 0x92400e, roughness: 0.95 });
  const stockMesh = new THREE.Mesh(stockGeo, oreMat);
  stockMesh.position.set(230, 20, 80);
  stockMesh.castShadow = true;
  stockMesh.receiveShadow = true;
  stockMesh.userData = { assetId: 'SP-01', assetType: 'STOCKPILE' };
  plantGroup.add(stockMesh);

  // 4. North Waste Dump WD-01 at {x: -220, y: 14, z: -180}
  const dumpGeo = new THREE.BoxGeometry(45, 12, 50);
  const wasteMat = new THREE.MeshStandardMaterial({ color: 0x57534e, roughness: 0.9 });
  const dumpMesh = new THREE.Mesh(dumpGeo, wasteMat);
  dumpMesh.position.set(-220, 20, -180);
  dumpMesh.castShadow = true;
  dumpMesh.receiveShadow = true;
  plantGroup.add(dumpMesh);

  // 5. SAG Mill & Concentrator Building ML-01 at {x: 280, y: 10, z: -160}
  const millBldgGeo = new THREE.BoxGeometry(36, 16, 48);
  const millBldgMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.3 });
  const millBldg = new THREE.Mesh(millBldgGeo, millBldgMat);
  millBldg.position.set(280, 18, -160);
  millBldg.castShadow = true;
  millBldg.userData = { assetId: 'ML-01', assetType: 'MILL' };
  plantGroup.add(millBldg);

  scene.add(plantGroup);
}

function createTruckMesh(truck: any): THREE.Group {
  const group = new THREE.Group();
  group.userData = { assetId: truck.id, assetType: 'TRUCK' };

  // Main chassis frame
  const chassisGeo = new THREE.BoxGeometry(4.8, 1.4, 9.2);
  const chassisMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.3 });
  const chassis = new THREE.Mesh(chassisGeo, chassisMat);
  chassis.position.y = 1.6;
  chassis.castShadow = true;
  group.add(chassis);

  // Operator Cabin
  const cabGeo = new THREE.BoxGeometry(1.8, 1.8, 2.2);
  const cabMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.4 });
  const cab = new THREE.Mesh(cabGeo, cabMat);
  cab.position.set(-1.3, 3.1, 2.8);
  cab.castShadow = true;
  group.add(cab);

  // Windshield glass
  const glassGeo = new THREE.BoxGeometry(1.6, 0.9, 0.2);
  const glassMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
  const glass = new THREE.Mesh(glassGeo, glassMat);
  glass.position.set(-1.3, 3.3, 3.95);
  group.add(glass);

  // Tilting Dump Bed
  const dumpBedGroup = new THREE.Group();
  dumpBedGroup.name = 'dumpBed';
  dumpBedGroup.position.set(0, 2.4, -1.8); // pivot hinge

  const bedGeo = new THREE.BoxGeometry(4.6, 2.2, 7.2);
  const bedMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.5, metalness: 0.2 });
  const bed = new THREE.Mesh(bedGeo, bedMat);
  bed.position.set(0, 1.1, 1.8);
  bed.castShadow = true;
  dumpBedGroup.add(bed);

  // Payload ore rocks inside bed
  const oreFillGeo = new THREE.BoxGeometry(4.2, 1.2, 6.6);
  const oreFillMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.9 });
  const oreFill = new THREE.Mesh(oreFillGeo, oreFillMat);
  oreFill.position.set(0, 1.9, 1.8);
  dumpBedGroup.add(oreFill);

  group.add(dumpBedGroup);

  // 6 Heavy Mining Tires
  const tireGeo = new THREE.CylinderGeometry(1.3, 1.3, 0.9, 16);
  tireGeo.rotateZ(Math.PI / 2);
  const tireMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.9 });

  const tireOffsets = [
    [-2.4, 1.3, 2.6],
    [2.4, 1.3, 2.6],
    [-2.4, 1.3, -1.4],
    [2.4, 1.3, -1.4],
    [-2.4, 1.3, -3.2],
    [2.4, 1.3, -3.2],
  ];

  tireOffsets.forEach(([tx, ty, tz]) => {
    const tire = new THREE.Mesh(tireGeo, tireMat);
    tire.position.set(tx, ty, tz);
    tire.castShadow = true;
    group.add(tire);
  });

  // Status Ring Halo underneath truck
  const ringGeo = new THREE.RingGeometry(3.6, 4.4, 24);
  ringGeo.rotateX(-Math.PI / 2);
  const ringMat = new THREE.MeshBasicMaterial({ color: 0x10b981, side: THREE.DoubleSide });
  const ringMesh = new THREE.Mesh(ringGeo, ringMat);
  ringMesh.name = 'statusRing';
  ringMesh.position.y = 0.1;
  group.add(ringMesh);

  return group;
}

function createShovelMesh(shovel: any): THREE.Group {
  const group = new THREE.Group();
  group.userData = { assetId: shovel.id, assetType: 'SHOVEL' };

  // Crawler tracks base
  const trackGeo = new THREE.BoxGeometry(10, 2.2, 12);
  const trackMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.8 });
  const tracks = new THREE.Mesh(trackGeo, trackMat);
  tracks.position.y = 1.1;
  tracks.castShadow = true;
  group.add(tracks);

  // Upper revolving body
  const upperCab = new THREE.Group();
  upperCab.name = 'upperCab';
  upperCab.position.y = 2.2;

  const bodyGeo = new THREE.BoxGeometry(9, 6.5, 10);
  const bodyMat = new THREE.MeshStandardMaterial({ color: 0xeab308, roughness: 0.4 });
  const body = new THREE.Mesh(bodyGeo, bodyMat);
  body.position.set(0, 3.25, -1);
  body.castShadow = true;
  upperCab.add(body);

  // Boom
  const boomGeo = new THREE.CylinderGeometry(0.8, 1.2, 16, 8);
  boomGeo.rotateX(Math.PI / 3.8);
  const boomMat = new THREE.MeshStandardMaterial({ color: 0xca8a04, metalness: 0.6 });
  const boom = new THREE.Mesh(boomGeo, boomMat);
  boom.position.set(0, 8.5, 6.5);
  boom.castShadow = true;
  upperCab.add(boom);

  // Shovel dipper bucket
  const bucketGeo = new THREE.BoxGeometry(4.5, 3.5, 4.0);
  const bucketMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.7, roughness: 0.3 });
  const bucket = new THREE.Mesh(bucketGeo, bucketMat);
  bucket.position.set(0, 3.0, 13.0);
  bucket.castShadow = true;
  upperCab.add(bucket);

  group.add(upperCab);

  // Active muckpile face next to shovel
  const muckGeo = new THREE.ConeGeometry(14, 8, 16);
  const muckMat = new THREE.MeshStandardMaterial({ color: 0x713f12, roughness: 0.95 });
  const muck = new THREE.Mesh(muckGeo, muckMat);
  muck.position.set(0, 3.8, 18);
  group.add(muck);

  return group;
}

function createDrillMesh(drill: any): THREE.Group {
  const group = new THREE.Group();
  group.userData = { assetId: drill.id, assetType: 'DRILL' };

  // Crawler Base
  const baseGeo = new THREE.BoxGeometry(6.0, 1.8, 8.0);
  const baseMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.7 });
  const base = new THREE.Mesh(baseGeo, baseMat);
  base.position.y = 0.9;
  group.add(base);

  // Cabin
  const cabGeo = new THREE.BoxGeometry(3.2, 2.6, 4.0);
  const cabMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.4 });
  const cab = new THREE.Mesh(cabGeo, cabMat);
  cab.position.set(-0.8, 2.8, -1.2);
  group.add(cab);

  // Vertical Drill Mast (Tower)
  const mastGeo = new THREE.BoxGeometry(1.6, 18.0, 2.0);
  const mastMat = new THREE.MeshStandardMaterial({ color: 0xe0f2fe, metalness: 0.7, roughness: 0.3 });
  const mast = new THREE.Mesh(mastGeo, mastMat);
  mast.position.set(0, 10.0, 2.2);
  mast.castShadow = true;
  group.add(mast);

  // Drill String Rod
  const rodGeo = new THREE.CylinderGeometry(0.3, 0.3, 14.0, 8);
  const rodMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9 });
  const rod = new THREE.Mesh(rodGeo, rodMat);
  rod.position.set(0, 6.0, 2.2);
  group.add(rod);

  return group;
}

function createBlastPatternMesh(pattern: any): THREE.Group {
  const group = new THREE.Group();
  group.userData = { assetId: pattern.id, assetType: 'BLAST' };

  pattern.holes.forEach((h: any) => {
    // Borehole marker cylinder
    const holeGeo = new THREE.CylinderGeometry(0.6, 0.6, 1.8, 12);
    const color = h.isLoaded ? 0xef4444 : h.isDrilled ? 0x10b981 : 0xf59e0b;
    const holeMat = new THREE.MeshBasicMaterial({ color });
    const holeMesh = new THREE.Mesh(holeGeo, holeMat);
    holeMesh.position.set(h.x, h.y + 0.9, h.z);
    group.add(holeMesh);

    // Collar flag / detonation delay tag
    const flagGeo = new THREE.ConeGeometry(0.5, 1.2, 8);
    const flagMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
    const flag = new THREE.Mesh(flagGeo, flagMat);
    flag.position.set(h.x, h.y + 2.2, h.z);
    group.add(flag);
  });

  return group;
}

function createBlockModelMesh(blocks: any[]): THREE.Group {
  const group = new THREE.Group();
  const boxGeo = new THREE.BoxGeometry(12, 5, 12);

  blocks.forEach((b) => {
    if (b.isMined) return;

    // Color by Cu Grade % or Lithology
    let hexColor = 0x64748b;
    if (b.classification === 'ORE') {
      hexColor = b.cuGrade > 1.2 ? 0xa855f7 : b.cuGrade > 0.8 ? 0xef4444 : 0xf59e0b;
    } else if (b.classification === 'LOW_GRADE') {
      hexColor = 0xeab308;
    }

    const boxMat = new THREE.MeshStandardMaterial({
      color: hexColor,
      transparent: true,
      opacity: 0.65,
      roughness: 0.8,
    });
    const mesh = new THREE.Mesh(boxGeo, boxMat);
    mesh.position.set(b.x, b.y + 2.5, b.z);
    mesh.userData = { assetId: b.id, assetType: 'BLOCK' };
    group.add(mesh);
  });

  return group;
}

function createRoadMesh(road: any, isTrafficHeatmap: boolean): THREE.Group {
  const group = new THREE.Group();
  const points = road.waypoints.map((wp: any) => new THREE.Vector3(wp.x, wp.y + 0.15, wp.z));

  if (points.length >= 2) {
    const curve = new THREE.CatmullRomCurve3(points);
    const tubeGeo = new THREE.TubeGeometry(curve, 32, 2.4, 6, false);

    let color = 0x334155;
    if (isTrafficHeatmap) {
      color = road.currentTrafficCount > 4 ? 0xef4444 : road.currentTrafficCount > 2 ? 0xf59e0b : 0x10b981;
    }

    const tubeMat = new THREE.MeshStandardMaterial({
      color,
      roughness: 0.9,
      transparent: true,
      opacity: 0.75,
    });
    const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat);
    tubeMesh.receiveShadow = true;
    group.add(tubeMesh);

    // Centerline dashed guide
    const lineGeo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(50));
    const lineMat = new THREE.LineDashedMaterial({
      color: 0xfacc15,
      dashSize: 4,
      gapSize: 2,
    });
    const lineMesh = new THREE.Line(lineGeo, lineMat);
    lineMesh.computeLineDistances();
    group.add(lineMesh);
  }

  return group;
}
