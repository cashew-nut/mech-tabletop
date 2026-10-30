// The lit display stage the walker stands on, shared by the builder's 3D view
// and the preview renderer: an environment map for metal reflections, a warm
// key light with soft shadows, a cool rim light, and a dark plinth floor.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

export interface Stage {
  scene: THREE.Scene;
  /** Move the shadow camera to fit a newly added model. */
  fit: (model: THREE.Object3D) => void;
}

export function setupRenderer(renderer: THREE.WebGLRenderer) {
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
}

/** White in the middle fading to clear at the rim, so the floor melts into the background. */
function fadeTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  grad.addColorStop(0, '#fff');
  grad.addColorStop(0.45, '#fff');
  grad.addColorStop(1, '#000');
  g.fillStyle = grad;
  g.fillRect(0, 0, 256, 256);
  return new THREE.CanvasTexture(c);
}

/** A soft radial floor so the walker reads against the background. */
function floorTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(256, 256, 0, 256, 256, 256);
  grad.addColorStop(0, '#3a322b');
  grad.addColorStop(1, '#2a241f');
  g.fillStyle = grad;
  g.fillRect(0, 0, 512, 512);
  // Faint hex grid, like the game table.
  g.strokeStyle = 'rgba(214, 178, 110, 0.05)';
  g.lineWidth = 1.5;
  const r = 26;
  for (let row = -1; row < 14; row++) {
    for (let col = -1; col < 12; col++) {
      const x = col * r * 1.5;
      const y = row * r * Math.sqrt(3) + (col % 2 ? (r * Math.sqrt(3)) / 2 : 0);
      g.beginPath();
      for (let i = 0; i <= 6; i++) {
        const a = (Math.PI / 3) * i;
        g.lineTo(x + r * Math.cos(a), y + r * Math.sin(a));
      }
      g.stroke();
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export function createStage(renderer: THREE.WebGLRenderer): Stage {
  setupRenderer(renderer);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#1b1815');
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;
  pmrem.dispose();

  scene.add(new THREE.HemisphereLight('#ffe9c4', '#2a2018', 0.5));
  const key = new THREE.DirectionalLight('#ffd9a0', 3.2);
  key.position.set(60, 110, 70);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.02;
  key.shadow.radius = 4;
  scene.add(key, key.target);
  const rim = new THREE.DirectionalLight('#9cc8ff', 2.4);
  rim.position.set(-70, 60, -90);
  scene.add(rim);
  const fill = new THREE.PointLight('#ff9a4a', 800, 0, 2);
  fill.position.set(-50, 15, 60);
  scene.add(fill);

  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(160, 64),
    new THREE.MeshStandardMaterial({ map: floorTexture(), alphaMap: fadeTexture(), transparent: true, depthWrite: false, roughness: 0.92, metalness: 0 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  floor.name = 'stage_floor';
  scene.add(floor);

  const fit = (model: THREE.Object3D) => {
    model.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) o.castShadow = o.receiveShadow = true;
    });
    const box = new THREE.Box3().setFromObject(model);
    const r = Math.max(30, box.getSize(new THREE.Vector3()).length() * 0.7);
    const cam = key.shadow.camera;
    cam.left = cam.bottom = -r;
    cam.right = cam.top = r;
    cam.near = 1;
    cam.far = 400;
    cam.updateProjectionMatrix();
  };
  return { scene, fit };
}
