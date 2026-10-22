# ILGS-IPR 代码改动、仓库入口与实验提升

更新时间：2026-10-22

## 1. 仓库定位

本目录以公开 ILGS 实现为基础，加入了 Identity-Preserving Reliability（IPR）预处理、置信度加权身份监督、受控多种子训练和补充评测工具。因此，该目录不能再描述为“未经修改的官方 ILGS 仓库”。

最终论文方法只包含以下变化：

1. 只用训练视角的身份掩码进行局部结构清理，不创建新的身份 ID。
2. 对同一身份在不同训练视角中的对象裁剪计算查询无关的 CLIP 图像一致性。
3. 用连通区域面积统计识别大范围混合区域风险。
4. 将上述对象级判断写入像素置信图，并只重加权 ILGS 的二维身份分类损失。

高斯表示、语言特征分支、三维正则项和文本查询推理流程保持不变。

## 2. 仓库结构

| 路径 | 作用 | 是否为最终实验入口 |
|---|---|---:|
| `train.py` | ILGS 训练与 IPR 置信度加权 | 是 |
| `arguments/` | 数据、模型和优化参数；包含 `object_confidence_path` | 是 |
| `scene/`, `gaussian_renderer/`, `utils/` | ILGS/3DGS 核心表示与渲染 | 是 |
| `refine_object_masks.py` | 训练视角身份掩码的局部结构清理及基础置信度 | 是 |
| `refine_object_masks_semantic_area.py` | 跨视角一致性、面积风险和最终置信图 | 是 |
| `script/subset_ipr_training_views.py` | 只保留训练视角对应的掩码 | 是 |
| `script/prepare_ipr_strict_protocol.sh` | LERF-Mask 最终预处理 | 是 |
| `script/prepare_3dovs_ipr_consistency.sh` | 3D-OVS 最终预处理 | 是 |
| `script/run_ipr_strict_protocol_2gpu.sh` | LERF-Mask 双 GPU 多种子训练 | 是 |
| `script/run_3dovs_controlled_2gpu.sh` | 3D-OVS 双 GPU 多种子训练 | 是 |
| `script/eval_*`, `script/summarize_*` | 评测、审计和汇总 | 是 |
| `config/experiments/paper_final.env` | 场景、种子、阈值和结果路径的唯一配置入口 | 是 |
| `documents/EXPERIMENTS_FINAL.md` | 最终实验运行说明 | 是 |
| `script/export_*`, `script/generate_paper_experiment_figures.py` | 使用真实结果生成论文图 | 否，仅用于材料复现 |
| `dataset/`, `checkpoints/`, `results/`, `output/` | 本地数据、权重和运行产物，均由 Git 忽略 | 否 |

`script/README_FINAL.md` 列出了当前保留的最终脚本。旧词表协议、
DEVA/SAM2 掩码变体、官方论文复现尝试、抓取系统以及文稿编辑脚本已从
公开代码树移除。

## 3. 相对 ILGS 的具体代码改动

### 3.1 训练参数与可复现性

- `arguments/__init__.py` 增加 `object_confidence_path`，允许为每个训练图像提供灰度置信图。
- `train.py` 增加 `--seed`，并将种子传入 `utils.general_utils.safe_state`。
- `utils/general_utils.py` 同时设置 Python、NumPy、PyTorch 和 CUDA 随机种子。
- `preprocess.py` 支持显式图像目录和本地 OpenCLIP 权重，避免依赖在线下载。

### 3.2 身份损失

设像素 (p) 的身份交叉熵为 \(\ell_p\)，ILGS 动态离群门控为 \(M_p\in\{0,1\}\)，IPR 置信度为 \(W_p\in[0,1]\)，身份类别数为 \(C\)。

公开代码的原始写法在门控后仍对整幅图取均值：

\[
L_{\mathrm{id}}^{\mathrm{released}}
=\frac{1}{\log C}\operatorname{mean}_p(M_p\ell_p).
\]

当前受控基线先按有效像素重新归一化：

\[
L_{\mathrm{id}}^{\mathrm{controlled}}
=\frac{\sum_p M_p\ell_p}{\log C\,\max(1,\sum_p M_p)}.
\]

IPR 在完全相同的受控训练代码上只加入可靠性权重：

