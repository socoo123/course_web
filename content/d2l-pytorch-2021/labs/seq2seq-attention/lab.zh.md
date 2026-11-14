---
title: Seq2Seq、翻译与注意力
kind: 编者阶段练习（非官方编号Lab）
source: 《动手学深度学习》当前中文第二版9.5–9.8、10.2–10.4；practice-plan四任务
source_commit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
status: 四任务要求与实现路线完整；worker未运行数值或训练，主验收实际范围见公共资料
license: 教材Apache-2.0不覆盖语料；ManyThings筛选Tatoeba句子，公开使用保留逐句署名及CC BY条件；不再分发语料全文
---

# Seq2Seq、翻译与注意力

## 学习问题：翻译变好了，还是答案被偷看了？

建立一条可解释的小型英译法链路：同一真实双语数据、同一划分，先训练固定上下文的seq2seq，再引入可随解码步变化的注意力。先证明信息边界正确，再讨论损失、搜索和对齐。模型可以译错；不能把teacher forcing的预测当自由翻译，把合成注意力图当真实模型的对齐。

本实验由你在本地用Python/PyTorch自行实现，程序、配置和学习记录仅供自己保存与自检；无需Git提交、推送、上交报告或上传本站，也不要求排行榜提交。个人学习与任务进度不作为教程完成条件，不由agent认证或追踪。

