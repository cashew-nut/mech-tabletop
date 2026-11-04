#!/usr/bin/env python3
"""Build Meshy prompts for a walker class from data/style-bible.json (stdlib only).

  prompts.py CLASS hero|turnaround|partsheet [--variant N]
  prompts.py CLASS all            # print the three prompts

Wording lives in the bible and the templates below, never per class by hand, so a faction reads the same across classes.
See docs/model-pipeline-plan.md ("Prompt templates").
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load(cls):
    bible = json.load(open(os.path.join(ROOT, "data/style-bible.json")))
    c = bible["classes"][cls]
    return bible["factions"][c["faction"]], c

# Three-quarter, front, and so on: small variations so re-rolls explore different poses instead of repeating.
HERO_VARIANTS = [
    "standing in a wide stance, three-quarter view from the front left",
    "standing braced, slightly low camera angle, three-quarter view from the front right",
    "marching forward, three-quarter view from the front left, banner and cloth moving",
]

def hero(f, c, variant=0):
    return (
        f"Concept art of an {f['name']} war-walker, {c['role']} class. Same faction and art style as the reference images. "
        f"{f['feel'].capitalize()}. Colours: {f['palette']}. Details: {f['motifs']}. "
        f"Silhouette: {c['silhouette']}. Armed with {c['weapons']}. Back: {c['back']}. "
        f"Full body, {HERO_VARIANTS[variant % len(HERO_VARIANTS)]}, dark moody background, dramatic rim light. "
        f"Not: {f['never']}."
    )

def turnaround(f, c):
    return (
        "The same war-walker as the reference, unchanged design and colours. Front, side and back views, standing in a "
        "relaxed A-pose with the arms held clear of the body and the legs apart, flat light grey background, even lighting, "
        "no shadows, no cloth blowing, no scenery, nothing held across the body. "
        f"Joints clearly visible: {f['joints']}. Every limb at least {c['minLimb']} of the body height thick. "
        f"Weapons: {c['weapons']}."
    )

def partsheet(f, c):
    return (
        "The same war-walker as the reference, taken apart into its pieces and laid out apart on a flat dark background, "
        f"like a model kit: {c['parts']}. Each piece shows its round connection socket. "
        "Same colours and detail as the reference. Every piece drawn once, nothing overlapping."
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cls"); ap.add_argument("kind", choices=["hero", "turnaround", "partsheet", "all"])
    ap.add_argument("--variant", type=int, default=0)
    a = ap.parse_args()
    f, c = load(a.cls)
    out = {"hero": hero(f, c, a.variant), "turnaround": turnaround(f, c), "partsheet": partsheet(f, c)}
    if a.kind == "all":
        for k, v in out.items():
            print(f"## {k}\n{v}\n")
    else:
        print(out[a.kind])

if __name__ == "__main__":
    main()
