// The board generator: seed in, MapDef and ScenarioDef out. It builds many
// candidate boards from the seed's own random stream, throws away any that
// break a hard rule, and keeps the best-scoring one. The same seed (and
// generator version) always gives the same board.
import { RULES, getMap, getScenario, type MapDef, type ObjectiveDef, type ScenarioDef } from '../data';
import { nextFloat, type Rng } from '../rng';
import { ARCHETYPES, getArchetype, laySpine, weighted, type Archetype, type ArchetypeId } from './archetypes';
import { Board } from './board';
import { softScores, nonOpenShare, type SoftScores } from './metrics';
import { PIECES, placePiece } from './pieces';
import { TEMPLATES, getTemplate, placeObjectives, type Template, type TemplateId } from './templates';
import { LIMITS, checkBoard, type BoardReport } from './validate';

/** Bump when a change would give an old seed a different board, so old share codes stay meaningful. */
export const GENERATOR_VERSION = 'G1';

export interface GenerateOptions {
  archetype?: ArchetypeId;
  template?: TemplateId;
  /** Most candidate boards built per seed; the best that passes every hard rule is kept. */
  candidates?: number;
  /** Stop early once this many candidates have passed (the best of them is kept). */
  enough?: number;
}

export interface GeneratedBoard {
  code: string;
  seed: number;
  archetype: ArchetypeId;
  template: TemplateId;
  map: MapDef;
  scenario: ScenarioDef;
  board: Board;
  objectives: ObjectiveDef[];
  report: BoardReport;
  scores: SoftScores | null;
  /** Candidates built, and how many passed the hard rules. */
  tried: number;
  passed: number;
  /** True when no candidate passed and a hand-made board stands in. */
  fallback: boolean;
}

const WIDTH = 16;
const HEIGHT = 12;

const TEMPLATE_WEIGHTS: Array<[TemplateId, number]> = [
  ['line', 3],
  ['diamond', 3],
  ['wells', 2],
  ['scatter', 2],
];

const NAME_FIRST = ['Gearwright', 'Hollowmere', 'Cinder', 'Vane', 'Brassgate', 'Ashby', 'Kettle', 'Coldforge', 'Mainspring', 'Saltire', 'Grieve', 'Tallow', 'Ironwell', 'Quill', 'Marrow', 'Soot'];
const NAME_SECOND: Record<ArchetypeId, string[]> = {
  foundry: ['Yard', 'Works', 'Smeltery', 'Sheds', 'Ironworks'],
  canal: ['Cut', 'Locks', 'Wharf', 'Basin', 'Crossing'],
  chapel: ['Chapel', 'Abbey', 'Reliquary', 'Cloister', 'Ruins'],
  ridge: ['Ridge', 'Heights', 'Scarp', 'Tors', 'Rise'],
  plain: ['Flats', 'Moor', 'Field', 'Reach', 'Commons'],
};

const pickOf = <T>(rng: Rng, xs: readonly T[]): T => xs[Math.floor(nextFloat(rng) * xs.length)];

export function boardCode(seed: number, archetype: ArchetypeId, template: TemplateId): string {
  return `${GENERATOR_VERSION}-${getArchetype(archetype).code}-${getTemplate(template).code}-${(seed >>> 0).toString(16).toUpperCase()}`;
}

/** Read a share code back into the options that rebuild its board, or null if it is not one of ours. */
export function parseBoardCode(code: string): { seed: number; archetype: ArchetypeId; template: TemplateId } | null {
  const m = /^G1-([A-Z]+)-([A-Z])-([0-9A-F]{1,8})$/.exec(code.trim().toUpperCase());
  if (!m) return null;
  const arch = ARCHETYPES.find((a) => a.code === m[1]);
  const tpl = TEMPLATES.find((t) => t.code === m[2]);
  if (!arch || !tpl) return null;
  return { seed: parseInt(m[3], 16) >>> 0, archetype: arch.id, template: tpl.id };
}

