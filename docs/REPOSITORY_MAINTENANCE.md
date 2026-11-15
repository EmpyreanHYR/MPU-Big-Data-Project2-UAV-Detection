# 仓库维护记录

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
- 不提交数据、权重、私有设备路径和账号信息；不要删除仍承担结果来源证明的历史记录。
- 提交前运行 `python scripts/check_project.py`。报告正文或图表发生变更时，再运行 `python scripts/build_report.py`。