\[
L_{\mathrm{id}}^{\mathrm{IPR}}
=\frac{\sum_p M_pW_p\ell_p}
{\log C\,\max(1,\sum_p M_pW_p)}.
\]

这一区别很重要：论文中的“ILGS 受控基线”不是 ILGS 原论文表格的直接复现值，而是与 IPR 共用当前损失归一化、训练入口和评测代码的配对基线。

### 3.3 置信图读取

`train.py` 对置信图执行以下处理：

1. 根据当前相机的 `image_name` 读取同名 PNG。
2. 将 8 位灰度值转换到 `[0,1]`。
3. 尺寸不一致时使用最近邻插值，以避免产生新的连续标签边界。
4. 缓存 CPU 张量，使用时再移动到当前 GPU。
5. 缺少置信图时退化为受控基线，不中断训练。

### 3.4 查询无关可靠性估计

`refine_object_masks_semantic_area.py` 的最终分支为 `--clip_consistency`：

1. 按身份 ID 收集训练视角中的连通区域。
2. 对每个实例生成保留对象、替换背景的裁剪图。
3. 使用 OpenCLIP ViT-B/16 编码裁剪图，不输入评测查询文本。
4. 对同一身份的裁剪特征计算两两余弦相似度均值，得到跨视角一致性。
5. 一致性低于阈值的身份被降权。
6. 根据连通区域面积占比的中位数、90 分位数和最大值识别大范围混合区域，并赋予更低权重。
7. 对象权重与 `refine_object_masks.py` 生成的基础像素置信图相乘，得到最终 `W(p)`。

最终配置关闭额外的逐视角可见性乘子。因此，当前 IPR 是“基础置信度 + 跨视角一致性门控 + 大范围区域风险门控”，不是早期的文本词表评分版本。

### 3.5 身份空间保持

- `--confidence_only` 使可靠性模块只输出置信图和审计报告。
- 最终训练使用 `object_mask_refined_trainonly_strict` 中已有的 ID。
- 不做全局重编号，不自动合并身份，也不读取测试真值。
- `merge_candidates.json` 只记录候选关系，不参与最终训练。

### 3.6 标准评测支持

- `render_all.py` 增加帧名清单和按指定帧渲染。
- `segmentation_mask_stream.py` 增加显式查询文件、自动编码器权重、输出目录、训练/测试分支和帧名映射。
- `script/eval_lerf_ovs_standard.py` 按帧-查询对计算标准 LERF-OVS mIoU 与 mAcc@0.25。
- `script/audit_lerf_ovs_reuse.py` 检查模型来源图像和官方标注帧是否兼容，防止只因指标名称相同就错误复用检查点。

## 4. 最终方法与协议

最终变体名：`strict_trainview_consistency`

| 项目 | 最终设置 |
|---|---|
| 可靠性视角 | 仅训练视角 |
| 语义可靠性 | 查询无关的跨视角 OpenCLIP 图像一致性 |
| 一致性阈值 | `0.75` |
| 大区域风险 | 启用 |
| 逐视角可见性乘子 | 关闭 |
| 身份 ID | 保留已有 ID |
| 评测查询/测试标注参与预处理 | 否 |
| 主实验种子 | `0, 1, 2` |
| LERF-Mask 分辨率参数 | `1` |
| 3D-OVS 分辨率参数 | `4` |

阈值、场景和结果根目录统一定义在 `config/experiments/paper_final.env`。LERF-Mask 和 3D-OVS 的最终预处理脚本均接受 `CONSISTENCY_THRESHOLD`，默认值均为 `0.75`。

## 5. 已验证的提升

以下数值均来自配对的受控实验，不与 ILGS 原论文报告值直接混合。

### 5.1 LERF-Mask：3 场景，3 种子

| 方法 | mIoU | mBIoU | 相对提升 |
|---|---:|---:|---:|
| ILGS 受控基线 | 70.77 | 66.35 | - |
| ILGS + IPR | 74.46 | 69.91 | +3.69 / +3.56 |

场景均值上，Ramen、Figurines 和 Teatime 的两项指标均提高，但不同场景和种子的波动不同，不能表述为普遍提高训练稳定性。

### 5.2 3D-OVS：10 场景，3 种子

| 方法 | mIoU | mBIoU | 相对提升 |
|---|---:|---:|---:|
| ILGS 受控基线 | 82.01 | 75.69 | - |
| ILGS + IPR | 86.78 | 80.93 | +4.77 / +5.24 |