/** One candidate board for an archetype and template (exported for the tuning tools). */
export function buildCandidate(arch: Archetype, template: Template, rng: Rng, depth: number): { board: Board; objectives: ObjectiveDef[]; spineShare: number } | null {
  const board = new Board(WIDTH, HEIGHT);
  if (arch.spine) laySpine(board, arch.spine, rng);
  const spineShare = nonOpenShare(board);
  const target = spineShare + arch.budget[0] + nextFloat(rng) * (arch.budget[1] - arch.budget[0]);
  for (let attempt = 0; attempt < 120 && nonOpenShare(board) < target; attempt++) {
    const type = weighted(rng, arch.pieces);
    const shape = PIECES[type](rng);
    const col = Math.floor(nextFloat(rng) * WIDTH);
    const row = arch.anchorRows[0] + Math.floor(nextFloat(rng) * (arch.anchorRows[1] - arch.anchorRows[0] + 1));
    const turns = Math.floor(nextFloat(rng) * 6);
    placePiece(board, shape, col, row, turns, arch.gap);
  }
  const objectives = placeObjectives(board, template, rng, depth);
  return objectives ? { board, objectives, spineShare } : null;
}

export function generateBoard(seed: number, options: GenerateOptions = {}): GeneratedBoard {
  const rng: Rng = { state: Math.imul((seed >>> 0) ^ 0x5bd1e995, 0x9e3779b1) | 0 };
  // Always draw both choices so a forced choice leaves the rest of the stream unchanged.
  const drawnArch = pickOf(rng, ARCHETYPES).id;
  const drawnTpl = weighted(rng, TEMPLATE_WEIGHTS);
  const archetype = options.archetype ?? drawnArch;
  const templateId = options.template ?? drawnTpl;
  const arch = getArchetype(archetype);
  const template = getTemplate(templateId);
  const name = `${pickOf(rng, NAME_FIRST)} ${pickOf(rng, NAME_SECOND[archetype])}`;
  const depth = RULES.map.deploymentDepth;
  const candidates = options.candidates ?? 120;
  const code = boardCode(seed, archetype, templateId);

  let best: { board: Board; objectives: ObjectiveDef[]; spineShare: number; report: BoardReport; scores: SoftScores } | null = null;
  let passed = 0;
  const enough = options.enough ?? 24;
  let tried = 0;
  // A hard seed (rare, mostly canal boards) keeps going, up to three times the usual budget, until one board passes.
  for (let i = 0; i < candidates * 3 && passed < enough && !(i >= candidates && passed > 0); i++) {
    tried++;
    const cand = buildCandidate(arch, template, rng, depth);
    if (!cand) continue;
    const report = checkBoard(cand.board, cand.objectives, depth, { limits: arch.limits, stopOnFail: true });
    if (!report.ok) continue;
    passed++;
    const budget: [number, number] = [arch.budget[0] + cand.spineShare, arch.budget[1] + cand.spineShare];
    const scores = softScores(cand.board, cand.objectives, depth, report, budget, arch.limits?.zoneLos ?? LIMITS.zoneLos);
    if (!best || scores.total > best.scores.total) best = { ...cand, report, scores };
  }

  if (!best) {
    const map = getMap('chapel-ruins');
    const scenario = getScenario('hold-the-field');
    const board = Board.fromMap(map);
    return {
      code,
      seed,
      archetype,
      template: templateId,
      map,
      scenario,
      board,
      objectives: scenario.objectives,
      report: checkBoard(board, scenario.objectives, depth, { limits: arch.limits }),
      scores: null,
      tried,
      passed: 0,
      fallback: true,
    };
  }

  const map: MapDef = { id: `gen-${code}`, name, width: WIDTH, height: HEIGHT, hexes: best.board.toMapHexes() };
  const scenario: ScenarioDef = {
    id: `gen-${code}`,
    name: template.label,
    objectives: best.objectives,
    rules: `${template.rules} Generated ${arch.label.toLowerCase()} board, code ${code}.`,
  };
  return {
    code,
    seed,
    archetype,
    template: templateId,
    map,
    scenario,
    board: best.board,
    objectives: best.objectives,
    report: best.report,
    scores: best.scores,
    tried,
    passed,
    fallback: false,
  };
}

/** Rebuild a board from its share code. */
export function boardFromCode(code: string, options: Omit<GenerateOptions, 'archetype' | 'template'> = {}): GeneratedBoard | null {
  const parsed = parseBoardCode(code);
  return parsed ? generateBoard(parsed.seed, { ...options, archetype: parsed.archetype, template: parsed.template }) : null;
}
