# ILGS 后接 GaussianGrasper / AnyGrasp 复现思路整理

## 1. 当前总体目标

当前目标不是单独复现 GaussianGrasper 原文的全部训练流程，而是把它的核心思想接到已经改进过的 ILGS 流程后面，形成一个适合大论文的完整链路：

```text
ILGS open-vocabulary 3D segmentation
  -> language query 定位目标
  -> 导出 query 对应的 3D Gaussian / point cloud
  -> 清理目标点云并构建局部抓取工作空间
  -> 接 AnyGrasp 生成抓取候选
  -> normal-guided / target-guided reranking
  -> 形成语言驱动 3DGS 抓取实验与论文图
```

换句话说，大论文里可以把这一部分写成：

```text
基于语言增强 3D Gaussian 表示的开放词汇目标定位与抓取候选生成。
```

## 2. 为什么这条路线可行

GaussianGrasper 的核心不是必须完全替换 ILGS，而是利用 3DGS 表示中的语义和几何信息完成：

```text
1. 语言查询目标；
2. 从 3D 场景中分离目标；
3. 将目标和局部场景送入预训练抓取模型；
4. 生成 collision-free grasp candidates；
5. 利用目标几何/法线筛选抓取姿态。
```

我们现在的 ILGS 已经有：

```text
1. open-vocabulary query mask；
2. object identity logits；
3. 训练好的 3D Gaussian point cloud；
4. query-to-object-id 投票能力；
5. 目标 Gaussian 子集导出能力。
```

因此，ILGS 可以承担 GaussianGrasper 中的语言感知和目标定位部分；AnyGrasp 承担抓取候选生成部分。

## 3. 当前已经完成的内容

### 3.1 ILGS 分割结果已经达到可用水平

以 ramen 场景为例，当前 refined/full-refine 结果为：

```text
Overall Mean IoU: 0.8584
Overall Boundary Mean IoU: 0.7728

pork belly IoU: 0.9531
pork belly Boundary IoU: 0.8572
```

这说明 pork belly 这个 query 的 2D/3D 语义定位质量已经足够作为后续抓取目标。

### 3.2 已实现 query 目标 Gaussian 导出

脚本：

```text
export_query_gaussians.py
```

作用：

```text
1. 读取 ILGS 输出的 query mask；
2. 根据 mask 覆盖区域统计 object id；
3. 用 classifier.pth 给 3D Gaussian 预测 object id；
4. 导出 query 对应的 Gaussian 子集和普通点云。
```

当前 pork belly 导出结果：

```text
selected_ids: [120, 212]
selected_gaussians: 18223
usable_view_count: 4
```

输出位置：

```text
/media/server1/data/cxdata/ILGS_grasp_exports/lerf/ramen_refined_masks/iteration_30000/test/pork_belly
```

### 3.3 已完成目标点云清理

脚本：

```text
clean_exported_query_points.py
```

作用：

```text
1. 去掉离群点；
2. 保留最大连通簇；
3. 同步清理 target_points 和 target_gaussians_full；
4. 重新生成 clean bbox 和 clean normals。
```

清理后结果：

```text
raw target points: 18223
clean target points: 17743
removed points: 480
clean target extent: 1.283, 1.229, 1.174
```

CloudCompare 检查结果：

```text
target_points_clean.ply 是紧凑的 pork belly 点云；
没有明显远处离群点；
适合作为抓取目标输入。
```

### 3.4 已生成论文验证图

脚本：

```text
make_grasp_export_figure.py
```

输出：

```text
query_to_grasp_target_figure.png
query_to_grasp_target_figure.pdf
query_to_grasp_target_figure.svg
```

这张图可以用于论文展示：

```text
RGB image
language query mask
selected object-id mask
raw target point cloud
clean target point cloud
export statistics
```

### 3.5 已构建 AnyGrasp 前置输入

脚本：

```text
prepare_anygrasp_input.py
```

