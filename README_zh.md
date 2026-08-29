# Scientific Agent Skills

> **🌐 Languages:** [English](README.md) | **简体中文** — 中文版可能滞后于英文原版，请以 [英文 README](README.md) 为准。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Version](https://img.shields.io/badge/Version-2.64.0-blue.svg)](pyproject.toml)
[![Skills](https://img.shields.io/badge/Skills-163-brightgreen.svg)](#-包含什么)
[![Databases](https://img.shields.io/badge/Databases-100%2B-orange.svg)](#-包含什么)
[![Agent Skills](https://img.shields.io/badge/Standard-Agent_Skills-blueviolet.svg)](https://agentskills.io/)
[![Agent Plugins](https://img.shields.io/badge/Standard-Agent_Plugins-0A7A72.svg)](https://agent-plugins.org/)
[![Security Scan](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/security-scan.yml/badge.svg)](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/security-scan.yml)
[![Skill Tests](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/skill-tests.yml/badge.svg)](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/skill-tests.yml)
[![Works with](https://img.shields.io/badge/Works_with-Cursor_|_Claude_Code_|_Codex_|_Google_Antigravity-blue.svg)](#-快速开始)
[![X](https://img.shields.io/badge/Follow_on_X-%40k__dense__ai-000000?logo=x)](https://x.com/k_dense_ai)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-K--Dense_Inc.-0A66C2?logo=linkedin)](https://www.linkedin.com/company/k-dense-inc)
[![YouTube](https://img.shields.io/badge/YouTube-K--Dense_Inc.-FF0000?logo=youtube)](https://www.youtube.com/@K-Dense-Inc)
[![Reddit](https://img.shields.io/badge/Reddit-u%2F--k--dense---FF4500?logo=reddit&logoColor=white)](https://www.reddit.com/user/-k-dense-/)

> **🔔 Claude Scientific Skills 现已更名为 Scientific Agent Skills。** skill 不变，但兼容性更广——现在适用于任何支持开放 [Agent Skills](https://agentskills.io/) 标准的 AI 智能体，而不仅仅是 Claude。

> **新增：[K-Dense BYOK](https://github.com/K-Dense-AI/k-dense-byok)** — 一款免费、开源的桌面端 AI 科研伙伴（co-scientist），由 Scientific Agent Skills 驱动。自带 API 密钥，可从 40+ 模型中选择，并拥有完整的科研工作区，支持网页搜索、文件处理、100+ 科学数据库，以及本仓库的全部 161 个 skill。你的数据始终保留在自己的电脑上，还可以通过 [Modal](https://modal.com/) 选择性地扩展至云端算力以应对繁重负载。[从这里开始。](https://github.com/K-Dense-AI/k-dense-byok)

> **🎥 网络研讨会回放 — [K-Dense BYOK 快速入门](https://youtu.be/Du3BIE48DKc?si=9dPpETKSc2PeQbvU)**
> 手把手上手演示 [K-Dense BYOK](https://github.com/K-Dense-AI/k-dense-byok)，这是一款免费、开源的桌面端 AI 科研伙伴，运行在你自己的机器上，由 Scientific Agent Skills 驱动。我们将介绍如何安装、自带 API 密钥，以及如何使用这些 skill 运行真实的科研 workflow。无需任何技术经验。[观看回放 →](https://youtu.be/Du3BIE48DKc?si=9dPpETKSc2PeQbvU)

> **保持关注：** 在 [X](https://x.com/k_dense_ai)、[LinkedIn](https://www.linkedin.com/company/k-dense-inc)、[YouTube](https://www.youtube.com/@K-Dense-Inc) 和 [Reddit](https://www.reddit.com/user/-k-dense-/) 上关注 K-Dense，获取新 skill、版本发布公告、实操演示、科研 workflow 示例，以及可与你自己的 AI 智能体配合使用的范例。

这是一套全面的 **163 项即用型科研与学术 skill**（涵盖癌症基因组学、个体级千人基因组查询、托管调控序列预测、实时病原体变异监测、分析方法验证、PK/PD 建模与剂量选择、生物医学与法规文献全文检索、药物-靶点结合、受限的生物医学知识图谱搜索、分子动力学、RNA 速率、微生物组基础模型、地理空间科学、时间序列预测、通过 Hugging Science 进行的科研机器学习资源发现、78+ 科学数据库等），适用于任何支持开放 [Agent Skills](https://agentskills.io/) 标准的 AI 智能体，由 [K-Dense](https://k-dense.ai) 创建。该仓库同时也是一个可移植的 [Agent Plugins](https://agent-plugins.org/) 包（`plugin.json` + `skills/`），因此支持插件的客户端可以将整个合集作为单个插件加载。适用于 **Cursor、Claude Code、Codex、Google Antigravity** 等。将你的 AI 智能体转变为能够在生物学、化学、医学等领域执行复杂多步骤科研 workflow 的研究助理。

> ⭐ **让 AI 助力科学更容易被发现：** 如果 Scientific Agent Skills 为你节省了时间、教会了你的智能体某个 workflow，或帮助你的实验室更快推进，请为[本仓库点 Star](https://github.com/K-Dense-AI/scientific-agent-skills)。一个 Star 就是一份公开的认可，表明这些开放、可复用的科研 skill 值得继续维护：它帮助科学家、工程师和开源贡献者找到这个项目，展示哪些智能体 skill 标准正获得实际采用，也给了我们一个明确的理由去持续扩展这个合集，造福社区。

---

这些 skill 让你的 AI 智能体能够跨多个科研领域无缝使用专门的科学库、数据库和工具。虽然智能体本身就可以使用任何 Python 包或 API，但这些显式定义的 skill 提供了精选的文档和示例，使其在以下 workflow 中显著更强大、更可靠：
- 🧬 生物信息学与基因组学 - 序列分析、单细胞 RNA-seq、基因调控网络、变异注释、系统发育分析
- 🧪 化学信息学与药物发现 - 分子性质预测、虚拟筛选、ADMET 分析、分子对接、先导化合物优化
- 🔬 蛋白质组学与质谱 - LC-MS/MS 处理、肽段鉴定、谱图匹配、蛋白质定量
- 🏥 临床研究与证据 workflow - 临床试验、药物基因组学、变异证据审查、药代动力学/药效动力学（PK/PD）建模与给药方案评估、聚合决策支持评估、来源限定的报告结构草稿，以及临床医生撰写的治疗决策格式化
- 🧠 医疗 AI 与生物信号研究 - 电子健康记录（EHR）与模型研究、生理信号分析、回顾性验证——不用于针对患者的诊断、治疗、报警或部署决策
- 🖼️ 医学影像与数字病理 - 隐私感知的 DICOM 处理和仅限研究的全切片图像分析、计算病理学、放射数据 workflow
- 🤖 机器学习与 AI - 深度学习、强化学习、时间序列分析、模型可解释性、贝叶斯方法
- 🔮 材料科学与化学 - 晶体结构分析、相图、代谢建模、计算化学
- 🌌 物理与天文 - 天文数据分析、坐标变换、宇宙学计算、符号数学、物理计算
- ⚙️ 工程与仿真 - 离散事件仿真、多目标优化、代谢工程、系统建模、过程优化
- 📊 数据分析与可视化 - 统计分析、网络分析、时间序列、可发表级别的图表、大规模数据处理、EDA
- 🌍 地理空间科学与遥感 - 卫星影像处理、GIS 分析、空间统计、地形分析、地球观测机器学习
- 🧪 实验室自动化 - 液体处理协议、实验室设备控制、workflow 自动化、LIMS 集成
- 📚 科学沟通 - 可溯源写作、保密授权同行评审、文献综述、文档处理、无宏 PPTX 海报、幻灯片、示意图、引文管理
- 🔬 多组学与系统生物学 - 多模态数据整合、通路分析、网络生物学、系统层面洞察
- 🧬 蛋白质工程与设计 - 蛋白质语言模型、结构预测、序列设计、功能注释
- 🧰 智能体平台与基础设施 - 基于 Pi 的 SDK、RPC、扩展、自定义提供方/模型、包、TUI 组件和会话工具开发
- 🎓 研究方法论 - 受证据约束的候选假设、科学头脑风暴、批判性思维、基金申请书撰写，以及对学术作品的定性低利害评估
- ⚖️ 法规与标准 - 为 ISO 管理体系与实验室标准，以及 ICH/USP/CLSI 框架下的分析方法验证、确认与转移，起草证据准备材料——仅用于合格审查，绝不用于认证、认可或方法放行决策

**将你的 AI 编码智能体变成桌面上的"AI 科学家"！**

> 🎬 **Scientific Agent Skills 新手？** 观看我们的 [Scientific Agent Skills 快速入门](https://youtu.be/ZxbnDaD_FVg) 视频，快速上手。

### 🎥 更多教程

关于这些 skill 在真实科研任务上的实操讲解录像，来自 [K-Dense YouTube 频道](https://www.youtube.com/@K-Dense-Inc)：

| 视频 | 内容 |
|-------|----------------|
| [Skills 101：构建你自己的科学智能体 skill](https://youtu.be/lVZbHiwzMEg) | 从零开始编写、测试并打包一项新 skill |
| [文献综述与假设生成](https://youtu.be/wKJp8y4ZyiM) | 检索文献并生成有依据的假设 |
| [起草并预算实验方案](https://youtu.be/Yz2L5s_M_34) | 把计划中的实验转化为带成本核算的书面方案 |
| [起草审稿意见回复](https://youtu.be/0MmU-Pmtg1o) | 根据审稿意见构建逐条反驳 |
| [AI 能复现 Nature Medicine 论文吗？](https://youtu.be/4WTCK9kSfdk) | 对一篇已发表分析进行端到端复现尝试 |

---

## 📦 包含什么

本仓库提供 **163 项科研与学术 skill**，按以下类别组织：

- **100+ 科学与金融数据库** - 一个统一的数据库查询 skill 可确定性、带完整溯源地访问 78 个公共数据库（PubChem、ChEMBL、UniProt、COSMIC、ClinicalTrials.gov、FRED、USPTO 等），另有针对 DepMap、Imaging Data Commons、PrimeKG、NCATS ARAX、美国财政部财政数据、Hugging Science、OneKGPd 和 Genomic Intelligence 的专个 skill。BioServices（约 40 个生物信息学服务）、BioPython（通过 Entrez 访问 39 个 NCBI 子数据库）和 gget（20+ 基因组学数据库）等多数据库包进一步扩展了覆盖范围
- **70+ 优化过的 Python 包 skill** - 针对 RDKit、Scanpy、PyTorch Lightning、scikit-learn、PyTDC、PathML、pydicom、NeuroKit2、PufferLib、QuTiP、GeoPandas、pymatgen、BioPython、Qiskit、分子动力学（OpenMM/MDAnalysis）等提供显式定义、感知版本的 workflow。智能体仍然可以使用*任何* Python 包；这些 skill 只是为所列包提供更强、更安全的指引
- **9 项科学集成 skill** - 针对 Benchling、DNAnexus、LatchBio、OMERO、Protocols.io、Open Notebook、Ginkgo Cloud Lab、LabArchives 和 Opentrons 的显式定义 skill。同样，智能体并不局限于这些——任何可从 Python 访问的 API 或平台都可使用；这些 skill 是经过优化的、已整理好文档的路径
- **30+ 分析与沟通工具** - 文献综述、可溯源的科学写作、保密同行评审、文档处理、Paperclip（全文论文、FDA/PMDA/EMA 申报文件、带行号固定引用的试验注册库）、Paperzilla、Exa Search、无宏 PPTX 海报、幻灯片、示意图、信息图、Mermaid 图表等
- **10+ 研究与临床工具** - 受证据约束的假设生成、基金申请书撰写、聚合临床决策支持研究、临床医生撰写的治疗计划格式化、PK/PD 建模与仿真（NCA、群体 PK、暴露-反应、生物等效性、首次人体剂量）、BIDS、ISO 标准就绪证据准备（ISO 13485、ISO 14971、ISO/IEC 17025、ISO 15189）、分析方法验证与转移（ICH Q2(R2)/Q14、ICH M10、USP、CLSI EP）、情景分析，以及通过 Autoskill 从 workflow 推导 skill

每个 skill 都包含：
- ✅ 全面的文档（`SKILL.md`）
- ✅ 实用的代码示例
- ✅ 使用场景与最佳实践
- ✅ 集成指南
- ✅ 参考资料
- ✅ 每项随附 `scripts/` 的 skill 都有测试套件——CI 会阻止引入捆绑工具却没有对应测试套件的拉取请求

---

## 📋 目录

- [包含什么](#-包含什么)
- [为什么要用它？](#-为什么要用它)
- [快速开始](#-快速开始)
- [安全声明](#%EF%B8%8F-安全声明)
- [支持开源社区](#%EF%B8%8F-支持开源社区)
- [前置要求](#%EF%B8%8F-前置要求)
- [快速示例](#-快速示例)
- [使用场景](#-使用场景)
- [可用 skill](#-可用-skill)
- [来自博客](#-来自博客)
- [贡献](#-贡献)
- [故障排除](#-故障排除)
- [常见问题（FAQ）](#-常见问题faq)
- [支持](#-支持)
- [引用](#-引用)
- [许可证](#-许可证)

---

## 🚀 为什么要用它？

### ⚡ **加速你的研究**
- **节省数天工作量** - 跳过 API 文档调研和集成配置
- **经验证的起始模板** - 经过测试的示例，带显式验证、溯源和安全边界；请在目标环境中自行验证
- **多步骤 workflow** - 用一条提示词即可执行复杂流水线

### 🎯 **全面覆盖**
- **161 个 skill** - 覆盖所有主要科研领域
- **100+ 数据库** - 通过 database-lookup 统一访问 78+ 数据库，另有专项数据访问 skill 以及 BioServices、BioPython、gget 等多数据库包
- **70+ 优化过的 Python 包 skill** - 对 RDKit、Scanpy、PyTorch Lightning、scikit-learn、PyTDC、pydicom、PufferLib、QuTiP、GeoPandas、pymatgen、Qiskit、分子动力学（OpenMM/MDAnalysis）、scVelo、TimesFM 等包提供当前、按版本限定的指引（智能体可以使用任何 Python 包；这些是已整理好文档的路径）

### 🔧 **易于集成**
- **简单设置** - 将 skill 复制到你的 skill 目录即可开始使用
- **配置后自动发现** - 兼容的 host 会从其配置的 skill 路径中自动发现并使用相关 skill
- **文档完善** - 每个 skill 都包含示例、使用场景和最佳实践

### 🌟 **持续维护与支持**
- **定期更新** - 由 K-Dense 团队持续维护和扩展
- **CI 测试** - 每项随附 `scripts/` 的 skill 在 `tests/` 下都有套件，另有仓库级结构契约（frontmatter、链接解析、脚本解析、`--help` 行为），在每个拉取请求上都会运行
- **社区驱动** - 开源，社区贡献活跃
- **企业级支持** - 高级需求可享商业支持服务

---

## 🎯 快速开始

### 方式一：npx（支持的 host）

用一条命令安装 Scientific Agent Skills：

```bash
npx skills add K-Dense-AI/scientific-agent-skills
```

这是一个基于标准的通用安装器，适用于支持 Agent Skills 标准的 host，包括当前版本的 **Claude Code**、**Claude Cowork**、**Codex**、**Gemini CLI**、**Google Antigravity** 和 **Cursor**。请查阅你所用 host 的最新文档，确认安装路径和可选的元数据行为。

### 方式二：GitHub CLI（`gh skill`）

如果你使用 [GitHub CLI](https://cli.github.com/)（v2.90.0+），可以通过 [`gh skill`](https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/) 安装 skill：

```bash
# 以交互方式浏览并安装
gh skill install K-Dense-AI/scientific-agent-skills

# 直接安装特定 skill
gh skill install K-Dense-AI/scientific-agent-skills scanpy

# 指定特定智能体 host
gh skill install K-Dense-AI/scientific-agent-skills --agent cursor
gh skill install K-Dense-AI/scientific-agent-skills --agent claude-code
gh skill install K-Dense-AI/scientific-agent-skills --agent codex
gh skill install K-Dense-AI/scientific-agent-skills --agent gemini
```

`gh skill` 会自动安装到你的智能体 host 的正确目录，并记录溯源元数据以保证供应链完整性。

#### 版本固定

固定到特定发布标签或提交 SHA，以实现可复现的安装：

```bash
# 固定到发布标签
gh skill install K-Dense-AI/scientific-agent-skills --pin v2.64.0

# 固定到提交 SHA
gh skill install K-Dense-AI/scientific-agent-skills --pin abc123def
```

#### 保持 skill 更新

```bash
# 交互式检查更新
gh skill update

# 更新所有已安装 skill
gh skill update --all
```

### 方式三：Agent 插件（Cursor、Codex 及其他插件客户端）

本仓库是一个有效的 [Agent Plugins](https://agent-plugins.org/) 1.0.0 包：根目录的 [`plugin.json`](plugin.json) 加上 `skills/` 下的 Agent Skills。支持该标准的客户端会发现 `skills/` 下每个包含 `SKILL.md` 的直接子目录。

**Cursor** — 将仓库符号链接或复制到本地插件目录，然后重新加载：

```bash
mkdir -p ~/.cursor/plugins/local
ln -s "$(pwd)" ~/.cursor/plugins/local/scientific-agent-skills
```

重启 Cursor，或运行 **Developer: Reload Window** 命令，然后在 **Customize** 下确认插件及其 skill 已出现。参见 [Cursor 插件](https://cursor.com/docs/plugins)。

**Codex** — 从本地检出安装（请在 Codex 文档中确认当前 CLI 标志名称）：

```bash
codex plugins install .
```

兼容的客户端（Cursor、Codex、GitHub Copilot、VS Code、Kiro 及 [agent-plugins.org](https://agent-plugins.org/compatible-clients) 列出的其他客户端）共享相同的包布局；安装体验仍因客户端而异。

### 其他 Agent Skills host（OpenClaw、NemoClaw、Pi、Hermes 等）

不同智能体 host 的安装路径、发现设置以及对可选 frontmatter 字段的支持各不相同。`npx skills add`（方式一）通常安装到 `~/.agents/skills/` 约定目录，项目级安装位于 `.agents/skills/` 下；请对照你所在 host 的最新文档确认这两个路径。要在配置为扫描这些位置的 host 上手动安装：

```bash
git clone https://github.com/K-Dense-AI/scientific-agent-skills.git ~/.agents/skills/scientific-agent-skills   # 用户级
git clone https://github.com/K-Dense-AI/scientific-agent-skills.git .agents/skills/scientific-agent-skills      # 项目级
```

对于支持 skill tap 的 Hermes 版本，可将仓库添加为 tap：

```bash
hermes skills tap add K-Dense-AI/scientific-agent-skills
```

每份 `SKILL.md` 都有 YAML frontmatter，但遗留 skill 和社区 skill 在 `metadata` 格式（块式或流式）以及可选扩展字段上各不相同。仓库更新必须保持 `metadata.version` 为带引号的数字字符串，并通过规范的 `skills-ref validate ./skills/<skill-name>` 检查。各 host 对可选元数据和凭据提示的处理可能不同，请在你实际使用的 host 上验证确认。由于 161 个 skill 会占用大量常驻上下文，建议安装主题子集而不是整个合集。

> **NemoClaw 注意：** NemoClaw 在 NVIDIA OpenShell 中运行智能体，出站网络默认为拒绝。skill 可以正常发现和加载，但任何需要网络的 skill——通过 `uv` 安装包，或 API 调用（Exa、Parallel、Benchling、NCBI、Materials Project 等）——只有操作员在 OpenShell TUI 中预先批准相关域名后才能工作。

**就这么简单！** 兼容的 host 可以从其配置的路径中发现这些 skill 并在相关时使用。你也可以通过在提示词中提及 skill 名称来手动调用任何 skill。

---

## ⚠️ 安全声明

> **skill 可以执行代码并影响你的编码智能体的行为。请审查你要安装的内容。**

Agent Skills 功能强大——它们可以指示你的 AI 智能体运行任意代码、安装包、发起网络请求以及修改你系统上的文件。恶意或编写不当的 skill 有可能引导你的编码智能体做出有害行为。

我们非常重视安全。所有贡献都会经过审查流程，我们会对本仓库中的每个 skill 运行基于 LLM 的安全扫描（通过 [Cisco AI Defense Skill Scanner](https://github.com/cisco-ai-defense/skill-scanner)）。然而，作为一个团队规模小、社区贡献不断增长的仓库，我们无法保证每个 skill 都已对所有可能的风险进行了详尽审查。

**最终责任在于你：审查你要安装的 skill，并决定信任哪些。**

我们建议如下：

- **不要一次性全部安装。** 只安装你工作确实需要的 skill。虽然当 K-Dense 创建并维护所有 skill 时，安装整个合集是合理的，但仓库现在包含许多我们可能没有同样深入审查的社区贡献。
- **安装前阅读 `SKILL.md`。** 每个 skill 的文档都会描述它的用途、使用哪些包、连接哪些外部服务。如果看起来可疑，就不要安装。
- **检查贡献历史。** 由 K-Dense（`K-Dense-AI`）编写的 skill 经过了我们内部审查流程。社区贡献的 skill 已尽我们所能审查，但资源有限。
- **自己运行安全扫描器。** 安装第三方 skill 前，先在本地扫描：
  ```bash
  uv pip install cisco-ai-skill-scanner
  skill-scanner scan /path/to/skill --use-behavioral
  ```
- **报告任何可疑内容。** 如果你发现某个 skill 看起来有恶意或行为异常，请立即[提交 issue](https://github.com/K-Dense-AI/scientific-agent-skills/issues)，以便我们调查。

skill 每周扫描一次——增量进行，未变化的 skill 沿用之前的扫描结果，全部内容至少每 30 天以及扫描器或模型变更时全量重扫——结果发布到 [docs/security-report.md](docs/security-report.md)。有关安全政策、范围内内容、如何私下报告漏洞以及如何对扫描发现提出异议，请参阅 [SECURITY.md](SECURITY.md)。我们尽力及时处理安全缺口。

---

## ❤️ 支持开源社区

Scientific Agent Skills 由全球致力于此的开发者与研究社区维护的 **50+ 优秀开源项目**驱动。Biopython、Scanpy、RDKit、scikit-learn、PyTorch Lightning 等项目构成了这些 skill 的基础。

**如果你认为本仓库有价值，请考虑支持那些支撑它的开源项目：**

- ⭐ 在 GitHub 上为它们**点 Star**
- 💰 通过 GitHub Sponsors 或 NumFOCUS **赞助维护者**
- 📝 在你的出版物中**引用这些项目**
- 💻 **贡献**代码、文档或错误报告

👉 **[查看完整的待支持项目列表](docs/open-source-sponsors.md)**

---

## 🙏 skill 致谢

**[docx](skills/docx/)**、**[pdf](skills/pdf/)**、**[pptx](skills/pptx/)** 和 **[xlsx](skills/xlsx/)** 文档 skill 由 **Anthropic** 创建和维护，并从 [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills) 引入本仓库。它们按 Anthropic 的条款使用——参见每个 skill 的 `LICENSE.txt`——我们会跟踪上游，以便你获得他们最新的改进。这四个 skill 的全部功劳归于 Anthropic。

---

## ⚙️ 前置要求

- **Python**：仓库工具要求 3.13+；单个 skill 的依赖可能支持更广的 Python 版本范围
- **uv**：Python 包管理器（安装 skill 依赖所需）
- **客户端**：任何支持 [Agent Skills](https://agentskills.io/) 标准的智能体（Cursor、Claude Code、Gemini CLI、Codex、Google Antigravity 等）
- **系统**：macOS、Linux 或带 WSL2 的 Windows
- **依赖**：由单个 skill 自动处理（具体需求请查看 `SKILL.md` 文件）

### 安装 uv

这些 skill 使用 `uv` 作为安装 Python 依赖的包管理器。请根据你所用操作系统的说明进行安装：

**macOS 和 Linux：**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows：**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**备选（通过 pip）：**
```bash
pip install uv
```

安装后，运行以下命令验证是否可用：
```bash
uv --version
```

更多安装选项和详情，请访问[官方 uv 文档](https://docs.astral.sh/uv/)。

---

## 💡 快速示例

安装好 skill 后，你可以让 AI 智能体执行复杂的多步骤科研 workflow。以下是一些示例提示词：

### 🧪 药物发现流水线
**目标**：为临床前肺癌研究筛选 EGFR 抑制剂候选分子

**提示词**：
```
Use available skills you have access to whenever possible. Query ChEMBL for EGFR inhibitors (IC50 < 50nM), analyze structure-activity relationships 
with RDKit, generate improved analogs with datamol, perform virtual screening with DiffDock 
against AlphaFold EGFR structure, search PubMed for resistance mechanisms, check COSMIC for 
mutations, and create visualizations and a comprehensive report.
```

**使用的 skill**：database-lookup、rdkit、datamol、diffdock、paper-lookup、scientific-visualization

---

### 🔬 单细胞 RNA-seq 分析
**目标**：对 10X Genomics 数据进行综合分析并整合公共数据

**提示词**：
```
Use available skills you have access to whenever possible. Load 10X dataset with Scanpy, perform QC and doublet removal, integrate with Cellxgene 
Census data, identify cell types using NCBI Gene markers, run differential expression with 
PyDESeq2, infer gene regulatory networks with Arboreto, enrich pathways via Reactome/KEGG, 
and identify therapeutic targets with Open Targets.
```

**使用的 skill**：scanpy、cellxgene-census、database-lookup、pydeseq2、arboreto

---

### 🧬 多组学生物标志物发现
**目标**：整合 RNA-seq、蛋白质组学和代谢组学以预测患者结局

**提示词**：
```
Use available skills you have access to whenever possible. Analyze RNA-seq with PyDESeq2, process mass spec with pyOpenMS, integrate metabolites from 
HMDB/Metabolomics Workbench, map proteins to pathways (UniProt/KEGG), find interactions via 
STRING, correlate omics layers with statsmodels, build predictive model with scikit-learn, 
and search ClinicalTrials.gov for relevant trials.
```

**使用的 skill**：pydeseq2、pyopenms、database-lookup、statsmodels、scikit-learn

---

### 🎯 虚拟筛选活动
**目标**：为蛋白质-蛋白质相互作用发现别构调节剂

**提示词**：
```
Use available skills you have access to whenever possible. Retrieve AlphaFold structures, identify interaction interface with BioPython, search ZINC 
for allosteric candidates (MW 300-500, logP 2-4), filter with RDKit, dock with DiffDock, 
rank with DeepChem, check PubChem suppliers, search USPTO patents, and optimize leads with 
MedChem/molfeat.
```

**使用的 skill**：database-lookup、biopython、rdkit、diffdock、deepchem、medchem、molfeat

---

### 🏥 研究变异证据审查
**目标**：为遗传性癌症研究和合格审查注释一份合成或正确去标识化的 VCF

**提示词**：
```
Use available skills you have access to whenever possible. Work only with authorized synthetic
or de-identified data. Parse the VCF with pysam, annotate variants with Ensembl VEP, retrieve
ClinVar/COSMIC/NCBI Gene/UniProt evidence, and verify literature sources. Build an evidence-
traceable research summary with scientific-writing. If clinical-reports is used, create only a
visibly marked draft structure from a verified source-fact manifest for qualified review; do not
diagnose, assess individual risk, recommend treatment, or determine trial eligibility.
```

**使用的 skill**：pysam、database-lookup、paper-lookup、scientific-writing、clinical-reports

---

### 🌐 系统生物学网络分析
**目标**：从 RNA-seq 数据中分析基因调控网络

**提示词**：
```
Use available skills you have access to whenever possible. Query NCBI Gene for annotations, retrieve sequences from UniProt, identify interactions via 
STRING, map to Reactome/KEGG pathways, analyze topology with Torch Geometric, reconstruct 
GRNs with Arboreto, assess druggability with Open Targets, model with PyMC, visualize 
networks, and search GEO for similar patterns.
```

**使用的 skill**：database-lookup、torch-geometric、arboreto、pymc、networkx、scientific-visualization

> 📖 **想要更多示例？** 查看 [docs/examples.md](docs/examples.md)，获取跨所有科研领域的全面 workflow 示例和详细使用场景。

---

## 🔬 使用场景

### 🧪 药物发现与药物化学
- **虚拟筛选**：从 PubChem/ZINC 中筛选数百万个化合物，对靶蛋白进行筛选
- **先导化合物优化**：用 RDKit 分析构效关系，用 datamol 生成类似物
- **ADMET 预测**：用 DeepChem 预测吸收、分布、代谢、排泄和毒性
- **分子对接**：用 DiffDock 预测结合构象，并用亲和力导向工具重新打分
- **生物活性挖掘**：查询 ChEMBL 获取已知抑制剂并分析 SAR 模式

### 🧬 生物信息学与基因组学
- **序列分析**：用 BioPython 和 pysam 处理 DNA/RNA/蛋白质序列
- **单细胞分析**：用 Scanpy 分析 10X Genomics 数据、鉴定细胞类型、用 Arboreto 推断基因调控网络（GRN）
- **变异注释**：用 Ensembl VEP 注释研究用 VCF 文件，并检索 ClinVar 证据供合格解读
- **变异数据库管理**：用 TileDB-VCF 构建可扩展的 VCF 数据库，支持增量添加样本、高效的人群规模查询以及基因组变异数据的压缩存储
- **群体基因组学**：用 OneKGPd 查询 3,202 人 GRCh38 千人基因组队列中的变异、队列样本 ID 和亲缘关系
- **调控序列模型**：运行托管的 Genomic Intelligence 启动子、剪接、增强子、染色质、表达和基因注释预测（仅限研究用途——不用于临床或诊断决策）
- **病原体监测**：通过 GenSpectrum LAPIS API 追踪当前流行的病毒谱系及其增长速度（SARS-CoV-2、包括 H5N1 在内的流感、RSV、猴痘、麻疹、登革热等），报告滞后是实测而非假设
- **基因发现**：查询 NCBI Gene、UniProt 和 Ensembl 获取全面的基因信息
- **网络分析**：通过 STRING 识别蛋白质-蛋白质相互作用，映射到通路（KEGG、Reactome）

### 🏥 临床研究与证据 workflow
- **临床试验**：分析聚合的试验格局和方案标准，不做个体入组资格判定
- **变异证据审查**：用 ClinVar、COSMIC 和 ClinPGx 注释经授权的研究数据；合格专业人员保留解读责任
- **药物安全研究**：查询 FDA 数据库获取聚合的不良事件、相互作用和召回证据
- **临床药理学**：从浓度-时间数据中推导暴露指标，拟合房室和群体 PK 模型，关联暴露与效应，并评估给药方案、生物等效性和首次人体剂量
- **全文证据检索**：用 Paperclip 端到端搜索并阅读论文、监管申报文件和试验记录，返回固定到行号而非摘要的引文
- **决策支持评估**：准备合成或聚合的评估、证据画像、隐私和治理材料——而非实时临床决策
- **临床医生撰写的文档**：构建有据可依的报告草稿结构，并格式化已由获得授权的执业专业人员做出的治疗决策

### 🔬 多组学与系统生物学
- **多组学整合**：结合 RNA-seq、蛋白质组学和代谢组学数据
- **通路分析**：在 KEGG/Reactome 通路中对差异表达基因进行富集
- **网络生物学**：重建基因调控网络、识别枢纽基因
- **生物标志物发现**：整合多组学层面以预测患者结局

### 📊 数据分析与可视化
- **统计分析**：执行假设检验、功效分析和实验设计
- **论文图表**：用 matplotlib 和 seaborn 创建可发表级别的可视化
- **网络可视化**：用 NetworkX 可视化生物网络
- **报告生成**：用科学写作和文档工具生成可溯源的研究报告；临床报告输出仍为明显标注的草稿，且仅基于经过验证的合成、去标识化或聚合来源事实

### 🧪 实验室自动化
- **方案设计**：在经培训操作员审查前，编写并仿真 Opentrons 或 PyLabRobot 方案
- **LIMS/ELN 集成**：在明确授权远程写入的前提下，准备有范围的 Benchling 和 LabArchives 操作
- **workflow 自动化**：离线验证并仿真多步骤实验室 workflow；实际执行始终位于设备专属的操作员安全门之后

---

## 📚 可用 skill

本仓库包含 **163 项科研与学术 skill**，按多个领域组织。每个 skill 都提供了全面的文档、代码示例，以及使用科学库、数据库和工具的最佳实践。

### skill 分类

> **注意：** 下面列出的 Python 包和集成 skill 是*显式定义*的 skill——经过文档、示例和最佳实践的精心整理，以获得更强、更可靠的性能。它们不是上限：智能体可以安装和使用*任何* Python 包或调用*任何* API，即使没有专用 skill。列出的 skill 只是让常见 workflow 更快、更可靠。

#### 🧬 **生物信息学与基因组学**（27 个 skill）
- RNA-seq 流水线：Bulk RNA-seq（端到端 FASTQ -> counts -> DE -> 富集编排器）
- 序列分析：BioPython、pysam、scikit-bio、BioServices
- 单细胞分析：Scanpy、AnnData、scvi-tools、scVelo（RNA 速率）、Arboreto、Cellxgene Census
- 基因组工具：gget、当前 geniml/Gtars 区间 workflow、deepTools、FlowIO、Polars-Bio、Zarr、TileDB-VCF
- 坐标卫生：基因组坐标（在 BED/GFF/GTF/VCF/SAM/WIG 约定间转换区间，规范化变异表示，并在它们破坏分析之前捕获 0-based 与 1-based 以及组装/contig 命名不匹配）
- 群体与序列智能：OneKGPd（个体级千人基因组队列查询）和 Genomic Intelligence（托管的调控/基因表达预测；仅限研究）
- 差异表达：PyDESeq2
- 功能富集：通路富集（通过 gseapy + g:Profiler 的 ORA、GSEA/preranked、ssGSEA；GO、KEGG、Reactome、WikiPathways、MSigDB）
- 系统发育：ETE Toolkit、系统发育学（MAFFT、IQ-TREE 2、FastTree）
- 微生物组基础模型：Waypoint（Outpost Bio 的开源 Waypoint-6m/45m/170m 检查点、Atlas 539k 样本 MGnify 预训练语料库，以及八任务 Compass 基准——对分类丰度谱进行嵌入、微调、基准测试和预训练，并支持 MetaPhlAn/Kraken2/QIIME 2 转换）

#### 🧪 **化学信息学与药物发现**（10 个 skill）
- 分子操作：RDKit、Datamol、Molfeat
- 深度学习：DeepChem、TorchDrug
- 对接与筛选：DiffDock
- 分子动力学：OpenMM + MDAnalysis（MD 仿真与轨迹分析）
- 云端量子化学：Rowan（pKa、对接、共折叠）
- 类药性：MedChem
- 基准：PyTDC 1.1.15（基于其已验证的 CPython 3.11 兼容栈）

#### 🔬 **蛋白质组学与质谱**（2 个 skill）
- 谱图处理：matchms、pyOpenMS

#### 🏥 **临床研究与证据 workflow**（8 个 skill）
- 临床数据库：通过数据库查询（ClinicalTrials.gov、ClinVar、ClinPGx、COSMIC、FDA、cBioPortal、Monarch 等）
- 临床药理学：PK/PD 建模（非房室分析、房室和群体 PK、暴露-反应和 Emax、TMDD、PBPK 方向、包括 RSABE/ABEL 在内的生物等效性、异速缩放和首次人体剂量、ICH M12 下的 DDI 预测、concentration-QTc 以及贝叶斯治疗药物监测——使用标准库 + numpy/scipy，不调用专有估算软件）
- 癌症基因组学：DepMap（癌症依赖性评分、药物敏感性）
- 癌症影像：Imaging Data Commons（通过 idc-index 获取 NCI 放射与病理数据集）
- 医疗 AI 研究：PyHealth
- 决策支持研究：仅限本地的、聚合的或合成的临床决策支持评估与治理材料
- 临床文档：来源限定的 Clinical Reports 草稿，以及对经验证的临床医生决策与治疗计划进行格式化；两个 skill 均不做诊断或治疗建议

#### 🖼️ **医学影像与数字病理**（4 个 skill）
- DICOM 处理：pydicom 3.0.2，隐私优先的本地预检，不做诊断或去标识化合规声明
- 全切片成像：histolab 和仅限研究的 PathML 3.0.5
- 虚拟空间转录组学：非商业 DeepSpot-M，从 224x224 H&E 切片进行转录组范围的空间基因表达

#### 🧠 **神经科学与电生理学**（3 个 skill）
- 数据标准：BIDS（用于神经科学和生物医学数据集的大脑成像数据结构）
- 神经记录：Neuropixels-Analysis（细胞外尖峰、硅探针、spike sorting）
- 生理信号：NeuroKit2 0.2.13，用于可复现的研究 workflow——不用于诊断、监测决策或医疗设备验证

#### 🤖 **机器学习与 AI**（14 个核心 skill）
- 深度学习：PyTorch Lightning、Transformers、Stable Baselines3，以及按版本分离的 PufferLib 3.0/4.0 workflow
- 经典机器学习：scikit-learn、scikit-survival 0.28 和 SHAP
- 时间序列：aeon、TimesFM（Google 的单变量预测零样本基础模型）
- 贝叶斯方法：PyMC
- 优化：PyMOO
- 图机器学习：Torch Geometric
- 降维：UMAP-learn
- 统计建模：statsmodels

#### 🔮 **材料科学、化学与物理**（7 个 skill）
- 材料：当前拆分后的 pymatgen 封装/核心，以及有明确边界的 Materials Project 查询
- 代谢建模：COBRApy
- 天文学：Astropy
- 量子计算：Cirq、PennyLane、Qiskit、QuTiP 5.3

#### ⚙️ **工程与仿真**（6 个 skill）
- 实验室硬件 CAD：参数化 build123d 0.11.1 微流控芯片与模具、光机安装座、微孔板和比色皿适配器、行为实验台模型，对照 ANSI/SLAS 和光学平台尺寸标准检查，并以强制多视图渲染进行审查
- 数值计算：专有 MATLAB R2026a 和独立的 GNU Octave 11.3 规划/审查 workflow
- 计算流体力学：受限的 FluidSim 0.9 仿真，带数值有效性和 HPC 检查
- 实验流场测量：OpenPIV（从 PIV 图像对获取速度场、查询窗口互相关、伪矢量验证、涡量/应变率/湍流统计）
- 离散事件仿真：SimPy 4.1.2，带重复、预热和输出分析指引
- 符号数学：SymPy

#### 📊 **数据分析与可视化**（22 个 skill）
- 可视化：Matplotlib、Seaborn、科学可视化
- 地理空间分析：GeoPandas 1.1.4 和 GeoMaster（遥感、GIS、卫星影像、空间机器学习、500+ 示例）
- 数据处理：Dask、Polars、Vaex
- 网络分析：NetworkX
- 文档处理：LiteParse（带边界框和 OCR 的本地 PDF/文档解析）、MarkItDown、PDF、DOCX、PPTX 和 XLSX
- 信息图：信息图（AI 驱动的专业信息图制作）
- 图表：Markdown 与 Mermaid 写作（默认以文本图表作为文档标准）
- 探索性数据分析：针对显式支持格式的有边界本地 EDA，未知格式默认失败关闭
- 统计分析：统计分析 workflow
- 单位与测量不确定度：不确定度与单位（pint 量纲检查、GUM 不确定度预算、A/B 类评定、包含因子和扩展不确定度、蒙特卡洛传播、CODATA 常数）
- 实验设计：实验设计（随机化、区组、因子/部分因子 DOE、交叉、聚类、序贯设计；pyDOE3）
- 统计功效：t 检验、ANOVA、比例、相关、回归的样本量与功效计算——涵盖闭式解，以及针对 GLM、混合模型和聚类设计的基于仿真的方法

#### 🧪 **实验室自动化**（6 个 skill）
- 液体处理：离线优先的 PyLabRobot 规划/仿真和 Opentrons 编写，实际执行位于显式操作员安全门之后
- 云端实验室：Ginkgo Cloud Lab（无细胞体系、大肠杆菌与毕赤酵母中的蛋白表达与纯化，体外转录（IVT）RNA 合成，热位移与 Echo-MS 检测，SPR 靶点接入，以及借助自主 RAC（可重构自动化小车）基础设施生成的荧光像素画）
- 协议管理：受限的 protocols.io 读取，覆盖文档化的 v3/v4 端点，以及不执行写入的计划
- LIMS/ELN 集成：Benchling 和独立的 LabArchives 遗留 ELN 与 Inventory v1 API

#### 🔬 **多组学与系统生物学**（3 个 skill）
- 通路分析：通过数据库查询（KEGG、Reactome、STRING）和 PrimeKG
- 数据管理：LaminDB

#### 🧬 **蛋白质工程与设计**（4 个 skill）
- 蛋白质语言模型：ESM
- 糖工程：糖工程（N/O-糖基化预测、治疗性抗体优化）
- 云端实验室平台：Adaptyv（自动化蛋白测试与验证）
- 云端结构与设计平台：Tamarind（通过 REST API 或 MCP 托管 GPU 访问 AlphaFold、Boltz、Chai、ESMFold、RFdiffusion、ProteinMPNN、BoltzGen、抗体/纳米抗体设计、DiffDock/Vina 对接、结合亲和力和 MSA 生成）

#### 📚 **科学沟通**（27 个 skill）
- 文献：论文查找（PubMed、PMC、bioRxiv、medRxiv、arXiv、OpenAlex、Crossref、Semantic Scholar、CORE、Unpaywall）、文献综述、Paperzilla
- 全文语料库访问：Paperclip（覆盖约 1100 万篇全文论文、217K+ 份 FDA/PMDA/EMA 监管文档、临床试验注册库以及 UniProt/PDB/ChEMBL 条目的只读虚拟文件系统——来源限定的语义搜索、语料库级 grep、SQL 元数据查询、跨多篇论文的 map/reduce 阅读、图像视觉分析，以及固定到行号的引文）
- 高级论文搜索：BGPT 论文搜索（每篇论文 25+ 个结构化字段——方法、结果、样本量、质量评分——来自全文而非仅摘要）
- 网络情报：并行网络（网页搜索、URL/PDF 提取、深度研究、结构化富集、实体发现和周期性监控）、Exa Search 和 Research Lookup
- 研究笔记本：Open Notebook（自托管 NotebookLM 替代品——PDF、视频、音频、网页；16+ 个 AI 提供方；多说话人播客生成）
- 写作：可溯源的科学写作，以及本地、保密、授权的同行评审
- 文档处理：LiteParse、PDF、DOCX、PPTX、XLSX 和 MarkItDown
- 出版与论文 workflow：会议模板（Venue Templates）
- 演示：科学幻灯片、LaTeX 海报，以及从作者批准的本地清单生成的无宏 PPTX 海报
- 图表：科学示意图、Markdown 与 Mermaid 写作
- 信息图：信息图（10 种类型、8 种风格、色盲安全调色板）
- 引文：引文管理、pyzotero
- 插图：生成图像（使用 FLUX.2 Pro 和 Gemini 3.1 Flash Image / Nano Banana 2 的 AI 图像生成）

#### 🔬 **科学数据库与数据访问**（11 个 skill → 共 100+ 数据库）
> 统一的数据库查询 skill 可跨所有领域确定性访问 78 个公共数据库，带检索契约、分页/计数对账和端点溯源。专个 skill 覆盖专门的数据平台。BioServices（约 40 个生物信息学服务）、BioPython（通过 Entrez 访问 39 个 NCBI 子数据库）和 gget（20+ 基因组学数据库）等多数据库包进一步扩展了覆盖范围。
- 统一访问：数据库查询（78 个数据库，横跨化学、基因组学、临床、通路、专利、经济学等领域——PubChem、ChEMBL、UniProt、PDB、AlphaFold、KEGG、Reactome、STRING、ClinVar、COSMIC、ClinicalTrials.gov、FDA、FRED、USPTO、SEC EDGAR 等数十个——带可审计的过滤器和溯源）
- 癌症基因组学：DepMap（癌细胞系依赖性、药物敏感性、基因效应谱）
- 癌症影像：Imaging Data Commons（通过 idc-index 获取 NCI 放射与病理数据集）
- 知识图谱：PrimeKG（精准医学知识图谱——基因、药物、疾病、表型）
- 生物医学知识图谱搜索：[NCATS ARAX](skills/ncats-arax/)（在最多五个明确指定的 NCATS Translator 提供方上，对知识图谱进行受限的、受 Biolink 约束的单跳查询和固定端点两跳查询，并保留溯源）
- 财政数据：美国财政部财政数据（国债、财政部报表、拍卖、汇率）
- 科研机器学习资源目录：Hugging Science（跨 17 个科学领域的精选数据集、模型、博客文章和交互式 Spaces 索引——天文学、生物学、化学、气候、基因组学、材料科学、医学、物理学、科学推理等——带 `datasets`、`transformers` 和 `gradio_client` 的使用模式）
- 个体级群体基因组学：OneKGPd（3,202 人高覆盖度千人基因组队列查询）
- 托管调控基因组学：Genomic Intelligence（用于研究用途的启动子、剪接、增强子、染色质、表达和基因注释预测）
- 本体标识符：本体术语解析（将自由文本的组织、细胞类型、疾病、表型、检测、化学物、生物体和发育阶段标签解析为术语 ID，并对照 EBI OLS4 验证 CURIEs，用于 GEO/ENA/BioSamples/CELLxGENE/HCA/ISA-Tab 元数据）
- 实时病原体监测：病原体变异监测（当前流行的病毒谱系、增长速度及其携带的突变——SARS-CoV-2、包括 H5N1 在内的流感、RSV、猴痘、麻疹、登革热等，通过 GenSpectrum LAPIS API，谱系名称对照实时 pango-designation 命名解析，报告滞后实测而非假设）

#### 🔧 **基础设施与平台**（11 个 skill）
- 云计算：Modal
- GPU 加速：GPU 优化（CuPy、Numba CUDA、Warp、cuDF、cuML、cuGraph、KvikIO、cuCIM、cuxfilter、cuVS、cuSpatial、RAFT）
- 基因组学平台：DNAnexus、LatchBio
- workflow 引擎：Nextflow（构建/运行/调试 Nextflow 与 nf-core 流水线——DSL2 模块、执行器/容器、HPC/云端扩展）和 pacsomatic（nf-core/pacsomatic 肿瘤-正常体细胞变异检测 workflow 的操作员工具包）
- 显微成像：OMERO
- 自动化：Opentrons
- 资源检测：按请求或在明确的资源敏感型本地工作负载之前获取可用资源；已脱敏且不做压力测试
- workflow 挖掘：Autoskill（基于本地 screenpipe 的重复 workflow 检测与 skill 起草）
- 智能体平台开发：Pi Agent（将 Pi 用作终端编码工具，并基于 SDK、RPC/JSONL、扩展、自定义提供方/模型、包、TUI 组件和会话工具进行开发）

#### 🎓 **研究方法论与规划**（13 个 skill）
- 构思：有证据意识的科学头脑风暴和不评分的假设生成，将假设始终标注为候选
- 文本数据集假设软件：HypoGeniC/HypoRefine 生成候选文本模式和任务预测统计，而非经过验证的科学假设
- 自主优化：Arbor（假设树优化——针对开发评估器迭代改进代码/模型/智能体工具/数据产物，同时用留出的测试门防止过拟合）
- 批判性分析：科学批判性思维，以及对作品的定性低利害学者评估——绝不给人排名或支持重大决策
- 情景分析：What-If Oracle（4–6 分支可能性探索、应急规划、决策压力测试）
- 多视角审议：Consciousness Council（多元专家视角、魔鬼代言人分析）
- 认知画像：DHDNA Profiler（从任何文本中提取思维模式与认知特征）
- 资助：研究基金
- 发现：Research Lookup、论文查找（10 个学术数据库）
- 市场分析：可溯源的市场研究报告，带假设驱动的规模估算和预测敏感性

#### ⚖️ **法规与标准**（2 个 skill）
- 标准就绪：为 ISO 13485（医疗器械质量管理体系）、ISO 14971（器械风险管理）、ISO/IEC 17025（检测和校准实验室）和 ISO 15189（医学实验室）起草证据准备材料，各标准的过程域由 `--standard` 配置文件选择
- 分析方法验证：在适用框架下规划、评估和记录分析程序的验证、确认与转移（HPLC、LC-MS/MS、GC、CE、ICP-MS、溶出度、qNMR、qPCR、NIR、配体结合和细胞基检测）——ICH Q2(R2)/Q14 和 ICH M10 根据其公开许可文本编码，USP `<1220>`/`<1225>`/`<1226>`、CLSI EP 系列和 ISO/IEC 17025 仅按名称和范围引用；仅用标准库统计，无网络访问
- 保证通道分离：保持 ISO 认证、实验室认可、FDA QMSR 检查、CLIA 认证、MDSAP 和 EU MDR/IVDR 证据边界相互独立——实验室是获得认可而非认证，且 ISO 15189 认可不满足 CLIA 要求
- 绝不用于合规、审计、评估、认证、认可或方法放行等决策；如需此类结论，须经合格的 RA/QA、法律、实验室主任、评估员及认证机构人员审查确认

> 📖 **关于所有 skill 的完整详情**，参见 [docs/skills.md](docs/skills.md)

> 💡 **正在寻找实用示例？** 查看 [docs/examples.md](docs/examples.md)，获取跨所有科研领域的全面 workflow 示例。

---

## 📝 来自博客

来自 [K-Dense 博客](https://www.k-dense.ai/blog) 的深度解析、基准测试和使用本仓库 skill 直接相关的指南。

### 从这里开始

- **[Agent Skills：AI 驱动科学研究的最后一块拼图](https://www.k-dense.ai/blog/agent-skills-final-piece-for-ai-powered-research)** — 什么是 Agent Skills，为什么精选的领域指引优于原始模型能力，以及本仓库的介绍。
- **[K-Dense Web 对比 Scientific Agent Skills：我们为何两者都做（以及你该用哪个）](https://www.k-dense.ai/blog/k-dense-web-vs-scientific-agent-skills)** — 何时开源 skill 是合适的工具，何时使用带托管算力的托管平台更有意义。
- **[AI 科研伙伴，答疑：与某大学研究中心直播实录的 20 个问题](https://www.k-dense.ai/blog/ai-co-scientists-answered-20-questions)** — 来自一个正在评估 AI 科研伙伴的研究中心的实际问题：哪些保持开源并采用 MIT 许可、本地与桌面部署如何工作、数据如何处理，以及如何在托管平台与运行这些 skill 的 BYOK 方案之间选择。
- **[如何在科研中使用 Multica](https://www.k-dense.ai/blog/multica-scientific-research)** — 一个自托管 Multica 工作区加上这些 skill 的精选子集：临床试验与变异分析、文献综述、每周自动流程，以及第二模型审计，每个 skill 从 `skills/<name>/` 导入。

### skill 基准与深度解析

- **[无声的 97%：waypoint-bio 智能体 skill 介绍](https://www.k-dense.ai/blog/introducing-waypoint-agent-skill)** — [waypoint-bio](skills/waypoint-bio/) 应对静默数据丢失：一张未转换的 MetaPhlAn 表保留了 3% 的丰度质量却仍返回有效嵌入；配备 skill 的智能体在配对对比中以 16 比 0 胜出。
- **[毫米问题：lab-hardware-cad 智能体 skill 介绍](https://www.k-dense.ai/blog/lab-hardware-cad-skill)** — [lab-hardware-cad](skills/lab-hardware-cad/) 在 98 次几何评分运行中：skill 组在 49/49 的情况下生成了参数化、可再生的模型（基线 0/49），并指出了缺失的 Y-maze 标准而非自行编造。
- **[一个 skill，78 个数据库：我们为何没有建 78 个 skill](https://www.k-dense.ai/blog/database-lookup-one-skill-78-databases)** — [database-lookup](skills/database-lookup/) 的设计原理：整合使常驻上下文成本降低 13.9 倍，同时保持五个模型的路由准确性。
- **[AI 智能体能运行你的质谱流水线吗？PyOpenMS skill 基准测试](https://www.k-dense.ai/blog/benchmarking-pyopenms-skill-mass-spectrometry)** — 对 [pyopenms](skills/pyopenms/) 的 250 次运行研究：有 skill 时任务成功率 100%，无 skill 时 96%；pyOpenMS API 错误减少 92%；成本降低 10%。
- **[超越 RDKit：Rowan 智能体 skill 与实验对照基准测试](https://www.k-dense.ai/blog/benchmarking-rowan-skill-chemistry)** — [rowan](skills/rowan/) 与 RDKit 和实验数据对比：pKa MAE 0.23（R² 0.986）、logD₇.₄ MAE 1.15，约 0.52 美元算力即可获得 0.19 Å RMSD 的对接构象恢复。
- **[用 GPU 加速你的科学：一个 skill 平均提速 58 倍](https://www.k-dense.ai/blog/optimize-for-gpu-skill)** — [optimize-for-gpu](skills/optimize-for-gpu/) 跨 12 个库重写 CPU 密集型 Python，加速比从 1.7 倍到 492 倍不等。
- **[迈向更智能的科学搜索：Exa 加入 Scientific Agent Skills 库](https://www.k-dense.ai/blog/towards-smarter-scientific-search-exa-scientific-agent-skills)** — [exa-search](skills/exa-search/) 带来的新增：为学术发现而非关键字匹配调优的神经语义搜索与 URL 提取。
- **[Nano Banana 2 Lite 科学图像生成基准测试](https://www.k-dense.ai/blog/benchmarking-nano-banana-2-lite-scientific-image-model)** — 对科学图表模型进行 240 张图像的对比，有助于为 [generate-image](skills/generate-image/) 选择后端：Nano Banana 2 Lite 中位延迟 3.8 秒，对比 GPT Image 2 的 49 秒，但存在质量权衡。
- **[NVIDIA BioNeMo Agent Toolkit skill（针对 NIM 微服务）基准测试](https://www.k-dense.ai/blog/benchmarking-nvidia-bionemo-nim-skill)** — 这是一套独立的 NVIDIA skill，而非以上之一，但结论具有普适性：skill 最有助于路由到不明显端点和弱模型可靠性，且不会提升底层科学模型的准确性。

### 为什么 workflow 层很重要

- **[模型不再是瓶颈](https://www.k-dense.ai/blog/the-model-is-no-longer-the-bottleneck)** — 为什么存在这样一个仓库的论证：前沿模型现在在原始能力上已与专业科学软件相当（NMR 氢位移预测 ±0.079 ppm），因此制约因素已转移到模型周围的 workflow——数据访问、代码执行、验证和可审计输出。
- **[AI 科研伙伴已到来。瓶颈是验证。](https://www.k-dense.ai/blog/ai-co-scientist-verification-bottleneck)** — 评估研究智能体的 10 点清单，围绕公开来源、代码、数据溯源和中间产物而非一个光鲜的最终答案——这与 [database-lookup](skills/database-lookup/) 和 [scientific-writing](skills/scientific-writing/) 等 skill 中溯源和检索契约要求的逻辑一致。
- **[复现而非生成，才是 AI 在科学领域的杀手级应用](https://www.k-dense.ai/blog/reproduction-not-generation-ai-for-science)** — 为什么重跑已发表分析是智能体最高价值的用途：在 221 项研究的基准中 78% 的论文和 93% 的单项分析任务得到复现，因为复现可以对照已知数字检查，而生成的论断则不能。
- **[K-Bench 01 介绍：九个前沿模型、178 个真实科学任务，以及大量自信的错误答案](https://www.k-dense.ai/blog/introducing-k-bench-01-internal-benchmark)** — 九个前沿模型应对 178 个真实用户任务，40% 的运行出现过度声称。有助于校准智能体报告成功时应检查什么，并为上述临床、法规和研究方法 skill 中写入的验证边界提供背景。

### 安全与安全部署

- **[科学智能体时代的安全：每个实验室在安装 skill 前需要知道的事](https://www.k-dense.ai/blog/skill-security-before-you-install)** — 本仓库[安全声明](#%EF%B8%8F-安全声明)背后的实用审查清单：安装前通读完整的 `SKILL.md` 和 `scripts/`，先扫描再安装，并固定版本而非跟踪分支。
- **[沙盒化的 AI 科学家：将 NVIDIA OpenShell 与 Scientific Agent Skills 结合](https://www.k-dense.ai/blog/sandboxed-ai-scientist-openshell-skills)** — 在策略治理的沙盒中运行这些 skill；另请参见[快速开始](#-快速开始)中的 NemoClaw 注意事项。

### 互补的开源项目

- **[Science Superpowers 介绍：为你的研究智能体注入科学纪律](https://www.k-dense.ai/blog/introducing-science-superpowers)** — 假设预注册、可复现 workflow 和先验证后声称，包裹在这些 skill 周围以防 p-hacking 和 HARKing。
- **[你的 AI 助手像通才一样推理。科学需要专家。](https://www.k-dense.ai/blog/introducing-scientific-agents)** — 503 个开源 `AGENTS.md` 配置文件，与这些 skill 中的"做什么"程序一起提供"如何思考"层。
- **[mimeo 与 80+ Mimeographs 介绍](https://www.k-dense.ai/blog/introducing-mimeo-and-mimeographs)** — 通过提炼特定从业者的推理方式，生成你自己的 `SKILL.md` / `AGENTS.md` 专家档案。
- **[Agentic Data Scientist：一个真正做分析的开源 AI](https://www.k-dense.ai/blog/agentic-data-scientist-open-source)** — 一个多智能体规划、执行和验证工具，加载这些 skill 以完成端到端数据科学 workflow。
- **[Karpathy：一个开源智能体机器学习工程师](https://www.k-dense.ai/blog/karpathy-agentic-ml-engineer)** — 一个自主 ML 训练智能体，从预处理到超参数搜索都消费 Scientific Agent Skills。

---

## 🤝 贡献

我们欢迎贡献，共同扩展和改进这个科学 skill 仓库！

关于添加或更新 skill 的详细说明，请参见 [CONTRIBUTING.md](CONTRIBUTING.md)。该指南涵盖仓库结构、必需的 `SKILL.md` frontmatter、Agent Skills 规范要求、版本管理、验证、安全扫描和拉取请求预期。

### 贡献方式

✨ **添加新 skill**
- 为更多的科学包或数据库创建 skill
- 添加对科学平台和工具的集成

📚 **改进现有 skill**
- 用更多示例和使用场景增强文档
- 添加新的 workflow 和参考资料
- 改进代码示例和脚本
- 修复错误或更新过时信息

🐛 **报告问题**
- 提交带详细复现步骤的错误报告
- 提出改进建议或新功能

### 如何贡献

1. **Fork** 本仓库
2. **创建**功能分支（`git checkout -b feature/amazing-skill`）
3. **遵循** [CONTRIBUTING.md](CONTRIBUTING.md) 和现有的目录结构
4. **确保**所有新 skill 都包含有效的 `SKILL.md` 文件，带必需的 frontmatter 和 `metadata.version`
5. **充分测试**你的示例和 workflow，如果 skill 随附 `scripts/`，请在 `tests/<skill-name>/` 下添加套件
6. **提交**你的更改（`git commit -m 'Add amazing skill'`）
7. **推送**到你的分支（`git push origin feature/amazing-skill`）
8. **提交**一个带清晰变更描述的拉取请求

### 贡献指南

✅ **遵守 [Agent Skills 规范](https://agentskills.io/specification)** — 每个 skill 必须遵循官方规范（有效的 `SKILL.md` frontmatter、命名约定、目录结构）
✅ 在每份 `SKILL.md` 中包含带引号的 `metadata.version` 值
✅ 更新现有 skill 时递增 `metadata.version`
✅ 与现有 skill 文档格式保持一致
✅ 确保所有代码示例都经过测试且可用
✅ 在示例和 workflow 中遵循科学最佳实践
✅ 添加新功能时更新相关文档
✅ 在代码中提供清晰的注释和 docstring
✅ 包含对官方文档的引用

### 测试

每项随附 `scripts/` 的 skill 都必须在 `tests/<skill-name>/` 下有测试套件，并在 `tests/skill-requirements.toml` 中有条目。这是强制性的——`tests/_meta` 会拒绝引入捆绑工具却没有配套测试的拉取请求，它还会对所有 skill 运行仓库级结构契约（frontmatter 一致性、`SKILL.md` 长度、本地链接解析、脚本解析、不打包字节码、无硬编码本地路径、`--help` 行为）。

```bash
# 结构规范与覆盖检查——仅需几秒，无需科学包
uv run python -m pytest tests/_meta -q

# 单个 skill 的套件
uv run --with pytest python -m pytest tests/<skill-name> -q

# 每个套件，各自在独立的临时环境中
uv run python tests/run_all.py --isolated
```

[skill 测试](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/skill-tests.yml) workflow 在每个拉取请求上运行契约加仅标准库的套件；完整的 `--isolated` 扫描会构建约 100 个环境，在本地或按计划运行。

### 安全扫描

本仓库中的所有 skill 都使用 [Cisco AI Defense Skill Scanner](https://github.com/cisco-ai-defense/skill-scanner) 进行安全扫描，这是一个开源工具，可检测 Agent Skills 中的提示注入、数据外泄和恶意代码模式。

如果你在贡献新 skill，建议在提交拉取请求前在本地运行扫描器：

```bash
uv pip install cisco-ai-skill-scanner
skill-scanner scan /path/to/your/skill --use-behavioral
```

> **注意：** 干净的扫描结果会减少审查中的噪音，但不能保证 skill 没有任何风险。贡献的 skill 在合并前也会经过人工审查。

### 认可

贡献者会得到社区的认可，并可能出现在：
- 仓库贡献者列表
- 发布说明中的特别提及
- K-Dense 社区亮点

你的贡献有助于降低科学计算的门槛，让研究人员能更高效地利用 AI 工具！

### 支持开源

本项目建立在 50+ 个优秀的开源项目之上。如果你认为这些 skill 有价值，请考虑[支持我们所依赖的项目](docs/open-source-sponsors.md)。

---

## 🔧 故障排除

### 常见问题

**问题：skill 无法加载**
- 验证 skill 文件夹位于正确的目录（参见[快速开始](#-快速开始)）
- 每个 skill 文件夹必须包含一个 `SKILL.md` 文件
- 复制 skill 后重启你的智能体/IDE
- 在 Cursor 中，检查设置 → 规则，以确认 skill 被发现

**问题：缺少 Python 依赖**
- 解决方法：查看特定 `SKILL.md` 文件了解所需包
- 安装依赖：`uv pip install package-name`

**问题：API 速率限制**
- 解决方法：许多数据库有速率限制。查看具体数据库文档
- 考虑实现缓存或批量请求

**问题：认证错误**
- 解决方法：某些服务需要 API 密钥。查看 `SKILL.md` 了解认证设置
- 验证你的凭据和权限

**问题：示例过时**
- 解决方法：通过 GitHub Issues 报告问题
- 查看官方包文档获取更新后的语法

**问题：`gh skill install` 或指向 `scientific-skills/` 的文档链接失败（v2.43.0+）**
- 自 v2.43.0 起，skill 位于 `skills/`（而非 `scientific-skills/`）下，以匹配 GitHub CLI 期望的 Agent Skills 布局
- 将手动复制路径、书签和引文从 `scientific-skills/<name>` 更新为 `skills/<name>`
- 拉取最新版本后重新运行 `gh skill install K-Dense-AI/scientific-agent-skills`

---

## ❓ 常见问题（FAQ）

### 常规问题

**问：这是免费使用的吗？**
答：是的！本仓库采用 MIT 许可。不过，每个 skill 在 `SKILL.md` 文件的 `license` 元数据字段中有自己的许可证——请务必查看并遵守这些条款。

**问：为什么所有 skill 都合在一起，而不是分成单独的包？**
答：我们相信，AI 时代的好科学本质上是跨学科的。把所有 skill 捆绑在一起，让你（和你的智能体）能够轻松跨领域衔接——例如在一个 workflow 中结合基因组学、化学信息学、临床数据和机器学习——而不必担心该安装或对接哪些 skill。

**问：我可以将其用于商业项目吗？**
答：仓库本身采用 MIT 许可，允许商业使用。但单个 skill 可能有不同的许可证——请检查每个 skill `SKILL.md` 文件中的 `license` 字段，以确保符合你预期的用途。

**问：所有 skill 都有相同的许可证吗？**
答：不是。每个 skill 在 `SKILL.md` 文件的 `license` 元数据字段中有自己的许可证。这些许可证可能不同于仓库的 MIT 许可。用户有责任审查并遵守他们使用的每个 skill 的许可条款。

**问：多久更新一次？**
答：我们会定期更新 skill，以反映包和 API 的最新版本。主要更新会在发布说明中宣布。

**问：我可以与其他 AI 模型一起使用吗？**
答：核心 `SKILL.md` 格式遵循开放 [Agent Skills](https://agentskills.io/) 标准。安装路径、发现和可选元数据支持因 host 和版本而异，因此请确认你目标 host 的当前文档。

### 安装与设置

**问：我需要安装所有 Python 包吗？**
答：不需要！只安装你需要的包。每个 skill 在 `SKILL.md` 文件中指定其要求。

**问：如果某个 skill 不起作用怎么办？**
答：先查看[故障排除](#-故障排除)一节。如果问题仍然存在，请在 GitHub 上提交带详细复现步骤的 issue。

**问：这些 skill 可以离线使用吗？**
答：数据库 skill 需要联网以查询 API。包 skill 在安装好 Python 依赖后可以离线工作。

### 贡献

**问：我可以贡献自己的 skill 吗？**
答：当然！我们欢迎贡献。参见[贡献](#-贡献)一节了解指南和最佳实践。

**问：如何报告错误或建议功能？**
答：在 GitHub 上提交带清晰描述的 issue。对于错误，请包含复现步骤以及预期与实际行为。

---

## 💬 支持

需要帮助？以下是获取支持的方式：

- 📖 **文档**：查看相关的 `SKILL.md` 和 `references/` 文件夹
- 🐛 **错误报告**：[提交 issue](https://github.com/K-Dense-AI/scientific-agent-skills/issues)
- 💡 **功能请求**：[提交功能请求](https://github.com/K-Dense-AI/scientific-agent-skills/issues/new)
- 📣 **更新与演示**：关注 [X](https://x.com/k_dense_ai)、[LinkedIn](https://www.linkedin.com/company/k-dense-inc)、[YouTube](https://www.youtube.com/@K-Dense-Inc) 和 [Reddit](https://www.reddit.com/user/-k-dense-/)，了解新 skill、教程和 Scientific Agent Skills 版本动态
- 💼 **企业支持**：联系 [K-Dense](https://k-dense.ai/) 获取商业支持

---

## 📖 引用

如果你在研究或项目中使用 Scientific Agent Skills，请引用整个合集，并在相关时引用实质支持了你工作的单个 skill。

合集引用有助于他人找到仓库、理解你 workflow 中使用的更广泛 skill 生态，并认可 Scientific Agent Skills 背后的维护工作。单个 skill 引用则更精确地归功于你的智能体使用的特定包、数据库或 workflow 指引。

推荐做法：
- 始终使用以下格式之一引用 **Scientific Agent Skills**。
- 同时引用对你的分析、代码、图表、报告或研究 workflow 有直接贡献的每个 skill。
- 如果一个 skill 封装或记录了外部包、数据库或平台，当你的领域规范要求时，也请引用该上游项目。

### 合集引用

#### BibTeX
```bibtex
@software{scientific_agent_skills_2026,
  author = {{K-Dense Inc.}},
  title = {Scientific Agent Skills: A Comprehensive Collection of Scientific Tools for AI Agents},
  year = {2026},
  url = {https://github.com/K-Dense-AI/scientific-agent-skills},
  note = {161 skills covering databases, packages, integrations, and analysis tools}
}
```

#### APA
```
K-Dense Inc. (2026). Scientific Agent Skills: A comprehensive collection of scientific tools for AI agents [Computer software]. https://github.com/K-Dense-AI/scientific-agent-skills
```

#### MLA
```
K-Dense Inc. Scientific Agent Skills: A Comprehensive Collection of Scientific Tools for AI Agents. 2026, github.com/K-Dense-AI/scientific-agent-skills.
```

#### 纯文本
```
Scientific Agent Skills by K-Dense Inc. (2026)
Available at: https://github.com/K-Dense-AI/scientific-agent-skills
```

### 单个 skill 引用

当引用特定 skill 时，请包含 skill 名称、该 skill `SKILL.md` 中 `metadata.version` 的版本号，以及 skill 的直接 URL。例如：

```bibtex
@software{scientific_agent_skills_astropy_2026,
  author = {{K-Dense Inc.}},
  title = {Astropy Skill for Scientific Agent Skills},
  year = {2026},
  url = {https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/astropy},
  note = {Version 1.0, part of Scientific Agent Skills}
}
```

纯文本格式：

```text
Astropy skill for Scientific Agent Skills, version 1.0.
K-Dense Inc. (2026).
https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/astropy
```

如果您在出版物、演示或项目中受益于这些 skill，我们深表感谢。

---

## 📄 许可证

本项目采用 **MIT 许可证**。

**版权所有 © 2026 K-Dense Inc.**（[k-dense.ai](https://k-dense.ai/)）

### 要点：
- ✅ **免费用于任何用途**（商业和非商业）
- ✅ **开源** - 可自由修改、分发和使用
- ✅ **宽松** - 对再利用的限制极少
- ⚠️ **无担保** - 按"原样"提供，不附带任何形式的保证

完整条款参见 [LICENSE.md](LICENSE.md)。

### 单个 skill 许可证

> ⚠️ **重要**：每个 skill 在 `SKILL.md` 文件的 `license` 元数据字段中有自己的许可证。这些许可证可能不同于仓库的 MIT 许可，并可能包含附加条款或限制。**用户有责任审查并遵守他们使用的每个 skill 的许可条款。**

## ⭐ 星标历史

<a href="https://star-history.dera.page/#K-Dense-AI/scientific-agent-skills">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://star-history.dera.page/svg?repos=K-Dense-AI/scientific-agent-skills&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://star-history.dera.page/svg?repos=K-Dense-AI/scientific-agent-skills" />
   <img alt="Star History Chart" src="https://star-history.dera.page/svg?repos=K-Dense-AI/scientific-agent-skills" />
 </picture>
</a>
