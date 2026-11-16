# 仓库维护记录

2026年11月16日：同步Git跟踪的进展、核查、复现与演示说明。当前统计为19个有效权重、11个scratch100主比较、GPU19组/Pi CPU17组/H10七组；LLM候选复核已完成负面结果，GUI模型与3分46秒视频已有公开Release。课程附件状态与实验未完成项分别记录在[核查清单](report/REVIEW_CHECKLIST.md)，旧阶段清单可从Git历史查看。

本次仅维护说明文件及检查摘要。提交报告的PDF、TeX、中文稿、BibTeX、IEEE类文件和全部图表保持原字节；提案、原始模板、代码、配置及实验数值也保持原样。文档检查和受保护文件哈希核对见[检查摘要](REPOSITORY_CHECKS.json)。

2026年11月15日：整理当前阅读入口，移除12个已被替代或不再适用的文件，工作树减少约4.64 MiB。提交历史仍保留旧文件，Git历史体积不会因此立即缩小。

| 移除内容 | 数量 | 原因与替代位置 |
|---|---:|---|
| `docs/results/figures/final_pconv_p2_20261104.*` | 4 | 旧网络图布局；统一使用[当前报告网络图](report/figures/final_pconv_p2.pdf)及其draw.io源 |
| `docs/results/figures/pconv_module_20261105.*` | 3 | 独立旧PConv图；当前图1已合入PConv/P2细节，保留[模块编辑源](report/figures/pinp2_modules.drawio) |
| `docs/report/figures/pinp2_modules.pdf/png/svg` | 3 | 未被当前报告引用的独立模块导出；保留draw.io，避免同一内容多份成品 |
| `docs/datasets/metadata/sirst_v2_count.json`、`sirst_v2_split_counts.json` | 2 | 早期候选数据集计数；当前数据协议未使用SIRST-V2，也无代码或文档依赖这两个文件 |

同时精简根README、项目状态和报告导航，修正结果／实验导航的旧数量与未完成状态。`REPOSITORY_CHECKS.json`只保留当前概况与核验记录，旧排版、旧待办和历史润色过程可从Git查看。

有效的旧实验结果、失败与取消说明、可编辑图源、模型适配器、仍被脚本／测试引用的历史配置继续保留。历史证据按日期解释，不把旧结论作为当前状态。原始数据、权重、私有运行记录及模板原件未清理。

## 找回旧文件

清理前完整版本为 `5d894e9`。查阅旧文件使用：

```sh
git show 5d894e9:docs/datasets/metadata/sirst_v2_count.json
```

确实需要恢复单个文件时，在仓库根目录运行 `git restore --source=5d894e9 -- 文件路径`；恢复后再判断是否要纳入当前工作。

## 后续维护约定

- 组员阅读以根README、项目状态和当前报告为入口，避免在多处追加相同进度。
- 新指标放入结果文件并注明模型、数据、初始化与评价口径，再更新结果导航。
- 报告图保留编辑源和实际使用的导出；不要把旧布局继续放入当前成果目录。
- 原始数据、PT/ONNX、私有设备路径和账号信息不写入Git；已批准的最终GUI HEF、匹配元数据与演示媒体通过Release提供，下载时核验发布清单。不要删除仍承担结果来源证明的历史记录。
- 仅说明文件变更时运行 `python scripts/check_repository.py`、`python scripts/check_references.py` 和 `git diff --check`，并检查报告及实验数据哈希。代码变更再运行适用测试；报告正文或图表确需修改时才运行会替换正式PDF的 `python scripts/build_report.py`。