作用：

```text
1. 读取 clean target；
2. 从原始 Gaussian point cloud 中裁剪目标周围局部场景；
3. 输出 target / scene crop 的 npy、ply、npz；
4. 生成 grasp_input_metadata.json。
```

当前结果：

```text
target_points_source: target_points_clean.ply
target_points: 17743
scene_crop_points: 86826
target_extent: 1.283, 1.229, 1.174
scene_crop_extent: 2.181, 2.089, 1.995
```

CloudCompare 检查结果：

```text
红色 target 正确落在 pork belly；
白色 scene crop 包含碗/面/局部上下文；
两者尺度和空间位置一致；
可以继续作为 AnyGrasp 输入。
```

### 3.6 已准备 AnyGrasp SDK request 适配脚本

脚本：

```text
prepare_anygrasp_sdk_request.py
run_anygrasp_sdk_inference.py
```

当前状态：

```text
脚本已写好，但暂时先不用；
因为服务器 AnyGrasp license 和 checkpoint 还没有拿到。
```

这两个脚本后续用于：

```text
1. 将 grasp_input/anygrasp_input.npz 转成 AnyGrasp SDK 请求包；
2. 生成 region_steering mask，让 AnyGrasp 聚焦 pork belly；
3. 调用 AnyGrasp SDK 推理；
4. 导出 grasp candidates；
5. 根据 target normals 做 normal-guided reranking。
```

### 3.7 AnyGrasp 环境已经基本装好

服务器安装位置：

```text
/media/server1/data/cxdata/anygrasp
```

conda 环境：

```text
anygrasp
```

已经成功：

```text
MinkowskiEngine: 0.5.4
graspnetAPI: import ok
AnyGrasp feature id: N62531636859492611945
```

已经提交官方 license 表单，目前等待官方 GitHub/email 邀请和模型文件。

## 4. 当前卡点

### 4.1 等待 AnyGrasp 官方授权

目前必须等待官方返回：

```text
license
checkpoint_detection.tar
```

收到后放到：

```text
/media/server1/data/cxdata/anygrasp/anygrasp_sdk/grasp_detection/license
/media/server1/data/cxdata/anygrasp/anygrasp_sdk/grasp_detection/log/checkpoint_detection.tar
```

然后验证：

```bash
cd /media/server1/data/cxdata/anygrasp/anygrasp_sdk/grasp_detection
conda activate anygrasp
python -c "from gsnet import check_license; check_license('license')"
```

### 4.2 PyTorch 暂时看不到 GPU

之前环境中出现过：

```text
torch.cuda.is_available(): False
```

编译阶段已经通过：

```bash
TORCH_CUDA_ARCH_LIST=8.6
```

绕过了自动 GPU 架构推断问题。

但真正推理 AnyGrasp 时必须解决 GPU 可见性。后续需要检查：

```bash
nvidia-smi
echo $CUDA_VISIBLE_DEVICES
python - <<'PY'
import torch
print(torch.__version__, torch.version.cuda)
print(torch.cuda.is_available())
print(torch.cuda.device_count())
PY
```

### 4.3 当前坐标还不是机器人真实坐标

当前 grasp input 仍在：

```text
ILGS / 3DGS reconstruction frame
```

这对论文离线实验和抓取候选可视化已经够用。

但如果要真实机械臂执行，还需要：

```text
1. metric scale；
2. camera coordinate transform；
3. robot base / gripper 外参；
4. gripper 尺寸和碰撞模型；
5. 从 AnyGrasp pose 到机器人末端 pose 的坐标转换。
```

## 5. 接下来要做什么

### 5.1 近期任务：等待并配置 AnyGrasp license

收到官方文件后：

```text
1. 放置 license；
2. 放置 checkpoint_detection.tar；
3. 运行 check_license；
4. 确认 AnyGrasp SDK 可以 import；
5. 确认 torch 能看到 GPU。
```

