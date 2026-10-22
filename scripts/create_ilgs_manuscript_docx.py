from __future__ import annotations

import html
import os
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(r"D:\wlxy")
OUT_FILE = OUT_DIR / "面向开放词汇三维语义分割的身份感知伪标签与掩码预测优化方法_初稿.docx"
FIG_3DOVS = ROOT / "paper_figures" / "fig_3dovs_dataset_examples.png"


def xml_text(text: str) -> str:
    return escape(text)


def run(text: str, bold: bool = False, italic: bool = False) -> str:
    props = ""
    if bold:
        props += "<w:b/>"
    if italic:
        props += "<w:i/>"
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f"<w:r>{rpr}<w:t xml:space=\"preserve\">{xml_text(text)}</w:t></w:r>"


def para(text: str = "", style: str | None = None, align: str | None = None) -> str:
    ppr = ""
    if style:
        ppr += f"<w:pStyle w:val=\"{style}\"/>"
    if align:
        ppr += f"<w:jc w:val=\"{align}\"/>"
    ppr = f"<w:pPr>{ppr}</w:pPr>" if ppr else ""
    return f"<w:p>{ppr}{run(text)}</w:p>"


def heading(text: str, level: int = 1) -> str:
    style = "Heading1" if level == 1 else "Heading2" if level == 2 else "Heading3"
    return para(text, style=style)


def table(headers: list[str], rows: list[list[str]]) -> str:
    def cell(text: str, bold: bool = False) -> str:
        return (
            "<w:tc><w:tcPr><w:tcW w:w=\"1800\" w:type=\"dxa\"/></w:tcPr>"
            f"<w:p>{run(text, bold=bold)}</w:p></w:tc>"
        )

    tbl_pr = (
        "<w:tblPr><w:tblStyle w:val=\"TableGrid\"/>"
        "<w:tblW w:w=\"0\" w:type=\"auto\"/>"
        "<w:tblBorders>"
        "<w:top w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "<w:left w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "<w:bottom w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "<w:right w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "<w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "<w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
        "</w:tblBorders></w:tblPr>"
    )
    header_xml = "<w:tr>" + "".join(cell(h, True) for h in headers) + "</w:tr>"
    rows_xml = "".join("<w:tr>" + "".join(cell(c) for c in row) + "</w:tr>" for row in rows)
    return f"<w:tbl>{tbl_pr}{header_xml}{rows_xml}</w:tbl>"


def image_para(rel_id: str, cx: int, cy: int, caption: str) -> str:
    # cx/cy in EMUs. 1 inch = 914400 EMU.
    drawing = f"""
    <w:p>
      <w:pPr><w:jc w:val="center"/></w:pPr>
      <w:r>
        <w:drawing>
          <wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" distT="0" distB="0" distL="0" distR="0">
            <wp:extent cx="{cx}" cy="{cy}"/>
            <wp:effectExtent l="0" t="0" r="0" b="0"/>
            <wp:docPr id="1" name="Figure"/>
            <wp:cNvGraphicFramePr/>
            <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
              <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
                  <pic:nvPicPr>
                    <pic:cNvPr id="0" name="fig_3dovs_dataset_examples.png"/>
                    <pic:cNvPicPr/>
                  </pic:nvPicPr>
                  <pic:blipFill>
                    <a:blip r:embed="{rel_id}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>
                    <a:stretch><a:fillRect/></a:stretch>
                  </pic:blipFill>
                  <pic:spPr>
                    <a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                  </pic:spPr>
                </pic:pic>
              </a:graphicData>
            </a:graphic>
          </wp:inline>
        </w:drawing>
      </w:r>
    </w:p>
    """
    return drawing + para(caption, align="center")


