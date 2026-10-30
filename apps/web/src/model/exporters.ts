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
  return new STLExporter().parse(wrapper, { binary: true }) as DataView;
}

export function exportStl(model: THREE.Object3D, name: string) {
  save(stlBytes(model), 'model/stl', `${slug(name)}.stl`);
}

export async function exportGlb(model: THREE.Object3D, name: string) {
  const data = (await new GLTFExporter().parseAsync(model, { binary: true })) as ArrayBuffer;
  save(data, 'model/gltf-binary', `${slug(name)}.glb`);
}