两个指标的场景均值均在 9/10 个场景提高。收益集中于 Bench、Blue Sofa、Office Desk 等部分场景；Covered Desk 等场景显示该方法仍具有明显的场景依赖性。

### 5.3 标准 LERF-OVS：4 场景，3 种子

| 方法 | mIoU | mAcc@0.25 | 相对提升 |
|---|---:|---:|---:|
| ILGS 受控基线 | 50.51 | 58.41 | - |
| ILGS + IPR | 52.02 | 60.23 | +1.51 / +1.82 |

该平均提升主要来自 Waldo Kitchen。Ramen 和 Figurines 的 mIoU 略有下降，因此不能声称四个场景全部改善。LERF-OVS 的帧-查询对聚合与 LERF-Mask 指标定义不同，两组绝对值不能直接比较。

### 5.4 阈值敏感性

种子 0 的阈值扫描覆盖 `0.65, 0.70, 0.75, 0.80, 0.85`。不同数据集的最佳点并不一致，但 `0.75` 在 3D-OVS 三场景子集上取得最高平均值，并被固定用于最终跨数据集配置。该实验支持“阈值附近可用”，不支持“0.75 对所有场景最优”。

## 6. 结果解释边界

1. **受控基线不是论文原值。** 它与 IPR 共用当前代码、有效像素归一化、解码器和评测实现。
2. **IPR 不恢复真实轨迹。** 它降低疑似错误监督的贡献，不能保证每个被降权区域一定是噪声。
3. **平均提升不等于逐场景提升。** 标准 LERF-OVS 中有轻微退化，3D-OVS 也存在场景差异。
4. **固定阈值仍是局限。** 当前阈值由开发实验确定，尚未证明可自动迁移到任意数据集。
5. **预处理有额外成本。** 需要 OpenCLIP 裁剪编码、置信图存储和离线审计；推理阶段不增加新的网络分支。

## 7. 最终复现入口

从仓库根目录进入 `ILGS` Conda 环境后加载统一配置：

```bash
set -a
source config/experiments/paper_final.env
set +a
```

LERF-Mask 预处理与训练：

```bash
DATASET_ROOT="$LERF_DATASET_ROOT" \
SCENES="$LERF_SCENES" \
CONSISTENCY_THRESHOLD="$IPR_THRESHOLD" \
bash script/prepare_ipr_strict_protocol.sh

EXTERNAL_ROOT="$LERF_MAIN_ROOT" \
DATASET_ROOT="$LERF_DATASET_ROOT" \
SCENES="$LERF_SCENES" \
VARIANTS="$LERF_VARIANT" \
SEEDS="$LERF_SEEDS" \
RESOLUTION=1 \
bash script/run_ipr_strict_protocol_2gpu.sh
```

3D-OVS 预处理与训练：

```bash
DATASET_ROOT="$OVS_DATASET_ROOT" \
SCENES="$OVS_SCENES" \
CONSISTENCY_THRESHOLD="$IPR_THRESHOLD" \
bash script/prepare_3dovs_ipr_consistency.sh

EXTERNAL_ROOT="$OVS_MAIN_ROOT" \
DATASET_ROOT="$OVS_DATASET_ROOT" \
SCENES="$OVS_SCENES" \
VARIANTS="$OVS_VARIANT" \
SEEDS="$OVS_SEEDS" \
RESOLUTION=4 \
bash script/run_3dovs_controlled_2gpu.sh
```

更完整的评测与报告路径见 `documents/EXPERIMENTS_FINAL.md`。

## 8. 发布仓库边界

仓库仅保留 ILGS 核心、IPR 最终方法、受控训练评测、消融、阈值敏感性、
LERF-OVS 附录评测和最终论文图生成入口。旧词表、DEVA/SAM2、trajectory、
v2-anchor、抓取系统、PPT/DOCX/SVG 编辑器和失败复现脚本不属于发布版本。

`.gitignore` 排除了数据集、检查点、模型输出、生成图和临时目录；原始
CSV/JSON 报告应随论文补充材料或数据存档单独发布，而不是提交到源码仓库。

## 9.代码仓库

[o1yaya/ILGS-IPR](https://github.com/o1yaya/ILGS-IPR)
