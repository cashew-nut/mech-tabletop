// Review render of the real 3D board with real walkers, for headless screenshots.
//   render-battle.html?f0=covenant&f1=foundries&map=chapel-ruins&scale=0.07&select=s0w0&pixel=1
import { createRoot } from 'react-dom/client';
import { createGame, type LanceInput } from '@brass-charter/rules';
import { Board3D } from './Board3D';
import '../styles.css';

const params = new URLSearchParams(location.search);
import examples from '../../../../data/lances/examples.json';

const EXAMPLE = Object.fromEntries((examples.lances as LanceInput[]).map((l) => [l.faction, l]));
// What to show instead of each example walker: the Meshy-built classes first, then the older ones.
const SHOW: Record<string, Array<[string, Record<string, string[]>]>> = {
  covenant: [['paladin', { armLeft: ['lance'], armRight: ['lance'] }], ['paladin', { armLeft: ['lance'] }], ['lancer', { armLeft: ['lance'] }]],
  foundries: [['brute', { armLeft: ['rocket-pod'], armRight: ['autocannon'] }], ['brute', { armRight: ['autocannon'] }], ['scavenger', { armRight: ['autocannon'] }]],
  reliquary: [['seer', { armRight: ['arc-cannon'] }], ['seer', { armRight: ['arc-cannon'] }], ['wraith', { armRight: ['kinetic-claws'] }]],
};

const state = createGame({
  seed: 7,
  scenario: params.get('scenario') ?? 'hold-the-field',
  map: params.get('map') ?? 'chapel-ruins',
  deploy: 'auto',
  lances: [EXAMPLE[params.get('f0') ?? 'covenant'], EXAMPLE[params.get('f1') ?? 'foundries']],
});
// Swap in the classes to review. The rules never see this: it only changes what the board draws.
for (const w of state.walkers) {
  const [chassis, loadout] = SHOW[state.lances[w.side].faction][Number(w.id.slice(3))];
  w.chassis = chassis;
  w.items = Object.entries(loadout).flatMap(([location, ids]) => ids.map((id, n) => ({ uid: `${w.id}${location}${n}`, id, location: location as 'armLeft', destroyed: false, ammo: null, uses: null, firedThisActivation: false })));
}
// Optional: pull the two sides together for a close-up.
if (params.get('close')) {
  const [a, b] = [state.walkers.find((w) => w.side === 0)!, state.walkers.find((w) => w.side === 1)!];
  b.pos = { q: a.pos.q + 2, r: a.pos.r - 1 };
  b.facing = ((a.facing + 3) % 6) as typeof b.facing;
}
const select = params.get('select');
if (params.get('prone')) state.walkers[Number(params.get('prone'))].prone = true;
if (params.get('spent')) state.walkers[Number(params.get('spent'))].activated = true;
createRoot(document.getElementById('root')!).render(
  <Board3D state={state} highlights={new Map()} selectedId={select} targetId={null} onHex={() => {}} onWalker={() => {}} />,
);
// Ready once the kit parts of every class on the board have had time to arrive.
const settle = async () => {
  await new Promise((r) => setTimeout(r, Number(params.get('wait') ?? 9000)));
  document.body.dataset.ready = '1';
};
settle();
