---
title: 检测、分割与风格迁移实践
kind: 编者阶段练习（非官方编号 Lab）
source: 固定中文第二版13.3–13.12、官方牛仔行头竞赛页面与torchvision0.20.1
source_commit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
version_boundary: 当前第二版固定源码，不是2021全书快照；非课堂整理
license: 教材代码、数据、预训练权重与第三方图片分别核查；不发布原图或权重
status: 四任务合同已编写；worker未执行训练或数值验收；本批实际执行范围以公共资料主验收为准
---

# 检测、分割与风格迁移实践

## 学习问题：输出不再是一个类别时，怎样知道模型真的做对了？

检测要同时回答“是什么、在哪里”；分割要回答每个有效像素属于什么；风格迁移则直接优化一张图像。三者共用卷积与梯度，却不能共用同一套标签、损失分母和验收证据。

先复用[LEC40边界框](#/c/d2l-pytorch-2021/lec/lec40?v=notes)与[LEC41锚框](#/c/d2l-pytorch-2021/lec/lec41?v=notes)，再串联[架构](#/c/d2l-pytorch-2021/lec/lec43?v=notes)、[小SSD](#/c/d2l-pytorch-2021/lec/lec44?v=notes)、[分割数据](#/c/d2l-pytorch-2021/lec/lec45?v=notes)、[转置卷积基础](#/c/d2l-pytorch-2021/lec/lec46?v=notes)、[线性伴随视角](#/c/d2l-pytorch-2021/lec/lec47?v=notes)、[FCN](#/c/d2l-pytorch-2021/lec/lec48?v=notes)与[风格迁移](#/c/d2l-pytorch-2021/lec/lec49?v=notes)。两讲转置卷积各有职责，不删除其中一讲，也不重复写两份相同推导。

本实验由你在本地用Python/PyTorch自行实现，程序、配置和学习记录仅供自己保存与自检；无需Git提交、推送、上交报告或上传本站，也不要求排行榜提交。个人学习与任务进度不作为教程完成条件，不由agent认证或追踪。

[指导页](#/c/d2l-pytorch-2021/lab/cv-dense-prediction?v=guide)只给路线、不变量与局部提示。本地使用Python/PyTorch练习。

## 先分清三层完成状态

| 层级 | 必须留下的证据 | 不能声称什么 |
|---|---|---|
| 合成机制 | 自拟框/标签/张量、形状、梯度、边界检查 | 不能称学会了真实检测或分割 |
| 真实小实验 | 真实banana检测、VOC分割、明确输入图像的风格优化；实际配置与日志 | 不等于全量收敛、论文效果、学生四任务全部完成 |
| 原竞赛执行 | 牛仔行头真实数据、五类映射、离线划分与COCO评估、真实JSON检查 | banana/VOC不能代替牛仔行头；离线结果不等于排行榜成绩 |

GPU/全量训练属于独立硬件扩展，不是第四种可以替代前三层的证明。未做的项目逐项写“未执行”或准确阻塞，不能用一次网站构建通过替代训练。

### 本批主验收实际做到哪里

主agent已在CPU上完成香蕉TinySSD、VOC小FCN和预训练VGG19单图优化的有限运行；样本ID、配置、数值和分层边界统一见[课程公共资料](#/c/d2l-pytorch-2021)，这里不重复日志。

验收只证明所述流程：TinySSD检查图在固定显示阈值下没有预测框；FCN验证预测几乎全背景；风格结果仅为低分辨率短步优化。三项均不宣称达到检测、分割或作品质量标准，也不替代学习者自己的四任务练习。

数据、权重、图像和本地可视化只留运行时cache，未发布。牛仔行头仍未认证/下载/训练，LEC71课堂总结仍未核；GPU和完整教材训练未做。worker来源清单的“未运行”保留自身历史，主agent的独立验收不回填成worker执行。

### 实验账本与获取路径

记录Python/PyTorch/torchvision版本、CPU或实际GPU、dtype、随机种子、线程数、数据哈希、明确样本ID、预处理、初始化、优化器、步数及耗时。先用小batch和`num_workers=0`排接口；不承诺旧d2l Notebook在现代环境原样运行。

- **banana**：教材作者收集、拍摄香蕉并公开提供下载，支持按教材开展本地教学测试；背景图片的任意再分发权不由此推出。正式包约139 MB，教材给SHA1。先核包再读`bananas_train`与`bananas_val`，不把教材合成场景数据误称自然野外竞赛图。
- **VOC2012 trainval**：正式包约2.00 GB，作者公开提供训练/验证；官方Database Rights要求尊重Flickr相应条款。读取`ImageSets/Segmentation`的划分，不把分类/检测全集当成全部带分割标签。个人本地教学与发布原图是不同用途；不把图片上传本站。
- **ResNet-18 / VGG-19**：分别明确`ResNet18_Weights.IMAGENET1K_V1`与`VGG19_Weights.IMAGENET1K_V1`。官方文件约46.8 MB与574.7 MB。代码BSD不等于权重许可；官方提示使用者核实训练数据派生的条款，这不是自动禁止本地学习，也不是任意用途开放授权。保存实际文件完整哈希，文件名8位前缀不是完整校验结果。
- **风格图**：教材`rainier.jpg`明确为作者拍摄；`autumn-oak.jpg`是随例题提供的油画图，所读章未注明画家和独立图片许可。直接用于本地书中示例与发布原图/生成作品的权利分别记录。也可用自己拍摄、自己绘制或明确授权的两张输入图，但注明不是教材原图复现，不用“网上可见”替代授权。

下载只进入自己的运行时cache；不提交压缩包、图片、权重或凭据。页底给正式入口与使用条件；worker只核页面和HEAD，没有下载这些大文件。

## 任务1：让每一个锚框都能追溯到正确预测

**任务id：`cv-dense-prediction-1`**

### 输入与输出合同

输入包含连续坐标的有效框`(N,4)`、目标类别、多个尺度的特征图与预测头。统一采用`(xmin,ymin,xmax,ymax)`；图像宽高为`W,H`时，横坐标除以`W`、纵坐标除以`H`，面积不加1。输出应能追踪“尺度→位置→锚框→类别logits/偏移→匹配目标→解码框→保留检测”。

复用LEC40/41已验几何和P6证据，不重抄整套helper。新增一张多尺度形状账：第i层`(B,C_i,H_i,W_i)`、每位置`a_i`个锚框，类别头通道`a_i(q+1)`、回归头通道`4a_i`；所有层总锚框数为各层`H_iW_ia_i`之和。类别、回归、锚框必须用同一种尺度和位置顺序拼接。

### 可观察验收

1. 用矩形图和非对称框检查坐标转换、IoU、水平翻转；输入必须是`(N,4)`而非裸`(4,)`。矩形特征图的锚框宽含`H/W`修正，不能沿用方图巧合。
2. 匹配覆盖真实目标；教材阈值是`>=`且有强制匹配。padding的`-1`先过滤；空GT单独定义为全部背景，不向仅支持非空GT的helper硬塞空矩阵。
3. 背景0参与分类但不参与框回归。offset编码中的epsilon使往返为近似而非严格恒等。
4. NMS明确阈值边界、类别策略、同分处理。教材helper按类无关方式抑制且IoU等于阈值保留；五类竞赛若改按类NMS，要标为改造。低置信度筛选不等于NMS。
5. 用带唯一标记的预测张量检查flatten/concat的顺序，不能仅因总元素数相同就判通过。

### 三种设计必须能解释

用同一张“远处小帽子、近处大外套”的自拟场景回答：R-CNN先提议区域再识别；Fast R-CNN共享整图特征，Faster R-CNN把提议改为可学习RPN。SSD直接在多尺度特征上预测锚框类别与偏移。课程YOLO主题保留为“整图一次前向联合预测框与类别”的设计对照，不把后来所有YOLO版本都当同一结构，不要求另读论文或复现某获奖模型。

交一张对照表：候选从哪里来、特征是否共享、何处处理大小目标、训练监督怎样对应、推理何处去重。不能把“单阶段”误写成只有一个卷积层。

## 任务2：真实小SSD，以及不能偷换身份的牛仔行头适配

**任务id：`cv-dense-prediction-2`**

### A. 教材banana小训练

保留TinySSD五尺度结构：基础块通道16/32/64，后续三个下采样块128通道，最后全局最大池；每位置4锚框。256×256输入的尺度为32、16、8、4、1，合计5444锚框。单前景类输出`(B,5444,2)`分类logits、`(B,21776)`偏移与`(1,5444,4)`锚框。

读取真实`label.csv`并核`img_name`与类别/框字段，抽取固定训练与验证ID，不交叉混用。教材banana helper将整个目标行除256只因类别恰为0未变；多类数据**只能归一化四个框坐标**，类别保持整数。教材输入是float32的0–255；若改成0–1须同时改变训练和预测并明确记录，不能声称逐像素原样复现。

真实小实验至少包含：加载与本地框叠图检查；训练前固定评估；有限步更新；训练后同批评估；独立验证；解码/NMS后本地可视化。报告分类CE、框损失、正负锚框数，以及验证检测框和对应GT。教材把masked框误差除以所有坐标数，不能改成正样本均值后沿用原名比较。背景占多数时高分类准确率不能证明定位有效。

验收要求损失/梯度有限、选定参数实际变化、验证不改变参数/BN状态/既有梯度、样本身份和显示坐标一致。记录初末loss及真实检出数量；若短预算尚未产生可用框，就报告失败或未收敛，不挑一张图冒称成功。完整20轮与更大训练是扩展，不捏造曲线。

### B. 牛仔行头原任务与离线验证

[LEC50](#/c/d2l-pytorch-2021/lec/lec50?v=notes)对应**CowBoy Outfits Detection**，Kaggle路径`cowboyoutfits`，host为Joshua Z. Zhang。官方公告结束链接与Kaggle Evaluation都指向CodaLab竞赛33573；这是同一历史任务的材料平台与评测平台，不是两个可以任选的竞赛。

| 类名 | 原始category_id |
|---|---:|
| belt | 87 |
| sunglasses | 1034 |
| boot | 131 |
| cowboy_hat | 318 |
| jacket | 588 |

公开Data说明：`images`与`train.json`用于训练；`valid.csv`、`test.csv`分别服务开发/最终阶段；总4882文件、1.47 GB。官方starter用COCO接口加载`train.json`，历史输出为3062张训练图。**列名有冲突**：Data文字称`image_id,file_name`，starter Version1却读取`id,file_name`；取得真实CSV后必须显式确认，不能静默猜列。训练类索引可以连续化，但保存双向映射，导出还原原始category_id。按图片ID而非标注行划分，近重复/同来源组能识别时也隔离。大整数ID不得经JavaScript不安全整数或浮点中转而丢精度。

评测为COCO式AP@0.50:0.95，不是分类准确率、单一IoU@0.5或框坐标MAE。离线应从有标注训练图片固定划出验证，使用匹配该协议的评估器，报告每类样本数、AP及空检测/重复检测处理。`valid.csv`并不承诺含公开真值，不能拿其无标签图片自行编造离线分数。

提交格式为JSON检测记录列表，每条含`image_id,category_id,bbox,score`；score有限且在0–1。**框约定必须分层**：官方starter Version1实际导出原图像素`[xmin,ymin,xmax,ymax]`；COCO接口常用的`[x,y,width,height]`不能不经转换直接替代。公开Evaluation只写“四个浮点数”，尚未读到实际CodaLab scorer，不能声称该差异已被评分端确认。离线评估器入口、内部规范与历史提交适配分别做转换测试，拿到真实标注/评分器再固化最终端点。检测列表允许一图多行；完整测试身份另有处理账，即使某图无检测也可解释。

**当前访问边界**：CodaLab公开Terms明确本比赛用于教育，须遵循非商业许可，不将数据为其他目的再分发；因此不能笼统写“未见任何使用条件”。Kaggle匿名Data可读说明，但文件预览明确要求登录并接受竞赛规则；Rules只显示通用模板。未登录、未接受、未下载，故认证后下载条件、实际文件及图片逐项权利仍未核。教育用途条款支持按其条件开展本地学习，不等于替用户完成认证或任意再分发许可。不绕登录，不找第三方拷贝假冒授权。

历史说明明确Kaggle提交会失败，实际评测在CodaLab；截止2021-08-07 04:00 UTC。今天看到Late Submission按钮不证明现在仍可提交。本任务以合法数据上的离线训练、评估和格式核验为目标，无需向排行榜提交。保留[LEC71后续总结](#/c/d2l-pytorch-2021/lec/lec71?v=notes)的阅读关联，但课堂内容未核，不能编获奖方案或教师建议。

## 任务3：像素标签、转置卷积与真实小FCN

**任务id：`cv-dense-prediction-3`**

输入RGB图`(B,3,H,W)`与整型标签`(B,H,W)`；VOC共有背景加20个对象类，输出logits`(B,21,H,W)`。掩码必须保持类别索引，不标准化、不做双线性插值；图像与标签共享裁剪/翻转参数。评估改为确定裁剪或明确的全图策略并保留尾批，不能照抄教材验证随机裁剪和drop_last后称为稳定完整验证。

VOC的void/边界像素不是背景。优先保留PNG调色板索引，255按ignore处理；若走RGB映射，未知颜色不能静默落到0。教材全0查表会产生这个问题，本实验显式修正。损失用有效像素总和除有效像素数；全void样本/批次须有明确跳过规则，不能0除或以背景填充。

先完成两个不同机制检查：LEC46的单点散布、重叠相加与形状；LEC47的线性算子伴随内积关系。转置卷积不是逆卷积，恢复尺寸不等于恢复信息。随后采用教材ResNet-18去掉pool/fc，接512→21的1×1卷积，再接核64/步幅32/padding16的转置卷积。记录是否真实加载V1权重；随机骨干只作独立从零基线，不叫预训练FCN。

真实小基线使用VOC明确train/val ID子集，给定可被32整除的裁剪尺寸、固定预算和BN策略。报告有效像素CE、混淆矩阵、像素准确率与每类IoU/mIoU；没有并集的类别标不适用并说明平均范围，不把缺类伪记为100%。前后本地查看原图、GT、预测三联图；全背景预测必须通过每类统计暴露，不能仅报高像素准确率。

验收：尺寸/标签对齐、ignore梯度为0、真实参数更新、确定验证状态不变；给实际初末训练与验证数值，不设虚构官方达标分数。小样本不代表完整VOC效果。

## 任务4：只优化一张图像，不训练一个分类器

**任务id：`cv-dense-prediction-4`**

选择一张内容图和一张风格图，记录原始尺寸、用途依据、文件哈希与预处理。使用明确VGG-19 V1权重，固定特征网络为eval且参数不求导；只将合成图像交给优化器。内容/风格目标预先提取并detach，合成图像分支仍需梯度，不能把整个VGG前向包进`no_grad`。

对单图特征`(1,C,H,W)`展平为`F∈R^{C×HW}`，采用教材归一化Gram：

$$
G(F)=\frac{FF^\top}{CHW}.
$$

内容损失比较特征位置，风格损失比较Gram，TV惩罚相邻像素差。记录选层、每层归一化、各权重和实际总目标；教材风格层0/5/10/19/28、内容层25。固定源码`10 * styles_l`是列表重复，实际风格项额外乘10；若用标准显式加权和，标为编者清晰化约定并同步日志，不能照抄图例误报总损失。

真实运行记录初始/中间/最终的各项loss、总loss、图像变化与冻结参数不变；本地展示内容/风格/输出，记录步数和实际分辨率。恒等Gram、空间列置换不变和梯度机制只能证明实现性质，不能冒充真实预训练风格优化。显示时反标准化并裁到0–1，不要把clamp后图像反复detach成新优化变量。

只做一个受控对照，例如改变风格权重但保持初始化、层、分辨率和步数；说明变化而不要求每项损失都同时下降。GPU、高分辨率和500步教材预算另列扩展，不外推短CPU优化的视觉效果或速度。

## 本地记录与自检

保持四个任务id；在本地保存自己的实现与简短记录：形状账、几何复用证据、真实数据/权重账、训练配置与失败记录、离线指标、身份映射、授权允许的本地可视化说明和未执行清单。不得提交完整参考答案、第三方原图、权重或账户资料。

<details>
<summary>自检：banana能检出框、VOC能输出21通道，就完成竞赛了吗？</summary>

没有。前者是独立检测训练，后者甚至可能仅证明形状。牛仔行头仍需要它自己的数据访问、五类映射、真实离线评估与导出；类别、标注、评测和权利边界都不能由其他数据替代。

</details>

## 来源、许可与执行边界

- 固定教材[13.5多尺度](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computer-vision/multiscale-object-detection.md)、[13.6数据](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computer-vision/object-detection-dataset.md)、[13.7 SSD](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computer-vision/ssd.md)、[13.8 R-CNN](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computer-vision/rcnn.md)、[13.9分割](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computer-vision/semantic-segmentation-and-dataset.md)、[13.10转置卷积](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computer-vision/transposed-conv.md)、[13.11 FCN](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computer-vision/fcn.md)、[13.12风格迁移](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_computer-vision/neural-style.md)。正文与PyTorch节选范围存manifest；不冒称全分支或课堂已读。13.3/13.4复用LEC40/41与P6验收。
- [banana正式下载](https://d2l-data.s3-accelerate.amazonaws.com/banana-detection.zip)、[VOC教材镜像](https://d2l-data.s3-accelerate.amazonaws.com/VOCtrainval_11-May-2012.tar)、[VOC官方数据/Database Rights](https://www.robots.ox.ac.uk/~vgg/projects/pascal/VOC/voc2012/index.html)。教材SHA1及HEAD长度存来源目录，不把校验和当图片许可。
- [模型权重使用提醒](https://docs.pytorch.org/vision/0.20/models.html)、[ResNet18官方权重](https://download.pytorch.org/models/resnet18-f37072fd.pth)、[VGG19官方权重](https://download.pytorch.org/models/vgg19-dcbb9e9d.pth)。教材图像固定路径：[rainier](https://raw.githubusercontent.com/d2l-ai/d2l-zh/e6b18ccea71451a55fcd861d7b96fddf2587b09a/img/rainier.jpg)、[autumn-oak](https://raw.githubusercontent.com/d2l-ai/d2l-zh/e6b18ccea71451a55fcd861d7b96fddf2587b09a/img/autumn-oak.jpg)。只核HEAD与书文说明，未在worker下载图像或权重。
- [课程公告](https://courses.d2l.ai/zh-v2/announcements.html)、[Kaggle原任务](https://www.kaggle.com/competitions/cowboyoutfits/overview)、[数据页](https://www.kaggle.com/competitions/cowboyoutfits/data)、[规则页](https://www.kaggle.com/competitions/cowboyoutfits/rules)、[官方starter Version1](https://www.kaggle.com/code/zhreshold/cowboy-outfits-starter-kit)、[CodaLab33573](https://competitions.codalab.org/competitions/33573)。2026-11-14匿名实读，未登录/接受规则/提交。starter页面Apache-2.0仅证明Notebook代码条款，不替代输入数据权利；其历史日志不是本次执行。网页标签“Categorization Accuracy”不替代Evaluation正文的检测AP协议。

本页是编者任务合同，不是学生已完成报告。worker未跑训练、数值、build或页面验收；本批主agent的独立实测和精确未执行范围见[课程公共资料](#/c/d2l-pytorch-2021)。