### 5.2 生成 AnyGrasp request

在 license/checkpoint 到位后，回到 ILGS 导出的 grasp input：

```bash
cd ~/vsproject1/ILGS_release-main
conda activate anygrasp

python prepare_anygrasp_sdk_request.py \
  --grasp_input_dir /media/server1/data/cxdata/ILGS_grasp_exports/lerf/ramen_refined_masks/iteration_30000/test/pork_belly/grasp_input \
  --region_radius 0.015
```

检查输出：

```text
anygrasp_sdk_request/points_region_preview.ply
anygrasp_sdk_request/anygrasp_sdk_request_report.json
```

目标：

```text
红色 region mask 应主要覆盖 pork belly；
浅色点云为局部场景；
不要让 region mask 大面积覆盖碗和面。
```

### 5.3 运行 AnyGrasp 推理

示例：

```bash
export ANYGRASP_SDK_DIR=/media/server1/data/cxdata/anygrasp/anygrasp_sdk/grasp_detection
export ANYGRASP_CKPT=/media/server1/data/cxdata/anygrasp/anygrasp_sdk/grasp_detection/log/checkpoint_detection.tar

python run_anygrasp_sdk_inference.py \
  --request /media/server1/data/cxdata/ILGS_grasp_exports/lerf/ramen_refined_masks/iteration_30000/test/pork_belly/grasp_input/anygrasp_sdk_request \
  --sdk_path "$ANYGRASP_SDK_DIR" \
  --checkpoint_path "$ANYGRASP_CKPT" \
  --normal_guided \
  --top_k 50
```

输出：

```text
grasp_candidates_raw.npy
grasp_candidates_selected.npy
grasp_candidates.json
grasp_candidates.csv
grasp_candidate_centers_centered.ply
grasp_candidate_centers_world.ply
anygrasp_inference_report.json
```

### 5.4 可视化抓取结果

后续需要补一个脚本：

```text
visualize_grasp_candidates.py
```

目标：

```text
1. 在 scene_crop 上画抓取中心；
2. 用颜色表示 grasp score；
3. 可选画 top-k gripper axes；
4. 生成论文图：
   language query -> target extraction -> local workspace -> grasp candidates。
```

### 5.5 做消融实验

建议至少做这些对比：

```text
1. raw target vs clean target；
2. without region steering vs with region steering；
3. AnyGrasp score only vs normal-guided reranking；
4. ILGS official mask vs refined/full-refine mask；
5. 不同 query，例如 pork belly / egg / chopsticks。
```

## 6. 大论文中可以怎么写

### 6.1 方法模块命名建议

可以写成三个模块：

```text
1. Query-guided 3D Gaussian Target Extraction
2. Local Grasp Workspace Construction
3. Normal-guided Grasp Candidate Selection
```

### 6.2 论文贡献点表达

可以强调：

```text
1. 将 ILGS 的 open-vocabulary 3D segmentation 能力扩展到语言引导抓取场景；
2. 提出从 query mask 到 3D Gaussian target 的导出和清理流程；
3. 构建面向抓取模型的局部场景输入；
4. 利用目标法线和语言目标区域对预训练抓取候选进行筛选；
5. 形成从语言查询到抓取候选的完整 3DGS 下游任务链路。
```

### 6.3 当前最适合放论文的图

建议图顺序：

```text
Figure A: ILGS query mask refinement result
Figure B: query-to-3D target extraction
Figure C: raw target vs clean target
Figure D: local grasp workspace
Figure E: AnyGrasp candidate visualization
Figure F: normal-guided candidate selection / top grasp
```

## 7. 当前阶段一句话总结

当前已经完成了从 ILGS 语言查询结果到干净 3D 目标点云和局部抓取工作空间的构建，并成功安装了 AnyGrasp 的主要环境依赖；下一步等待官方 license 和 checkpoint，随后运行 AnyGrasp 推理并生成抓取候选及论文可视化结果。