def build_document_xml(include_image: bool) -> str:
    body: list[str] = []
    body.append(para("面向开放词汇三维语义分割的身份感知伪标签与掩码预测优化方法", style="Title", align="center"))
    body.append(para("陈旭", align="center"))
    body.append(para("（单位、城市、邮编待补充）", align="center"))

    body.append(heading("摘  要", 1))
    body.append(
        para(
            "开放词汇三维语义分割旨在根据自然语言查询从三维场景中分割任意语义目标。"
            "Identity-aware Language Gaussian Splatting (ILGS) 通过联合学习三维高斯外观、语言特征和身份场，在 LERF-Mask 等数据集上取得了较好的性能。"
            "然而，ILGS 的性能上限受到两个环节限制：一是训练阶段使用的 object mask 伪标签可能存在碎片、边界误差和跨视角身份不一致；二是测试阶段根据文本相似度和 identity region growing 生成 query mask 时，容易出现区域扩张漂移和局部部件失配。"
            "针对上述问题，本文提出一种身份感知伪标签与掩码预测优化方法。首先，在不重新引入额外跟踪模型的前提下，对已有 object mask 进行连通域、边界不确定性和跨视角面积一致性分析，生成修正后的身份伪标签和置信度图，并在训练中使用置信度加权身份损失。"
            "其次，在预测阶段引入身份一致性后处理，通过种子区域保护抑制错误扩张，并通过局部连通分量选择细化小部件目标。"
            "在 LERF-Mask 的 figurines、teatime 和 ramen 场景上的实验表明，训练前伪标签优化在 figurines 场景中将 mIoU 从 65.99% 提升至 75.21%；预测后处理在 teatime 和 ramen 场景中分别将 mIoU 提升至 89.19% 和 85.56%。"
            "结果说明，开放词汇三维语义分割不仅依赖语言特征表示，还需要同时优化身份伪标签质量和查询掩码生成策略。"
        )
    )
    body.append(para("关键词：开放词汇三维语义分割；三维高斯泼溅；伪标签优化；身份一致性；掩码后处理"))
    body.append(para("中图分类号：TP391    文献标识码：A        DOI：待补充"))

    body.append(heading("1 引言", 1))
    body.append(
        para(
            "三维场景理解是机器人感知、增强现实、数字孪生和具身智能中的关键问题。传统三维语义分割通常依赖封闭类别集合，难以处理真实应用中不断变化的开放语义查询。"
            "近年来，CLIP 等视觉语言模型使开放词汇识别成为可能，NeRF 和 3D Gaussian Splatting 等三维表示进一步推动了从二维语言特征向三维场景的映射。"
            "在这一方向上，LERF、LangSplat、Feature-3DGS 和 ILGS 等方法尝试将语言特征嵌入三维辐射场或高斯场中，使用户能够通过自然语言查询三维目标。"
        )
    )
    body.append(
        para(
            "ILGS 的重要特点是引入身份感知学习，将语言特征与 object-level identity labels 共同建模，从而缓解纯语言特征在局部区域中的噪声。"
            "但是，ILGS 公开代码中的身份标签主要来自已经准备好的 object_mask，而 DEVA 或 zero-shot tracker 并未作为可运行模块集成在训练流程中。"
            "这意味着，如果 object_mask 本身存在错误，后续三维身份场也会继承这些伪标签偏差。另一方面，即便三维身份场学习正确，测试阶段的文本查询 mask 仍可能因 region growing 引入相邻背景或物体，导致最终评估结果下降。"
        )
    )
    body.append(
        para(
            "本文围绕上述两个瓶颈展开改进，提出身份感知伪标签与掩码预测优化方法。该方法包括两个互补模块：训练前的 Identity-aware Pseudo-label Refinement (IPR) 和预测后的身份一致性掩码优化。"
            "前者作用于数据预处理和训练监督，后者作用于最终 query mask 生成。通过将错误来源拆分为训练监督误差和预测生成误差，本文为 ILGS 类方法提供了一个更可诊断、可复现的优化路径。"
        )
    )

    body.append(heading("2 相关工作", 1))
    body.append(
        para(
            "开放词汇二维视觉识别通常依赖大规模视觉语言预训练模型。CLIP 通过图像文本对比学习获得了强泛化能力，随后 LSeg、MaskCLIP、GroundingDINO 和 Segment Anything 等方法进一步推动了开放词汇检测与分割。"
            "这些方法能够从二维图像中提取语义线索，但缺少跨视角一致的三维表示。"
        )
    )
    body.append(
        para(
            "三维开放词汇分割方法尝试将二维视觉语言特征投影或蒸馏到三维场景中。LERF 将语言特征嵌入 NeRF 表示，LangSplat 和 Feature-3DGS 则利用 3DGS 的高效渲染能力表示开放词汇语义。"
            "ILGS 进一步引入身份感知约束，用 object-level identity labels 改善三维语义聚合。然而，自动生成的身份伪标签并不完全可靠，且公开流程主要默认这些标签已经准备好，缺少对伪标签质量的显式修正。"
        )
    )

    body.append(heading("3 方法", 1))
    body.append(heading("3.1 方法概述", 2))
    body.append(
        para(
            "本文方法建立在 ILGS 框架基础上。给定多视角图像、COLMAP 相机参数、语言特征和原始 object_mask，方法首先生成 refined object mask 和 object confidence map。"
            "训练阶段保持外观重建损失和语言特征损失不变，仅对身份分类损失进行置信度加权。测试阶段，模型渲染得到每个视角的图像、语言特征图和身份 logits，并根据文本查询生成初始 mask。"
            "随后，后处理模块根据身份区域的一致性、面积漂移、边界接触和局部连通性修正最终 query mask。"
        )
    )
    body.append(heading("3.2 身份感知伪标签优化", 2))
    body.append(
        para(
            "给定原始 object_mask，本文不从 RGB 图像重新生成伪标签，而是在已有身份编号体系上进行保守修正。这样可以避免破坏数据集中跨视角建立的 identity label 关系。"
            "具体而言，首先对每个身份类别执行连通域分析，将面积过小且与周围主导身份不一致的孤立连通域视为碎片噪声，并将其重分配给邻域内占比最高的身份或降低其训练置信度。"
            "其次，对身份边界区域赋予较低置信度，以减弱自动分割边缘误差对训练的影响。最后，统计同一身份在不同视角中的面积分布，当某一视角中的身份面积显著偏离稳定分布时，将对应区域标记为面积不一致区域。"
        )
    )
    body.append(
        para(
            "优化后的伪标签包括 object_mask_refined 和 object_confidence_refined。训练时，身份分类损失写为："
        )
    )
    body.append(para("L_obj = sum_i c_i CE(p_i, y_i) / max(sum_i c_i, eps)", align="center"))
    body.append(
        para(
            "其中，p_i 表示像素 i 的身份预测，y_i 表示修正后的身份伪标签，c_i 表示该像素的伪标签置信度。"
            "该设计的目的不是强行改变所有标签，而是在不可靠区域降低错误监督的影响。"
        )
    )
    body.append(heading("3.3 身份一致性的掩码预测后处理", 2))
    body.append(
        para(
            "ILGS 官方预测流程首先计算文本查询与渲染语言特征之间的 CLIP 相似度，并选择相似度最高的 identity 区域作为初始种子区域，再根据相似度差异进行邻域扩张。"
            "实验观察表明，该过程存在两类典型错误。第一类是区域扩张漂移：初始 identity 与目标高度重合，但 region growing 将相邻桌面、背景或其他物体纳入 mask。"
            "第二类是部件级目标失配：对于 spoon handle 等小部件，完整 identity 区域通常覆盖更大的物体，无法精确对应查询目标。"
        )
    )
    body.append(
        para(
            "针对扩张漂移，本文比较官方扩张结果和初始种子区域在面积、边界接触和相似度分布上的差异。当扩张结果出现明显面积漂移或异常边界接触时，优先保留 seed-ref mask。"
            "针对部件级目标，本文在候选 identity 区域内部选择局部连通分量，并综合考虑相似度对比度、面积先验、区域紧致度、平均文本相似度和边界惩罚。候选评分定义为："
        )
    )
    body.append(para("S = 0.35 C_contrast + 0.30 C_area + 0.25 C_compact + 0.10 C_mean - 0.25 B_border", align="center"))
    body.append(
        para(
            "与只依赖平均文本相似度相比，该评分更强调空间结构和局部可靠性，因此能够避免高相似度但空间位置错误的大区域被误选。"
            "需要说明的是，后处理模块不改变训练得到的三维高斯参数，也不改变评估脚本的 IoU 计算逻辑，只改变测试阶段 query mask 的生成方式。"
        )
    )

    body.append(heading("4 实验设置", 1))
    body.append(
        para(
            "实验主要在 LERF-Mask 的 figurines、teatime 和 ramen 三个场景上进行，评估指标为 mean Intersection over Union (mIoU) 和 mean Boundary IoU (mBIoU)。"
            "所有评估均沿用仓库中的 script/eval_lerf_mask.py。硬件环境为 NVIDIA GeForce RTX 3090 24 GB，训练迭代次数为 30,000。"
            "由于 ILGS 原论文未报告单场景训练时间，本文主要报告硬件配置、训练迭代数和评估协议，训练耗时可作为补充实现信息。"
        )
    )
    body.append(
        para(
            "为分析不同模块的作用，本文设置 Official-fixed、IPR、Post-process 和 IPR + Post-process 四组实验。Official-fixed 保持官方 mask 生成逻辑，仅修复测试索引、查询名称和文件命名与评估脚本不一致的问题；IPR 使用训练前伪标签优化；Post-process 仅使用预测阶段后处理；IPR + Post-process 同时使用两个模块。"
        )
    )

    body.append(heading("5 实验结果与分析", 1))
    body.append(para("表 1 给出了训练前身份伪标签优化的结果。"))
    body.append(table(
        ["方法", "figurines mIoU", "figurines mBIoU", "teatime mIoU", "teatime mBIoU", "ramen mIoU", "ramen mBIoU", "Avg. mIoU", "Avg. mBIoU"],
        [
            ["Official-fixed", "65.99", "64.22", "72.87", "69.55", "79.21", "72.00", "72.69", "68.59"],
            ["IPR", "75.21", "73.12", "72.79", "69.95", "79.57", "71.89", "75.86", "71.65"],
            ["Gain", "+9.22", "+8.89", "-0.08", "+0.40", "+0.36", "-0.11", "+3.17", "+3.06"],
        ],
    ))
    body.append(
        para(
            "可以看到，IPR 在 figurines 场景上带来最明显提升，说明该场景原始 object_mask 的碎片化和跨视角不一致对三维身份学习影响较大。"
            "在 teatime 和 ramen 场景中，IPR 对 mIoU 的提升较小，说明这两个场景的主要误差更多来自预测阶段的 mask 生成策略。"
        )
    )
    body.append(para("表 2 给出了预测后掩码优化结果。"))
    body.append(table(
        ["方法", "teatime mIoU", "teatime mBIoU", "ramen mIoU", "ramen mBIoU", "figurines mIoU", "figurines mBIoU"],
        [
            ["Official-fixed", "72.87", "69.55", "79.21", "72.00", "65.99", "64.22"],
            ["Post-process", "89.19", "85.84", "85.56", "77.34", "65.99", "64.22"],
        ],
    ))
    body.append(
        para(
            "后处理在 teatime 和 ramen 上提升明显，主要修正了 sheep、plate、spoon handle 和 pork belly 等目标中的扩张漂移和部件级失配。"
            "在 figurines 中，主要失败模式是 top-1 identity seed 选择错误和文本提示敏感性，例如 red toy chair 的第二高相似度 identity 才与真实目标高度重合，因此当前后处理对该场景改善有限。"
        )
    )

    body.append(heading("6 3DOVS 数据集扩展检查", 1))
    body.append(
        para(
            "本文还初步检查了 3DOVS 数据集。当前本地数据集中包含 bed、bench、blue_sofa、covered_desk、lawn、office_desk、room、snacks、sofa 和 table 等场景，每个场景包含 RGB 图像、COLMAP 稀疏重建结果和少量测试分割标注。"
            "然而，3DOVS 当前目录尚不直接满足 ILGS 训练格式，因为其缺少全量 object_mask 和 images_train 划分。后续若将 3DOVS 纳入完整实验，需要先将 segmentations 转换为 test_mask，并额外生成训练阶段所需的 object_mask。"
        )
    )
    if include_image:
        body.append(image_para("rIdImage1", 6000000, 7600000, "图 1  3DOVS 数据集示例。左列为 RGB 图像，右列为测试分割标注叠加结果。"))

    body.append(heading("7 讨论", 1))
    body.append(
        para(
            "实验结果表明，ILGS 的误差来源可以拆分为训练监督误差和预测生成误差。训练监督误差主要来自 object-level pseudo labels 的碎片、边界错标和跨视角身份不一致，适合通过 IPR 在训练前修正。"
            "预测生成误差发生在测试阶段，即使三维身份场已经学习到较正确的目标区域，text-query mask 仍可能因为 region growing 或局部部件尺度不匹配而失败。"
        )
    )
    body.append(
        para(
            "当前方法仍存在局限。首先，预测后处理中的面积、紧致度和边界惩罚仍包含启发式设计，尚未形成完全可学习的通用策略。"
            "其次，对于 figurines 中的 top-1 seed 选择错误，当前方法只能诊断，不能稳定修正。最后，3DOVS 数据集仍需要额外的数据适配和伪标签生成流程后才能纳入完整实验。"
        )
    )

    body.append(heading("8 结论", 1))
    body.append(
        para(
            "本文针对 ILGS 在开放词汇三维语义分割中的伪标签质量和查询掩码生成问题，提出身份感知伪标签与掩码预测优化方法。"
            "训练前 IPR 通过连通域、边界不确定性和跨视角面积一致性分析生成更可靠的身份监督；预测后处理通过种子保护和局部部件细化修正 query mask。"
            "实验结果表明，该方法能够在不同错误模式下改善 LERF-Mask 场景的分割结果，为开放词汇三维语义分割中的伪标签治理和预测修正提供了可复现的改进方向。"
        )
    )

    body.append(heading("参考文献", 1))
    refs = [
        "RADFORD A, KIM J W, HALLACY C, et al. Learning transferable visual models from natural language supervision[C]. International Conference on Machine Learning, 2021: 8748-8763.",
        "KERR J, KIM C M, GOLDBERG K, et al. LERF: Language embedded radiance fields[C]. IEEE/CVF International Conference on Computer Vision, Paris, France, 2023: 19729-19739.",
        "QIN M, LI W, ZHOU J, et al. LangSplat: 3D language Gaussian splatting[C]. IEEE/CVF Conference on Computer Vision and Pattern Recognition, Seattle, USA, 2024.",
        "ZHOU S, CHANG H, JIANG S, et al. Feature 3DGS: Supercharging 3D Gaussian splatting to enable distilled feature fields[C]. IEEE/CVF Conference on Computer Vision and Pattern Recognition, Seattle, USA, 2024.",
        "YE M, DANELLJAN M, YU F, et al. Gaussian grouping: Segment and edit anything in 3D scenes[C]. European Conference on Computer Vision, Milan, Italy, 2024.",
        "JANG J and KIM C. Identity-aware language Gaussian splatting for open-vocabulary 3D semantic segmentation[C]. IEEE/CVF International Conference on Computer Vision, 2025.",
        "KIRILLOV A, MINTUN E, RAVI N, et al. Segment anything[C]. IEEE/CVF International Conference on Computer Vision, Paris, France, 2023: 4015-4026.",
        "CHENG H K, OH S W, PRICE B, et al. Tracking anything with decoupled video segmentation[C]. IEEE/CVF International Conference on Computer Vision, Paris, France, 2023.",
        "KERBL B, KOPANAS G, LEIMKUEHLER T, et al. 3D Gaussian splatting for real-time radiance field rendering[J]. ACM Transactions on Graphics, 2023, 42(4): 1-14.",
        "MILDENHALL B, SRINIVASAN P P, TANCIK M, et al. NeRF: Representing scenes as neural radiance fields for view synthesis[J]. Communications of the ACM, 2021, 65(1): 99-106.",
        "SCHONBERGER J L and FRAHM J M. Structure-from-motion revisited[C]. IEEE Conference on Computer Vision and Pattern Recognition, Las Vegas, USA, 2016: 4104-4113.",
        "OQUAB M, DARCET T, MOUTAKANNI T, et al. DINOv2: Learning robust visual features without supervision[J]. Transactions on Machine Learning Research, 2024.",
        "LI B, WEINBERGER K Q, BELONGIE S, et al. Language-driven semantic segmentation[C]. International Conference on Learning Representations, 2022.",
        "LIU K, ZHAN F, CHEN Y, et al. Weakly supervised 3D open-vocabulary segmentation[C]. Advances in Neural Information Processing Systems, 2023.",
        "PENG S, GENOVA K, JIANG C M, et al. OpenScene: 3D scene understanding with open vocabularies[C]. IEEE/CVF Conference on Computer Vision and Pattern Recognition, Vancouver, Canada, 2023.",
    ]
    for i, ref in enumerate(refs, 1):
        body.append(para(f"[{i}] {ref}"))

    body.append(heading("作者简介", 1))
    body.append(para("陈旭：研究方向为三维视觉、开放词汇语义分割和三维高斯泼溅。"))

    body.append(heading("Extended Abstract", 1))
    body.append(
        para(
            "Objective Open-vocabulary 3D semantic segmentation aims to localize and segment arbitrary semantic targets in 3D scenes according to natural-language queries. "
            "Although Identity-aware Language Gaussian Splatting improves language-driven 3D segmentation by introducing object-level identity supervision, its performance is constrained by the quality of pseudo identity labels and by the reliability of query mask generation. "
            "This paper studies these two limitations and proposes an identity-aware pseudo-label and mask prediction refinement method."
        )
    )
    body.append(
        para(
            "Methods The proposed method contains two complementary components. "
            "First, the original object masks are refined before training by connected-component analysis, boundary uncertainty estimation, and cross-view area consistency checking. "
            "The refined masks and confidence maps are then used to weight the identity classification loss during ILGS training. "
            "Second, a post-processing module is introduced during inference to suppress region-growing drift and refine part-level targets. "
            "The module preserves reliable seed regions when the expanded mask shows abnormal area drift, and it selects compact local connected components for small object parts."
        )
    )
    body.append(
        para(
            "Results and Discussions Experiments on the LERF-Mask benchmark show that pseudo-label refinement improves the figurines scene substantially, increasing mIoU from 65.99% to 75.21%. "
            "The inference-stage post-processing module further improves scenes where the main error comes from query mask generation, increasing mIoU to 89.19% on teatime and 85.56% on ramen. "
            "These observations indicate that different scenes are limited by different error sources: figurines is more sensitive to training pseudo-label quality, whereas teatime and ramen are more sensitive to region-growing drift and part-level mask mismatch."
        )
    )
    body.append(
        para(
            "Conclusions The proposed refinement strategy shows that open-vocabulary 3D segmentation should not only optimize language feature representation but also explicitly improve pseudo identity labels and query mask generation. "
            "The method provides a reproducible direction for improving ILGS-like systems, while future work should replace the heuristic post-processing scores with learnable or more general multi-candidate selection strategies."
        )
    )
    body.append(para("Key words: open-vocabulary 3D semantic segmentation; 3D Gaussian splatting; pseudo-label refinement; identity consistency; mask post-processing"))

    sect_pr = (
        "<w:sectPr>"
        "<w:pgSz w:w=\"11906\" w:h=\"16838\"/>"
        "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" w:header=\"720\" w:footer=\"720\" w:gutter=\"0\"/>"
        "</w:sectPr>"
    )
    body.append(sect_pr)

    styles = """
    <w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
        <w:name w:val="Normal"/>
        <w:qFormat/>
        <w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr>
        <w:rPr><w:rFonts w:ascii="Times New Roman" w:eastAsia="宋体" w:hAnsi="Times New Roman"/><w:sz w:val="21"/></w:rPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Title">
        <w:name w:val="Title"/>
        <w:basedOn w:val="Normal"/>
        <w:qFormat/>
        <w:rPr><w:b/><w:rFonts w:ascii="Times New Roman" w:eastAsia="黑体" w:hAnsi="Times New Roman"/><w:sz w:val="32"/></w:rPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Heading1">
        <w:name w:val="heading 1"/>
        <w:basedOn w:val="Normal"/>
        <w:qFormat/>
        <w:rPr><w:b/><w:rFonts w:ascii="Times New Roman" w:eastAsia="黑体" w:hAnsi="Times New Roman"/><w:sz w:val="28"/></w:rPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Heading2">
        <w:name w:val="heading 2"/>
        <w:basedOn w:val="Normal"/>
        <w:qFormat/>
        <w:rPr><w:b/><w:rFonts w:ascii="Times New Roman" w:eastAsia="黑体" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr>
      </w:style>
      <w:style w:type="table" w:styleId="TableGrid">
        <w:name w:val="Table Grid"/>
        <w:tblPr><w:tblBorders>
          <w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>
          <w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>
          <w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>
          <w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>
          <w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>
          <w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>
        </w:tblBorders></w:tblPr>
      </w:style>
    </w:styles>
    """

    document = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\" "
        "xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
        "xmlns:pic=\"http://schemas.openxmlformats.org/drawingml/2006/picture\">"
        "<w:body>"
        + "".join(body)
        + "</w:body></w:document>"
    )
    return document, styles


def write_docx() -> None:
    include_image = FIG_3DOVS.exists()
    document_xml, styles_xml = build_document_xml(include_image)

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
      <Default Extension="xml" ContentType="application/xml"/>
      <Default Extension="png" ContentType="image/png"/>
      <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
      <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
    </Types>
    """
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
    </Relationships>
    """
    doc_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
    """
    if include_image:
        doc_rels += '<Relationship Id="rIdImage1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>'
    doc_rels += "</Relationships>"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_FILE.exists():
        OUT_FILE.unlink()
    with zipfile.ZipFile(OUT_FILE, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document_xml)
        z.writestr("word/styles.xml", styles_xml)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        if include_image:
            z.write(FIG_3DOVS, "word/media/image1.png")

    print(str(OUT_FILE))


if __name__ == "__main__":
    write_docx()

