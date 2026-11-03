// Freeing GPU memory when the 3D board goes away. Three.js never does this on its own: a geometry, material or texture stays
// uploaded until dispose() is called, and the renderer keeps a listener on each one, so anything shared between mounts (the board
// kit, the part library, the module-level props in boardArt) also keeps the old renderer alive. Disposing a shared resource is safe:
// it is simply uploaded again if a later board uses it.
import * as THREE from 'three';

/** Dispose each distinct item once. */
export function disposeAll(items: Iterable<{ dispose: () => void }>) {
  for (const item of new Set(items)) item.dispose();
}

/** A material and the textures it holds. */
export function materialResources(m: THREE.Material) {
  const found: Array<{ dispose: () => void }> = [m];
  for (const value of Object.values(m)) if ((value as THREE.Texture | null)?.isTexture) found.push(value as THREE.Texture);
  return found;
}

/** Every geometry, material and material texture under `root` (the root included), each listed once. */
export function gpuResources(root: THREE.Object3D) {
  const found = new Set<{ dispose: () => void }>();
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (mesh.geometry) found.add(mesh.geometry);
    const materials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
    for (const m of materials) for (const r of materialResources(m)) found.add(r);
  });
  return found;
}

/** Dispose everything under `root` that holds GPU memory. The objects stay attached; only their GPU copies are freed. */
export function disposeTree(root: THREE.Object3D) {
  disposeAll(gpuResources(root));
}
