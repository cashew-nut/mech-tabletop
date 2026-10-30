// File exports for a built war-walker: STL for 3D printing, GLB for Blender or other tools.
import * as THREE from 'three';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import { STLExporter } from 'three/examples/jsm/exporters/STLExporter.js';

function save(data: BlobPart, type: string, filename: string) {
  const url = URL.createObjectURL(new Blob([data], { type }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const slug = (name: string) => name.replace(/[^a-z0-9]+/gi, '-').toLowerCase() || 'war-walker';

/** Binary STL in millimetres, Z up as slicers expect. */
export function stlBytes(model: THREE.Object3D): DataView {
  const wrapper = new THREE.Group();
  const copy = model.clone(true);
  wrapper.add(copy);
  wrapper.rotation.x = Math.PI / 2; // three.js is Y up; slicers are Z up
  wrapper.updateMatrixWorld(true);
  // Mirrored kit parts (scale x = -1) would export inside out: reverse their triangles.
  copy.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh || mesh.matrixWorld.determinant() >= 0) return;
    const g = mesh.geometry.index ? mesh.geometry.toNonIndexed() : mesh.geometry.clone();
    const pos = g.getAttribute('position');
    for (let i = 0; i + 2 < pos.count; i += 3) {
      const [x, y, z] = [pos.getX(i + 1), pos.getY(i + 1), pos.getZ(i + 1)];
      pos.setXYZ(i + 1, pos.getX(i + 2), pos.getY(i + 2), pos.getZ(i + 2));
      pos.setXYZ(i + 2, x, y, z);
    }
    mesh.geometry = g;
  });
  return new STLExporter().parse(wrapper, { binary: true }) as DataView;
}

export function exportStl(model: THREE.Object3D, name: string) {
  save(stlBytes(model), 'model/stl', `${slug(name)}.stl`);
}

export async function exportGlb(model: THREE.Object3D, name: string) {
  const data = (await new GLTFExporter().parseAsync(model, { binary: true })) as ArrayBuffer;
  save(data, 'model/gltf-binary', `${slug(name)}.glb`);
}
