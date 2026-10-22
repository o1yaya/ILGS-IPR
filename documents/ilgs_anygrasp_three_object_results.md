# ILGS-to-AnyGrasp Three-Object Feasibility Results

## 1. Experimental scope

This experiment evaluates an end-to-end language-conditioned grasp pipeline on
three targets from two TUM RGB-D sequences:

1. `game controller` in `fr1/desk`: a compact non-planar object in clutter.
2. `cereal box` in `fr1/desk`: an upright approximately planar object.
3. `coke can` in `fr2/coke`: a thin cylindrical object on a tabletop.

The evaluated pipeline is:

`text query -> multi-view pseudo masks -> confidence-weighted ILGS identity field
-> named ILGS masks -> metric RGB-D fusion -> target-region AnyGrasp ->
target-aware final grasp selection`.

Candidate quality is measured by the distance from each predicted grasp center
to the reference target point cloud. `Hit@20mm` is a semantic localization
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
| Coke can | Full | 38 | 38 | 100% | 100% | 100% | 2.46 | 0.0700 | 0.797 |
| Coke can | No region steering | 84 | 50 | 58% | 58% | 58% | 109.89 | 0.2626 | 0.873 |
| Coke can | No normal reranking | 38 | 38 | 100% | 100% | 100% | 2.46 | 0.0700 | 0.797 |
| Coke can | Fixed support-plane filtering | 12 | 12 | 100% | 100% | 100% | 2.69 | 0.1000 | 0.790 |

## 3. Cross-object summary

| Comparison | Macro Hit@20mm | Macro mean distance (mm) | Interpretation |
|---|---:|---:|---|
| Full | 100% | 2.49 | Candidates remain localized to all three queried targets. |
| No region steering | 33.3% | 124.33 | Many high-scoring grasps move to unrelated scene geometry. |
| No normal reranking | 100% | 2.52 | Localization is retained; orientation benefits are object dependent. |

Across the three objects, removing semantic region steering reduces macro
`Hit@20mm` by 66.7 percentage points and increases mean target distance by
approximately 50 times. It also raises the maximum SDK score for every tested
object. Raw AnyGrasp confidence therefore cannot determine whether a grasp
belongs to the language-selected object.

Normal reranking does not change localization for these cases. Its clearest
effect is on the cereal box, where mean normal alignment increases from 0.695
to 0.784. The controller and coke-can candidate sets remain effectively
unchanged. The evidence supports an object-dependent orientation-quality claim,
not a target-localization claim.

## 4. Cylindrical-object support-plane failure

The coke-can experiment exposes a failure mode that `Hit@20mm` alone cannot
measure. Fixed support-plane filtering changes the input as follows:

| Coke-can geometry statistic | Adaptive full pipeline | Fixed plane filtering |
|---|---:|---:|
| Target points | 1,278 | 122 |
| Target point-count ratio | 100% | 9.55% |
| Reference geometry coverage at 10 mm | 100% | 13.30% |
| Bounding-box diagonal ratio | 100% | 30.26% |
| Raw grasp candidates | 38 | 12 |
| Top-1 normal alignment | 0.894 | 0.545 |
| Hit@20mm | 100% | 100% |

The remaining 122 points are still spatially close to the can, so all 12 grasp
centers pass the distance-based hit test. However, only 13.30% of the clean
reference geometry lies within 10 mm of this residual cloud, its bounding-box
diagonal is 30.26% of the reference, and 68.4% of the candidate set has been
removed. Thus, center proximity does not establish that object geometry, grasp
diversity, or grasp orientation has been preserved.

The correct policy is object-adaptive: support-plane cleanup is useful when it
removes surrounding support geometry without explaining the target itself, but
must be disabled when the fitted plane consumes a large fraction of a thin,
planar, or cylindrical target.

The adaptive guard was subsequently tested without manually disabling plane
processing. It detected a dominant plane with inlier ratio 0.821, predicted
that cleanup would retain only 92 points (10.75%), and automatically rejected
the filter with `target_geometry_collapse`. The target-plane hypothesis also
failed surrounding-scene confirmation, with normal alignment 0.052 and a
56.3 mm plane-offset difference. The resulting target retained 856 points and
a full-object extent of approximately `65.3 x 149.8 x 101.0 mm`. Thus the
decision is now made from measured geometry and scene consistency rather than
an object-category-specific switch.