按[实验指导](#/c/d2l-pytorch-2021/lab/seq2seq-attention?v=guide)自行实现。本地使用Python/PyTorch练习。

### 四任务原身份

| 任务ID | 原任务 |
|---|---|
| `seq2seq-attention-1` | 建立双语词表、padding、有效长度与mask，区分teacher forcing训练和逐词推理。 |
| `seq2seq-attention-2` | 完成seq2seq基线并解释贪心与束搜索；在小例上比较搜索行为，不保证束宽越大越好。 |
| `seq2seq-attention-3` | 实现核回归注意力小例、加性/点积打分与masked softmax，检查padding权重。 |
| `seq2seq-attention-4` | 加入Bahdanau注意力，对相同固定验证样本比较基线与注意力模型并绘制对齐权重。 |

## 任务1：双语数据与信息边界

### A. 两个同名压缩包，不是同一个版本

教材注册的`fra-eng.zip`是ManyThings/Tatoeba英法句对的历史镜像。包内`_about.txt`标注2019-04-07，说明数据来自Tatoeba的`sentences_detailed.csv`；`fra.txt`有167130行、每行两列，**没有当前发布包的逐句署名列**。本次实取压缩包SHA-1与教材注册值一致；这只验证文件身份，不证明可以把缺失的作者信息忽略后公开再分发。

本阶段真实小训练选用**当前ManyThings发布包**：页面标注2026-02-13更新，英法240521对，每行是“英语TAB法语TAB署名”。下载后分别记录实际包与文本hash，不复用教材2019镜像的hash或行号。保留第三列中的句子ID、句主用户名、来源与许可；它只进元数据，不进入任何模型输入或词表。包内说明、两个版本的校验及使用条件见页底与来源清单。

语料只放仓库外的运行缓存，不提交压缩包、句对全文或权重。公开展示少量验证例时，将原句、参考译文、句主/句子ID链接、ManyThings/Tatoeba署名及许可关联到同一记录；明确小写化/分词等修改。模型生成不是人工参考，也不能给模型输出冒用参考作者署名。

### B. 固定划分合同

下面是**编者小实验方案**，不是教材提供的官方训练/验证/测试集。先完成身份核对，再执行：

1. 按原文件行序解析英语、法语、署名。仅清洗前两列：将U+202F与U+00A0改为空格，转小写，在`,.!?`前补空格，再按空白分词、单空格连接；不移除法语重音、不拆撇号、不做额外词干化。排除空句/不合法字段行并计数。
2. 以完整清洗后的`(source,target)`去重，保留首次出现的原始行号与署名。不要先截断再把不同长句认作同一句。重复句对不能跨段。
3. **按清洗后的完整源句分组**，比只按句对分组更严格：同一英语句的不同法译进入同一段。令`h`为UTF-8字符串`"p9-v1\t" + source`的SHA-256前8位十六进制转整数，再取`h % 100`。结果`0–79`训练、`80–89`验证、`90–99`测试。比例是分桶规则，不保证句对数恰好80/10/10。
4. 各段保留原文件顺序，取训练前512对、验证前64对用于小运行；测试封存。ManyThings按长度排序，因此此子集偏短，**不是随机代表总体的翻译基准**。各段相同目标句仍可能出现；没有声称消除全部近重复或语义重合。
5. 只在这512个训练句对上分别拟合源词表、目标词表，`min_freq=1`；不是先在全库/完整训练桶fit后再选512。固定特殊ID为`<unk>=0,<pad>=1,<bos>=2,<eos>=3`，普通词按频数降序、同频按Unicode字典序。验证未见词映射到`<unk>`，不更新词表。记录两词表hash与验证OOV数。
6. 保存清洗版本、所有分桶统计、去重数、所取原始行号/句对hash、同源跨段交集与重复句对跨段交集。测试数据只参与划分身份统计，不用于词表、调参、指标或选样。

这套固定方案的实际统计和是否执行，以[公共资料](#/c/d2l-pytorch-2021)中的主验收为准，不把要求表写成运行结果。

### C. 长度、EOS与teacher forcing

两端统一最大数组长度$N=12$，先取正文前$N-1=11$个词元，**再添加EOS**，剩余右侧补PAD。有效长度包括EOS、不包括PAD，必在$[1,N]$；记录源端与目标端截断数量。教材“先加EOS再整体截断”的示例可能截掉EOS，本实验刻意改为保留EOS。截断后的EOS表示实验序列终点，不保证原长句真的在这里结束。

目标数组`Y`包含EOS；解码训练输入为`BOS + Y`去掉最后一列。第$t$步只看到之前的目标词，不看到正在预测的$Y_t$。例如以下**自拟符号例**，不是语料或训练输出：

| 位置 | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| 目标Y | A | B | EOS | PAD | PAD |
| 解码输入 | BOS | A | B | EOS | PAD |
| 损失mask | 1 | 1 | 1 | 0 | 0 |

目标有效长度只服务于训练/评分的损失mask。自由推理接口只接收源序列、源有效长度和自己已经生成的历史；**不接收参考目标、参考长度或参考EOS位置**。改写/打乱参考译文不能改变一次已固定模型的生成。

## 任务2：固定上下文基线与搜索

### A. 编解码状态的合同

采用单层、单向GRU，源/目标独立embedding。符号：batch为$B$，源数组长$S$，目标数组长$T$，嵌入维$E$，隐维$H$，目标词表大小$V_t$。

| 对象 | 形状与责任 |
|---|---|
| 源ID、源有效长度 | `(B,S)`、`(B,)` |
| 编码器输出 | `(B,S,H)`；供后续注意力使用 |
| 编码器有效终态 | `(1,B,H)`；每行停在自己最后一个有效词元 |
| 固定上下文c | `(B,H)`；保存编码终态最后一层，不随解码推进改变 |
| 解码器动态hidden | `(1,B,H)`；每步更新，初始为编码终态 |
| 解码器输入 | 上一步目标embedding与c拼接，最后维`E+H` |
| 输出logits | `(B,T,V_t)`；不是softmax后的概率 |

**源有效长度必须影响编码器终态。** 仅将PAD的embedding设零仍会让GRU在PAD步更新；仅对注意力权重加mask也救不回被padding改变的初始hidden。推荐用packed sequence；或单层单向时从每行最后有效输出取终态，显式证明等价。扩展到多层/LSTM/双向不能机械把顶层输出当所有状态。

基线状态要分开保存`fixed_encoder_context`与`decoder_hidden`。固定教材PyTorch示例每次`forward`重新从传入`state[-1]`取context：整段teacher forcing和逐token调用会有不同的context更新边界。本实验按数学上的固定上下文基线实现，**不声称逐字复现该预测helper**。关闭dropout，整段teacher forcing与逐步输入同一真实前缀的logits应一致。

### B. 训练损失与有限预算

未归约交叉熵为$l_{bt}$，目标mask为$m_{bt}$：

$$
A=\sum_{b,t}m_{bt}l_{bt},\qquad K=\sum_{b,t}m_{bt}
$$

$$
L=A/K
$$

EOS计入有效目标token，PAD不计，UNK仍计。一次更新使用该batch的$A/K$；一个epoch或验证集指标重新累计所有$A,K$后相除，不平均句均值/batch均值。教材示例对时间轴`mean`再按token数汇总的数值不能冒充此处有效token CE。改变右侧PAD数量不能稀释本实验损失。

固定小预算：两模型均`E=32,H=32`，单层GRU、dropout 0，batch 32，Adam学习率0.005，全局梯度L2裁剪阈值1，20轮。模型seed为2029，数据洗牌使用独立seed 2030生成并复用同一批次顺序；记录实际更新步数和参数量。相同$H$不等参数量，短训练不支持架构优劣的普遍结论。初末CE用相同数据、`eval`及不建图模式重算；验证不修改参数、buffer或既有梯度。

### C. 贪心与beam必须走完整状态

先完成贪心：BOS起步，把自己的预测回送，遇EOS停止；未出EOS最多生成12个token（EOS也占一个生成位置），记录`eos`或`max_length`终止原因。BOS/PAD不允许成为输出候选，UNK允许；在`log_softmax`后屏蔽BOS/PAD候选，不重新归一化，其余分数仍是原模型log概率。

再完成束宽$k=1,3$的合成小例比较（可额外加入其他束宽）。每个候选至少保存：历史token、累计log概率、动态hidden、固定context、源身份、源长度、完成标记；注意力版本还包括源memory与该路径的注意力历史。top-k选的是“父beam×下一token”，不只是下一token。按父索引同步重排所有状态，允许一个父项被复制成多个子项，不能只重排token。

规定一个可复核的搜索版本：每步将未完成候选扩展，与已完成候选原样合并，再保留累计log概率最大的$k$项；已完成项不继续解码、不再累计EOS、不增长长度。学习者应明确同分顺序，例如父索引、token ID；本次小实测使用PyTorch 2.5.1 CPU `topk`的返回顺序，再稳定排序合并候选，没有验证跨设备同分顺序一致。直到全部保留项完成或到最大长度，**不在第一个EOS出现时停止**。末轮若保留池有已完成候选，仅在其中按下式终选；否则在未完成候选中终选并标`max_steps_unfinished`：

$$
s(y)=\frac{\sum_{t=1}^{L}\log p(y_t\mid y_{<t},x)}{L^{\alpha}}
$$

$L$不含BOS，含已生成EOS；未完成项用实际生成长度。机制对照先取$\alpha=0$，真实beam3取0.6，明确中间剪枝仍按原始累计分数、终选优先已完成集合。这是有限beam近似，不保证最终归一化目标全局最优。$\alpha>0$减轻负log分数的短句偏好，不是简单“惩罚长句”。相同策略下$k=1$应等于贪心；增大束宽不保证BLEU上升。

用极小有限状态概率树枚举全体允许路径作oracle，并展示至少一次贪心非最优与父状态重排。**这是搜索机制检查，不是机器翻译训练成绩。** 真实小模型的生成至少用贪心；若报告真实beam比较，须同checkpoint、同验证句、同终止与打分约定。

## 任务3：从核回归到两类注意力

### A. 独立合成核回归

自拟一维键值点，先比较均值汇聚与高斯核汇聚：查询$q$、键$k_i$、值$v_i$。

$$
e_i=-\tfrac12\bigl(w(q-k_i)\bigr)^2
$$

$$
a_i=\operatorname{softmax}(e)_i,\qquad c=\sum_i a_i v_i
$$

固定$w=1$是非参数版本；可学习$w$的版本用留一法：训练查询为第$i$个点时，从键值中去掉同一个样本，不能让模型靠无限窄核复制自己的标签。用固定非零初始$w$检查梯度，再做短更新与曲线/权重图；记录噪声、seed、训练点和独立查询。$|w|$越大通常越尖锐，$w=0$给均匀权重且该参数梯度可能为零。此合成回归不属于翻译语料训练。

### B. 加性、点积、masked softmax

要求两种评分均实现并说明形状，而不是把其中一种删成链接：

$$
e_{ji}=v_a^\top\tanh(W_q q_j+W_k k_i)
$$

$$
e_{ji}=q_j^\top k_i/\sqrt d
$$

加性评分允许原始query/key特征维不同，先各自映射到共同注意力隐维；点积要求最后维同为$d$（必要时先投影）。两者的score与权重均为`(B,Q,S)`，value为`(B,S,Dv)`，输出为`(B,Q,Dv)`。softmax沿**源key轴S**。

源有效长度`(B,)`在每个query共享，或机制函数接收`(B,Q)`表示各query长度。mask要在softmax前排除非法key；不是把softmax结果乘mask后不重归一化。该实验拒绝有效长度0/越界：清洗非空且保留EOS保证每行至少一个key。全mask输入应明确报合同错误，不能用有限负数填满后得到“均匀注意力”或让全负无穷产生NaN后悄悄改零。

检查：有效权重非负且和为1；PAD位置为0；同分key均匀；加常数到一行有效score不改变权重；只改PAD区的key/value不改变输出；梯度有限且流向合法query/key/value。画归一化权重时关闭dropout或取dropout前权重，不能要求dropout后每行严格和为1。

## 任务4：Bahdanau与真实样本对齐

保留任务2所有数据、损失、推理约定，只将固定$c$改为随解码步变化的$c_t$。第$t$步query是**更新前**的解码器hidden $s_{t-1}$；key与value都是编码器各有效位置输出，先算注意力context，再与上一词embedding拼接进入GRU。不要用已经消费当前目标的状态查询。

两模型使用同一512训练对、64验证对、两词表、批次顺序、更新预算与生成上限；分别报告参数量、初末训练CE、验证CE、真实生成、终止情况与下节BLEU。注意力参数更多，不能称为严格等参数比较。不能要求注意力一定更优或把结果不佳改成漂亮手写译文。

预先固定展示验证集前几条，不按译得好坏挑样本。对每条保存原始行号、句对hash、句主/ID、源token、完整参考文本、两模型生成、checkpoint、解码方式。真实对齐图必须来自**同一次注意力模型自由生成**，行对应预测token（可含EOS并标记），列对应源有效token（含源EOS、不含PAD）；权重来自该次真实forward，不用教材图或人工对角线填充。基线没有注意力矩阵，标注“不适用”，不能杜撰基线对齐。

图可很平、模型可重复词；解释这是观察到的权重，不是人工词对齐真值，也不是因果解释。teacher-forcing对齐若额外提供，必须另标模式，不能与自由生成混用。

## 统一评估口径

主报告采用**语料级BLEU-2**：对完整固定64条验证输出逐句计数、句内裁剪，再汇总unigram/bigram的匹配数和总数；不跨句拼n-gram，不平均64个句级BLEU。每句一个对应参考，不把同源其他译文暗中增加为多参考。此处为短句小运行明确选择2阶，不称为标准BLEU-4基准。

- 假设与参考均采用上面的预处理/空白分词，已小写，不再次`13a`切分。两个阶数各权重$1/2$，**无平滑、固定阶数2、不使用effective-order**，分数为0–1。使用自编计数器时保留合同版本及计数，不冒称某评测库的输出。
- 计分前删除生成中的BOS/PAD和首个EOS及其后部分；正常候选屏蔽下BOS/PAD不会出现。UNK保留为模型失败的可见符号；**参考用清洗后的完整文本，不把参考OOV替换成UNK，也不按训练截断长度截短参考**。记录参考长句数，避免截断系统通过缩短答案抬分。
- 汇总精确率为$p_1,p_2$，总生成/参考长度为$C,R$。$C>0$且两阶分母/匹配均非零时，用下式；任一阶零匹配或没有候选bigram时得0，不能自动退化到unigram。整组空输出得0；个别空输出仍贡献参考长度，不能删掉难例。

$$
\mathrm{BP}=\exp(\min(0,1-R/C))
$$

$$
\mathrm{BLEU}=\mathrm{BP}\sqrt{p_1p_2}
$$

- 句级诊断另用2阶、仅bigram的add-one平滑与effective-order：unigram不平滑；有bigram时$p_2=(m_2+1)/(n_2+1)$，只有一个预测词时只用unigram；空预测为0。这只是另一个诊断口径，不能与语料级无平滑分数混比。
- 教材示例`bleu(...,k=2)`是特定句级示例，使用$2^{-n}$指数（两阶不是等权）；不能与本实验语料级BLEU-2混称同一指标。标准原论文常用4阶等权，若扩展到BLEU-4或sacreBLEU须另报阶数、分词、平滑、版本/signature和0–1或0–100尺度。

保存$n$阶匹配/分母、候选/参考总长度、BP、完整配置和原样生成，以便重算。BLEU反映词面匹配，单参考短句可能把合理异译判低；不以这64条的高低推断通用翻译质量。

## 本地自检清单与证据边界

1. **数据账**：两个下载物身份分开；实际训练版本、许可与署名、清洗/去重/分桶/子集/词表hash、OOV与截断统计。
2. **机制账**：teacher forcing错位、padding终态不变、固定context跨调用一致、有效token损失、核回归留一与梯度、加性/点积/mask、beam完整父状态与EOS。
3. **真实训练账**：两模型相同样本和预算、参数量、有限更新、CE、原样生成、语料BLEU、同样本真实对齐。合成机制通过不能填进此栏。
4. **解释账**：翻译错误、搜索和模型误差、短句偏差、指标边界、未运行的扩展。CPU记录不外推GPU吞吐，不把机制检查或主验收小运行当学生全部任务完成。

本站统一数值、真实小训练与页面验收结果见[公共资料](#/c/d2l-pytorch-2021)。本页规定的是合同；worker未自行训练或运行测试。

## 引用与来源

- 阿斯顿·张、李沐、扎卡里·C. 立顿、亚历山大·J. 斯莫拉，《动手学深度学习》，当前中文第二版固定提交`e6b18ccea71451a55fcd861d7b96fddf2587b09a`，不是2021课程快照。[9.5数据](https://zh.d2l.ai/chapter_recurrent-modern/machine-translation-and-dataset.html)、[9.6接口](https://zh.d2l.ai/chapter_recurrent-modern/encoder-decoder.html)、[9.7 seq2seq](https://zh.d2l.ai/chapter_recurrent-modern/seq2seq.html)、[9.8搜索](https://zh.d2l.ai/chapter_recurrent-modern/beam-search.html)、[10.2核回归](https://zh.d2l.ai/chapter_attention-mechanisms/nadaraya-waston.html)、[10.3评分](https://zh.d2l.ai/chapter_attention-mechanisms/attention-scoring-functions.html)、[10.4 Bahdanau](https://zh.d2l.ai/chapter_attention-mechanisms/bahdanau-attention.html)。任务为编者整合，不是官方Lab逐字翻译；10.4是Bahdanau的实际章节号。
- [教材S3镜像](https://d2l-data.s3-accelerate.amazonaws.com/fra-eng.zip)：3420152字节，SHA-1匹配教材注册值，详见下表。包内说明标2019-04-07、一般CC BY 2.0链接；文本全两列，不能凭空恢复逐句作者。
- [ManyThings发布页](https://www.manythings.org/anki/)与[当前英法包](https://www.manythings.org/anki/fra-eng.zip)：Charles Kelly整理的Tatoeba精选句对，非教材作者原创语料。页面说明筛选母语者/校对句仍可能有错，并按长度排序；当前第三列保留逐句ID与用户名。本站使用较新的带署名版本，不将其称为教材2019下载物的逐字节副本。
- 当前发布包实取8242175字节，包内`fra.txt`为36202401字节；`_about.txt`日期2026-02-13。实际身份校验如下，两包全文均只在外部缓存，本站仅保存说明原件和校验记录。

| 文件 | 算法 | 实测校验值 |
|---|---|---|
| 教材2019包 | SHA-1 | `94646ad1522d915e7b0f9296181140edcf86a4f5` |
| 教材2019包 | SHA-256 | `fa96382b2c8b609e1662654c1e6e6baeb8d30b3bf63dfb4a5a261cc36347df13` |
| 当前2026包 | SHA-1 | `e11256f7c7f592e3f224ff7bb6c5430b3efbbbfb` |
| 当前2026包 | SHA-256 | `9e35994767f7307dc1fa9d5efcc36681f3756a1bdaaa02c1381b3eb11461261e` |
| 当前fra.txt | SHA-256 | `5fb8a159269e50d5de145ace082aa89da55b988969cf0cd61a4fb7e7aae84548` |

- [Tatoeba使用条件§6.2、§6.5](https://tatoeba.org/en/terms_of_use)：文本默认CC BY 2.0 France，使用、修改、传播须遵守署名条件；音频许可可能另有条件，本实验不使用音频。[CC BY 2.0 FR说明](https://creativecommons.org/licenses/by/2.0/fr/deed.en)允许分享/改编包括商业用途，需适当署名、许可链接、标明修改，不暗示背书，不施加额外限制；不保证所有其他权利均已清除。ManyThings明确再分发时应署名每个句主，不能用教材Apache-2.0替代。本站不发布完整语料。
- [PyTorch 2.5 pack_padded_sequence](https://docs.pytorch.org/docs/2.5/generated/torch.nn.utils.rnn.pack_padded_sequence.html)：有效长度、batch轴和排序约定；本实验实现路线补充，不宣称2021 Notebook已原样兼容现代环境。
- Kishore Papineni、Salim Roukos、Todd Ward、Wei-Jing Zhu，2002，[BLEU: a Method for Automatic Evaluation of Machine Translation](https://aclanthology.org/P02-1040/)，§2.1.1、§2.3（编者指标补充）。[sacreBLEU v2.5.1说明](https://github.com/mjpost/sacrebleu/blob/v2.5.1/README.md)，Scoring、Version Signatures、Languages & Preprocessing；阅读文档不等于该版本已经安装或运行。
- 原件、实际阅读范围、hash、许可片段及未运行数值合同位于`sources/p9-seq2seq-attention/`。本实验不另建课堂稿、材料翻译或英文Lab；未阅读课堂音视频，不编造课堂时间码或问答。
