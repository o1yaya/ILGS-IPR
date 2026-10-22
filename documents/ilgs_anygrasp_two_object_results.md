# ILGS-to-AnyGrasp Two-Object Feasibility Results

## 1. Experimental scope

This experiment evaluates an end-to-end language-conditioned grasp pipeline on
two targets from the TUM `fr1/desk` RGB-D sequence:

1. `game controller`: a compact non-planar target partially surrounded by desk
   clutter and a planar cardboard support region.
2. `cereal box`: an upright approximately planar target adjacent to another
   box and office objects.

The pipeline is:

`text query -> multi-view pseudo masks -> confidence-weighted ILGS identity field
-> named ILGS masks -> RGB-D metric fusion -> target-region AnyGrasp ->
target-aware final grasp selection`.

Candidate quality is evaluated using the distance from each predicted grasp
center to the reference target point cloud. `Hit@20mm` is a target-localization
proxy, not a physical grasp-success rate.

## 2. Object-level ablation results

| Target | Method | Raw | Saved | Hit@10mm | Hit@20mm | Hit@30mm | Mean target distance (mm) | Max SDK score | Mean normal alignment |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Game controller | Full | 8 | 8 | 100% | 100% | 100% | 2.23 | 0.0912 | 0.835 |
| Game controller | No region steering | 90 | 50 | 12% | 12% | 12% | 91.92 | 0.1640 | 0.841 |
| Game controller | No normal reranking | 8 | 8 | 100% | 100% | 100% | 2.23 | 0.0912 | 0.835 |
| Game controller | No support-plane cleanup | 68 | 50 | 48% | 48% | 48% | 45.83 | 0.0692 | 0.740 |
| Cereal box | Full | 59 | 50 | 98% | 100% | 100% | 2.79 | 0.0985 | 0.784 |
| Cereal box | No region steering | 123 | 50 | 30% | 30% | 30% | 171.17 | 0.2112 | 0.826 |
| Cereal box | No normal reranking | 59 | 50 | 98% | 100% | 100% | 2.87 | 0.0985 | 0.695 |

## 3. Cross-object summary

| Comparison | Macro Hit@20mm | Macro mean distance (mm) | Interpretation |
|---|---:|---:|---|
| Full | 100% | 2.51 | Candidates remain localized to both queried targets. |
| No region steering | 21% | 131.55 | Most high-scoring grasps move to unrelated scene geometry. |
| No normal reranking | 100% | 2.55 | Localization is retained, but orientation quality drops on the planar box. |

Removing semantic region steering reduces macro Hit@20mm by 79 percentage
points and increases mean target distance by approximately 52 times. Meanwhile,
the maximum raw AnyGrasp score increases from an average of 0.0949 to 0.1876.
This shows that grasp confidence alone does not indicate whether a grasp belongs
to the language-selected object.

Normal reranking does not change target-hit rate in these two cases. On the
cereal box, however, it increases mean normal alignment from 0.695 to 0.784.
This supports an orientation-quality claim, not a target-localization claim.

Support-plane cleanup raises controller Hit@20mm from 48% to 100%. It is not
applied to the cereal box because fitting a dominant plane inside that target
would remove the object's own planar faces. The cleanup stage must therefore be
object-adaptive rather than universally enabled.

## 4. Automatically selected final grasps

| Target | Selected rank | SDK score | Width (mm) | Insertion depth (mm) | Target distance (mm) |
|---|---:|---:|---:|---:|---:|
| Game controller | 0 | 0.0912 | 50.80 | 20.00 | 3.97 |
| Cereal box | 1 | 0.0848 | 61.99 | 30.00 | 2.85 |

For the cereal box, raw Rank 0 lies near the upper flap and has only 10 mm
insertion depth. The target-aware selector instead chooses Rank 1 by combining
the existing ranking score with target-center proximity, insertion depth,
contact distance, and a saturated-width penalty. This converts the final choice
from manual visual inspection into a reproducible rule.

## 5. Claims supported by the current evidence

- The proposed bridge can connect an ILGS-derived semantic identity field to
  metric RGB-D geometry and AnyGrasp without retraining AnyGrasp.
- Semantic region steering substantially improves language-target consistency
  in the tested cluttered scene.
- Normal guidance can improve grasp orientation consistency even when target
  localization is already correct.
- Geometry cleanup must account for object shape; planar-support removal helps
  the controller case but is unsafe for the planar cereal box.
- Target-aware final reranking avoids selecting shallow edge grasps solely due
  to a higher SDK score.

## 6. Current limitations

- Results cover two objects in one RGB-D scene and are a feasibility study, not
  a statistically sufficient benchmark.
- `Hit@20mm` measures semantic target localization only. It does not measure
  force closure, lift success, robot reachability, or collision-free execution.
- No calibrated `T_robot_from_camera` transform or physical robot experiment is
  included yet.
- The two ILGS models are target-specific binary models. A single model queried
  for multiple unseen text targets remains future work.
- Selection weights are fixed heuristics validated on the two current cases and
  require evaluation on additional object geometries.

## 7. Next experiments

1. Add at least three more targets with different geometry: a thin object, a
   cylindrical object, and a small irregular object.
2. Repeat on at least two additional RGB-D scenes.
3. Report per-object candidate localization, collision validity, and simulated
   or physical grasp success.
4. Add calibrated camera-to-robot transformation and reachability filtering.
5. Train a multi-object ILGS identity field to replace one-model-per-query
   evaluation.
