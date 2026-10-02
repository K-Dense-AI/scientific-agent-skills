# Scientific Agent Skills (AI 科学智能体技能库)

<div align="center">

[English](README.md) | [简体中文](README.zh-CN.md)

</div>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![arXiv](https://img.shields.io/badge/arXiv-2609.00065-b31b1b.svg)](https://arxiv.org/abs/2609.00065)
[![Version](https://img.shields.io/badge/Version-2.68.0-blue.svg)](pyproject.toml)
[![Skills](https://img.shields.io/badge/Skills-165-brightgreen.svg)](#-包含内容)
[![Databases](https://img.shields.io/badge/Databases-100%2B-orange.svg)](#-包含内容)
[![Agent Skills](https://img.shields.io/badge/Standard-Agent_Skills-blueviolet.svg)](https://agentskills.io/)
[![Agent Plugins](https://img.shields.io/badge/Standard-Agent_Plugins-0A7A72.svg)](https://agent-plugins.org/)
[![Security Scan](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/security-scan.yml/badge.svg)](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/security-scan.yml)
[![Skill Tests](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/skill-tests.yml/badge.svg)](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/skill-tests.yml)
[![Works with](https://img.shields.io/badge/Works_with-Cursor_|_Claude_Code_|_Codex_|_Google_Antigravity-blue.svg)](#-快速开始)
[![X](https://img.shields.io/badge/Follow_on_X-%40k__dense__ai-000000?logo=x)](https://x.com/k_dense_ai)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-K--Dense_Inc.-0A66C2?logo=linkedin)](https://www.linkedin.com/company/k-dense-inc)
[![YouTube](https://img.shields.io/badge/YouTube-K--Dense_Inc.-FF0000?logo=youtube)](https://www.youtube.com/@K-Dense-Inc)
[![Reddit](https://img.shields.io/badge/Reddit-u%2F--k--dense---FF4500?logo=reddit&logoColor=white)](https://www.reddit.com/user/-k-dense-/)

> **🔔 Claude Scientific Skills 现已正式更名为 Scientific Agent Skills。** 保持原汁原味的强大技能，带来更广泛的兼容性 —— 现已支持任何兼容开放 [Agent Skills](https://agentskills.io/) 标准的 AI 智能体，不仅限于 Claude。

> **新品发布：[K-Dense BYOK](https://github.com/K-Dense-AI/k-dense-byok)** —— 一款运行在桌面端的免费、开源 AI 科学协作者，由 Scientific Agent Skills 提供底层驱动。自带 API 密钥，可从 40 多个模型中任意挑选，获得包含网络检索、文件处理、100+ 科学数据库以及本仓库全部 165 个专业技能的完整科研工作空间。所有数据严格保存在本地，重度科研计算任务还可通过 [Modal](https://modal.com/) 无缝扩展至云端。[点此立即体验。](https://github.com/K-Dense-AI/k-dense-byok)

> **🎥 网络研讨会实录 —— [K-Dense BYOK 入门指南](https://youtu.be/Du3BIE48DKc?si=9dPpETKSc2PeQbvU)**  
> 全面展示 [K-Dense BYOK](https://github.com/K-Dense-AI/k-dense-byok) 的实操演练。涵盖如何快速配置、导入 API 密钥，以及如何利用本仓库技能执行真实的科学研究工作流。无需预备高级编程经验。**[观看视频回放 →](https://youtu.be/Du3BIE48DKc?si=9dPpETKSc2PeQbvU)**

> **持续关注：** 关注 K-Dense 的 [X](https://x.com/k_dense_ai)、[LinkedIn](https://www.linkedin.com/company/k-dense-inc)、[YouTube](https://www.youtube.com/@K-Dense-Inc) 和 [Reddit](https://www.reddit.com/user/-k-dense-/)，第一时间获取新技能发布、版本公告、实操演示以及可直接复用于自有智能体的科研工作流用例。

> **📄 学术论文：** Scientific Agent Skills 在论文 [*Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*](https://arxiv.org/abs/2609.00065) (arXiv:2609.00065) 中有详细阐述。如果您在学术研究中使用了本技能库，请[引用该论文](#-论文引用)。

本仓库由 [K-Dense](https://k-dense.ai) 倾力打造，汇集了 **165 个即开即用的科学研究智能体技能**，全面覆盖癌症基因组学、1000 人基因组个体水平查询、调控序列预测、活体病原变异监测、分析方法验证、PK/PD 建模与剂量选择、生物医药全文本检索、药物靶点结合亲和力预测、受限生物医学知识图谱搜索、分子动力学模拟、RNA 速率、微生物组基底模型、地球空间科学、时间序列预测，以及通过 Hugging Science 发掘科学 ML 资源、78+ 科学数据库检索等丰富领域。本仓库同时也是一个便携式的 [Agent Plugins](https://agent-plugins.org/) 软件包（`plugin.json` + `skills/`），支持插件特性的客户端可一键将整个技能集合加载为单个插件。全面兼容 **Cursor、Claude Code、Codex、Google Antigravity 等主流平台**。助您将桌面端的 AI 编程助手秒级升级为能够执行跨生物、化学、医学等多学科复杂科研任务的超级“AI 科学家”。

> ⭐ **让科学 AI 工具更易被发现：** 如果 Scientific Agent Skills 为您节省了调研时间、教会了您的智能体专业工作流，或加速了您的课题组研究进程，欢迎 [Star 本仓库](https://github.com/K-Dense-AI/scientific-agent-skills)。您的 Star 是对开源社区持续维护可复用科研技能的莫大鼓励与公开认可！

---

这些技能使您的 AI 智能体能够流畅对接跨学科领域的专业科学代码库、权威数据库及实验工具。虽然智能体本身具备调用任意 Python 包或 API 的基础能力，但这些经过精心编写的规范技能提供了高度梳理的文档、约束与实操范例，使其在处理以下专业工作流时表现出极高的准确度与鲁棒性：

- 🧬 **生物信息学与基因组学 (Bioinformatics & Genomics)** - 序列分析、单细胞 RNA-seq、基因调控网络重构、突变注释、系统发育树构建
- 🧪 **化学信息学与药物发现 (Cheminformatics & Drug Discovery)** - 分子性质预测、虚拟筛选、ADMET 分析、分子对接、先导化合物优化
- 🔬 **蛋白质组学与质谱分析 (Proteomics & Mass Spectrometry)** - LC-MS/MS 数据处理、肽段鉴定、光谱图谱匹配、蛋白质定量分析
- 🏥 **临床研究与证据链工作流 (Clinical Research & Evidence Workflows)** - 临床试验检索、药物基因组学、变异证据审查、药代动力学/药效动力学 (PK/PD) 建模与给药方案评估、结构化临床报告草案整理
- 🧠 **医疗 AI 与生物信号研究 (Healthcare AI & Biosignal Research)** - 电子病历 (EHR) 与模型前沿研究、生理信号分析与回顾性科学验证
- 🐭 **临床前研究与动物福利 (Preclinical Research & Animal Welfare)** - 实验动物多元 RELSA 严重程度评分与人道终点预测，严格遵循 3R 原则与合规审查
- 🖼️ **医学影像与数字病理 (Medical Imaging & Digital Pathology)** - 隐私合规的本地 DICOM 影像处理、计算病理学、全切片图像 (WSI) 科学分析
- 🤖 **机器学习与人工智能 (Machine Learning & AI)** - 深度学习、强化学习、时间序列分析、模型可解释性、贝叶斯推断
- 🔮 **材料科学与计算化学 (Materials Science & Chemistry)** - 晶体结构分析、相图计算、代谢通量建模 (COBRApy)、量化化学计算
- 🌌 **物理学与天文学 (Physics & Astronomy)** - 天文数据分析、坐标变换、宇宙学计算、符号数学与理论物理计算
- ⚙️ **工程模拟与系统建模 (Engineering & Simulation)** - 离散事件仿真、多目标优化、代谢工程、复杂系统建模、工艺流程优化
- 📊 **数据分析与期刊级可视化 (Data Analysis & Visualization)** - 统计推断、网络拓扑分析、时间序列、CNS 顶刊级出版图表绘制、探索性数据分析 (EDA)
- 🌍 **地球空间科学与遥感 (Geospatial Science & Remote Sensing)** - 卫星遥感图像处理、GIS 地理信息系统分析、空间统计学、数字高程模型
- 🧪 **实验室自动化 (Laboratory Automation)** - 液体处理工作站协议编译 (Opentrons/PyLabRobot)、实验室硬件 CAD 建模、LIMS/ELN 电子实验记录本集成
- 📚 **科学交流与学术写作 (Scientific Communication)** - 证据可追溯学术写作、同行评议规范、文献综述、无宏 PPTX 学术海报制作、矢量图表与文献引用管理
- 🔬 **多组学与系统生物学 (Multi-omics & Systems Biology)** - 多模态数据整合、生物信号通路富集、网络生物学、系统层级机制解析
- 🧬 **蛋白质工程与分子设计 (Protein Engineering & Design)** - 蛋白质语言模型 (ESM 系列)、结构预测 (AlphaFold 等)、序列从头设计、酶功能注释
- 🧰 **智能体平台与底层架构 (Agent Platforms & Infrastructure)** - 基于 Pi 与开放 Agent 架构开发终端编码框架、SDK 拓展、自定义 Provider/模型及 TUI 工具
- 🎓 **科研方法论与课题设计 (Research Methodology)** - 假说提出与候选方案设计、头脑风暴、批判性学术思维、基金申报书构思与评估
- ⚖️ **法规与行业标准 (Regulatory & Standards)** - 面向 ISO 质量管理体系 (ISO 13485, ISO 17025 等) 与 ICH/USP/CLSI 分析方法验证 (Q2(R2)/Q14, M10) 的标准化证据准备

**即刻将您桌面端的 AI 编程助手转化为全能的“AI 科学家”！**

---

## 📦 包含内容

本仓库汇集整理了 **165 个科学与研究专业技能**，结构体系如下：

- **100+ 顶级科学与金融数据库**：统一的 `database-lookup` 技能提供对 78 个公共权威数据库（PubChem、ChEMBL、UniProt、PDB、AlphaFold、COSMIC、ClinicalTrials.gov 等）的确定性 REST API 检索；更有针对 DepMap、IDC、PrimeKG、NCATS ARAX、Hugging Science 的专属深度集成；加上 BioServices（涵盖 40+ 生物信息服务）、BioPython（通过 Entrez 访问 39 个 NCBI 子库）和 gget（20+ 基因组学库）的全面覆盖。
- **70+ 深度优化的 Python 专业包技能**：针对 RDKit、Scanpy、PyTorch Lightning、scikit-learn、PyTDC、PathML、pydicom、NeuroKit2、QuTiP、GeoPandas、pymatgen、BioPython、Qiskit、OpenMM/MDAnalysis 等关键库提供经真实测试的最佳实践工作流。
- **9 大科研平台集成技能**：对 Benchling、DNAnexus、LatchBio、OMERO、Protocols.io、Open Notebook、Ginkgo Cloud Lab、LabArchives 和 Opentrons 等知名平台提供预置的调用指导与安全边界。
- **30+ 科学分析与交流工具**：学术文献综述、证据链可追溯写作、同行评议协助、Paperclip 全文检索（精准锁定文献行号引用）、Mermaid 流程图、科研信息图表 (Infographics) 制作。
- **10+ 前沿临床与方法论工具**：假说生成、项目申报、群体 PK/PD 药代动力学模拟、ISO 体系与分析方法验证、Autoskill 自动化技能发掘。

每个技能均包含：
- ✅ 详尽完备的使用指南 (`SKILL.md`)
- ✅ 实用的可运行代码用例
- ✅ 典型应用场景与最佳实践
- ✅ 平台集成接入指南与参考资料
- ✅ 为包含 `scripts/` 的技能配套编写的独立自动化测试套件

---

## 📋 目录索引

- [包含内容](#-包含内容)
- [为什么选择本技能库？](#-为什么选择本技能库)
- [快速开始](#-快速开始)
- [安全合规免责声明](#%EF%B8%8F-安全合规免责声明)
- [致敬与支持开源社区](#%EF%B8%8F-致敬与支持开源社区)
- [环境前置要求](#%EF%B8%8F-环境前置要求)
- [实战经典范例](#-实战经典范例)
- [典型科研应用场景](#-典型科研应用场景)
- [全部技能分类概览](#-全部技能分类概览)
- [如何参与开源贡献](#-如何参与开源贡献)
- [论文引用](#-论文引用)
- [开源协议](#-开源协议)

---

## 🚀 为什么选择本技能库？

### ⚡ **大幅加速科学研究**
- **省去数天无谓摸索**：免除繁重的底层 API 文档阅读与配置踩坑。
- **经学术验证的起点**：范例均经过验证、溯源性标注和明确的安全边界测试。
- **复杂多步流水线一键触达**：只需一段自然语言指令，即可驱动跨多工具的复杂科研流程。

### 🎯 **宏大而专业的全领域覆盖**
- **165 个技能全景覆盖**：横跨生命科学、化学、临床、物理、工程和地球空间科学。
- **100+ 权威数据库**：打通从分子、基因、通路到临床试验与专利文献的全部数据通道。

### 🔧 **极简轻量集成**
- **即插即用**：将技能文件夹复制到您的智能体技能路径下即可生效。
- **标准化发现**：主流支持 Agent Skills 的客户端可自动检索、加载并按需调用。

---

## 🎯 快速开始

### 方式一：npx 一键安装（推荐）

通过支持 Agent Skills 的通用包管理器一键安装：

```bash
npx skills add K-Dense-AI/scientific-agent-skills
```

兼容 **Cursor**、**Claude Code**、**Codex**、**Gemini CLI**、**Google Antigravity** 等主流平台。

### 方式二：GitHub CLI (`gh skill`)

如果您已安装 [GitHub CLI](https://cli.github.com/) (v2.90.0+)：

```bash
# 交互式浏览并选择安装
gh skill install K-Dense-AI/scientific-agent-skills

# 直接安装单个特定技能（如 scanpy）
gh skill install K-Dense-AI/scientific-agent-skills scanpy

# 指定安装到特定客户端
gh skill install K-Dense-AI/scientific-agent-skills --agent cursor
gh skill install K-Dense-AI/scientific-agent-skills --agent claude-code
gh skill install K-Dense-AI/scientific-agent-skills --agent codex
gh skill install K-Dense-AI/scientific-agent-skills --agent gemini
```

### 方式三：Agent Plugins (Cursor、Codex 等插件化客户端)

本仓库符合 [Agent Plugins](https://agent-plugins.org/) 规范。

**Cursor 用户**：创建软链接或复制到本地插件目录：
```bash
mkdir -p ~/.cursor/plugins/local
ln -s "$(pwd)" ~/.cursor/plugins/local/scientific-agent-skills
```
随后重启 Cursor 或运行 **Developer: Reload Window** 即可在 **Customize** 中启用。

---

## ⚠️ 安全合规免责声明

> **技能具备代码执行能力，并会影响您的 AI 助手行为。安装前请仔细审阅。**

所有技能均通过自动化代码审计及 [Cisco AI Defense Skill Scanner](https://github.com/cisco-ai-defense/skill-scanner) 的大模型安全筛查。但作为开源项目，**用户始终对本地安装并执行的技能负有最终审查责任**：
1. **按需安装**：建议只安装课题研究真正需要的技能子集，避免不必要的上下文浪费与安全暴露；
2. **仔细阅读 `SKILL.md`**：了解其引用的包、连接的外网服务与执行逻辑；
3. **敏感操作安全边界**：严禁将任何未脱敏患者隐私数据、机密临床数据直接交由大模型处理。

---

## 💡 实战经典范例

安装技能后，您可以直接向 AI 智能体提出类似以下的高阶多步科研需求：

### 🧪 药物发现与虚拟筛选管线
> **指令**：*“请调用可用技能：从 ChEMBL 检索针对 EGFR 的抑制剂（IC50 < 50nM），用 RDKit 分析构效关系 (SAR)，用 datamol 生成改进类似物，结合 AlphaFold 预测的 EGFR 靶点结构用 DiffDock 进行分子对接虚拟筛选，检索 PubMed 获取耐药机制文献并输出科研图表与综合分析报告。”*  
> **涉及技能**：`database-lookup`, `rdkit`, `datamol`, `diffdock`, `paper-lookup`, `scientific-visualization`

### 🔬 单细胞 RNA-seq 综合分析
> **指令**：*“加载 10X 单细胞数据集并使用 Scanpy 进行质控与双胞消除，与 Cellxgene Census 数据库整合，利用 NCBI Gene 标记注释细胞亚群，用 PyDESeq2 进行差异基因表达分析，并结合 Arboreto 重构基因调控网络。”*  
> **涉及技能**：`scanpy`, `cellxgene-census`, `database-lookup`, `pydeseq2`, `arboreto`

### 🧬 多组学标志物联合发现
> **指令**：*“使用 PyDESeq2 分析转录组差异，用 pyOpenMS 处理质谱蛋白质组，从 HMDB 整合代谢物，通过 STRING 构建分子互作网络并映射到 KEGG 通路，结合 scikit-learn 构建预测模型。”*  
> **涉及技能**：`pydeseq2`, `pyopenms`, `database-lookup`, `statsmodels`, `scikit-learn`

---

## 📚 全部技能分类概览

本仓库包含 **165 个科学与研究技能**，按领域分类如下：

- 🧬 **生物信息学与基因组学 (27 项技能)**：Bulk RNA-seq、BioPython、pysam、scikit-bio、Scanpy、AnnData、scvi-tools、scVelo、Cellxgene Census、gget、deepTools、OneKGPd (1000 人基因组)、PyDESeq2、Pathway Enrichment 通路富集、ETE Toolkit、Phylogenetics 等。
- 🧪 **化学信息学与药物研发 (10 项技能)**：RDKit、Datamol、Molfeat、DeepChem、TorchDrug、DiffDock (分子对接)、OpenMM + MDAnalysis (分子动力学)、Rowan (量化计算)、MedChem、PyTDC 等。
- 🔬 **蛋白质组学与质谱 (2 项技能)**：matchms、pyOpenMS。
- 🏥 **临床研究与证据链 (8 项技能)**：Database Lookup、PK/PD Modeling (药代动力学/药效动力学)、DepMap、IDC、PyHealth 等。
- 🐭 **临床前与动物实验 (1 项技能)**：RELSA Severity Assessment。
- 🖼️ **医学影像与数字病理 (4 项技能)**：pydicom、histolab、PathML、DeepSpot-M 等。
- 🤖 **机器学习与人工智能 (14 项技能)**：PyTorch Lightning、Transformers、Stable Baselines3、scikit-learn、SHAP、TimesFM (时间序列预测)、PyMC、PyMOO、Torch Geometric、UMAP-learn 等。
- 🔮 **材料科学与物理化学 (7 项技能)**：pymatgen、COBRApy (代谢通量分析)、Astropy、Cirq、Qiskit、QuTiP 等。
- ⚙️ **工程模拟与科学计算 (6 项技能)**：build123d (CAD 建模)、FluidSim (流体力学)、OpenPIV、SimPy (离散仿真)、SymPy 等。
- 📊 **数据分析与可视化 (22 项技能)**：Matplotlib、Seaborn、Scientific Visualization、GeoPandas、Dask、Polars、NetworkX、LiteParse、MarkItDown、Mermaid 绘图、实验设计 (DOE) 等。
- 🧪 **实验室自动化 (6 项技能)**：PyLabRobot、Opentrons (液体工作站)、Ginkgo Cloud Lab (云实验室)、protocols.io、Benchling、LabArchives 等。
- 🧬 **蛋白质工程与设计 (4 项技能)**：ESM (蛋白质语言模型)、Glycoengineering (糖工程预测)、Adaptyv (自动化蛋白测试)、Tamarind (AlphaFold/ESMFold/RFdiffusion 显卡云接入) 等。
- 📚 **科学交流与写作 (27 项技能)**：Paper Lookup (PubMed 等 10 大库)、Paperclip (全文穿透与行级精准引用)、Literature Review、Scientific Writing、LaTeX Posters、Infographics (信息图表)、Zotero 联动等。
- 🔬 **权威科学数据库接入 (12 项技能，直通 100+ 数据库)**：Database Lookup (直连 78 个库)、DepMap、PrimeKG 知识图谱、NCATS ARAX、Hugging Science、OneKGPd 等。
- 🔧 **底层架构与科研工具 (12 项技能)**：Modal (云算力)、DataLad、GPU 优化加速 (Numba/CuPy)、Nextflow、Autoskill、Pi Agent 等。
- 🎓 **科研方法论与战略设计 (13 项技能)**：科学头脑风暴、假说生成、批判性思维、Arbor 假说树细化、What-If 预案演练、基金撰写等。
- ⚖️ **法规认证与方法验证 (2 项技能)**：ISO 体系准备、ICH Q2(R2)/Q14 分析方法验证等。

---

## 🤝 参与贡献

我们极其欢迎全球科研人员与开发者共同完善与扩充科学技能库！
- ✨ **新增技能**：为更多前沿科学计算包、权威数据库或实验平台编写规范技能。
- 📚 **完善文档**：贡献更多真实科研课题的代码范例与使用场景，纠正过时 API。
- 🐛 **提交反馈**：在 GitHub Issues 中报告 Bug 或提出新技能需求。

详细指南请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 论文引用

如果您在科研论文或学术项目中使用了本仓库，请引用官方论文：

```bibtex
@article{scientific-agent-skills2026,
  title={Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents},
  author={K-Dense},
  journal={arXiv preprint arXiv:2609.00065},
  year={2026}
}
```

---

## 📜 开源协议

本项目主体遵循 [MIT License](LICENSE.md) 开源协议。  
个别具体技能可能在其 `SKILL.md` 中声明了适用的特定子协议，请遵照相关条款使用。