End-to-end inference on this final adaptive coke-can request preserved 100% of
the reference geometry at both 5 mm and 10 mm coverage thresholds and retained
100% `Hit@20mm`. Mean candidate-to-target distance changed only from 2.46 mm to
2.65 mm. The candidate count decreased from 38 to 34 and occupied target-hit
voxels from 36 to 28. The highest-ranked candidate's normal alignment also
dropped from 0.894 to 0.596, so final execution must use the target-aware pose
selector rather than the SDK Top-1 candidate directly.

The complementary acceptance branch was verified on the game controller. The
detected support plane had inlier ratio 0.619; cleanup retained 811 points
(38.15%) and 49.01% of the original bounding-box diagonal. Both values passed
the adaptive guard. Its normal alignment with the surrounding scene plane was
0.9995 and its plane-offset difference was 6.58 mm, so cleanup was applied
automatically and reproduced the previous valid 811-point controller target
without a manual override.

A surrounding-scene plane-consistency check was added after a cereal-box test
showed that point-count and extent retention alone could accept one of the
box's own planar faces. The target-plane normal had alignment 0.045 with the
surrounding support plane and an 87.8 mm plane-offset difference, so cleanup
was rejected as `support_plane_not_confirmed_by_scene`. The complete cereal-box
geometry was restored to 2,049 points with extent approximately
`118.3 x 188.7 x 132.1 mm`.

## 5. Automatically selected final grasps

| Target | Selected rank | SDK score | Width (mm) | Insertion depth (mm) | Target distance (mm) |
|---|---:|---:|---:|---:|---:|
| Game controller | 0 | 0.0912 | 50.80 | 20.00 | 3.97 |
| Cereal box | 1 | 0.0848 | 61.99 | 30.00 | 2.85 |
| Coke can | 1 | 0.0526 | 80.00 | 20.00 | 2.17 |

For the cereal box, the selector rejects raw Rank 0, a shallow grasp near the
upper flap, and chooses Rank 1. For the coke can, the revised selector rejects
SDK Rank 0 because its adaptive-request normal alignment is 0.732, below the
0.80 execution threshold, and selects Rank 1 with normal alignment 0.970. Its
center is 2.17 mm from the target cloud and the RGB overlay places the gripper
across the can body. The predicted 80 mm width is the maximum gripper opening
and must be treated as a pre-grasp opening rather than the final commanded
closure. Full gripper-to-scene collision checking and robot-specific closure
control are still required before physical execution.

## 6. Reconstruction and segmentation observations

The coke-can ILGS model reaches training PSNR 24.92 dB and L1 0.0242 at 30,000
iterations. Across eight held-out views, the binary coke-can masks obtain mean
IoU 0.734. Precision is generally high, while the largest error is
under-segmentation in views where the can is small or weakly observed.

These results are sufficient for the metric RGB-D fusion stage to recover 1,278
target points with local PCA extents of approximately
`159.5 x 61.5 x 46.7 mm`, consistent with a can-like object.

## 7. Claims supported by the current evidence

- ILGS-derived language identity masks can steer AnyGrasp using metric RGB-D
  geometry without retraining AnyGrasp.
- Semantic region steering is the dominant component for language-target
  consistency across the three tested objects.
- Raw AnyGrasp score can increase when semantic localization becomes worse.
- Normal guidance improves orientation quality for some geometries but does not
  consistently alter candidate localization.
- Support-plane processing must preserve target geometry and cannot be enabled
  unconditionally.
- Target-aware final selection can avoid shallow edge grasps that rank highly
  under the SDK score alone.

## 8. Current limitations

- The study contains three objects from two TUM sequences and is still a
  feasibility experiment rather than a statistically sufficient benchmark.
- `Hit@20mm` measures target localization only. It does not measure force
  closure, lift success, reachability, or full-scene collision safety.
- The support-plane ablation needs an explicit geometry-retention metric because
  center-distance hits can remain high after severe target erosion.
- No calibrated `T_robot_from_camera` or physical robot experiment is included.
- The ILGS models are target-specific binary models rather than one shared model
  queried for multiple unseen targets.
- Final-selection weights are fixed heuristics and require broader validation.

## 9. Next experiments

1. Add a small irregular object and a thin flat object in another RGB-D scene.
2. Report target-point retention and candidate diversity alongside `Hit@20mm`.
3. Add full gripper-to-scene collision checking rather than table-plane-only
   clearance.
4. Evaluate top-k grasp coverage and orientation diversity, not only candidate
   center distance.
5. Add calibrated camera-to-robot transformation and physical grasp trials.
