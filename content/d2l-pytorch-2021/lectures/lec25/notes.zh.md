---
source: "《动手学深度学习》中文第二版7.2，固定提交e6b18ccea71451a55fcd861d7b96fddf2587b09a，非2021快照。"
video: "https://www.bilibili.com/video/BV1Ao4y117Pd"
license: "教材仓库Apache-2.0不外推视频；视频copyright=1/no_reprint=1。算例与SVG为编者自拟。"
status: "教材导读；主agent已完成完整教材结构的CPU前向与参数量核验，未训练VGG。3P字幕空列表，课堂未核实。"
title: "VGG：重复块、感受野与成本"
lectureId: lec25
kind: "教材导读 / 编者笔记"
videoContentVerified: false
textbookCommit: e6b18ccea71451a55fcd861d7b96fddf2587b09a
codeExecution: "2026-11-14主agent统一CPU前向验收通过；224输入、完整通道与分类头，非缩版，见sources/p4-shared/。"
---

# VGG：重复块、感受野与成本

## 1. 从散列层清单到可重复块

[LEC24的AlexNet](#/c/d2l-pytorch-2021/lec/lec24?v=notes)用了不同核大小和步幅。VGG把设计收敛到一个模板：**若干次3×3、stride1、padding1的卷积＋ReLU，然后一次2×2、stride2最大池化**。

块内卷积保持高宽，块末池化缩小高宽。通道数、卷积次数是块配置，不是池化“自动增加”的。本页采用教材的单通道、10类VGG-11变体，不冒充原RGB、1000类模型。

| 块 | 卷积次数 | 通道路径 | 输入→池化后空间 | 池化后理论感受野 |
|---|---:|---|---|---:|
| 1 | 1 | 1→64 | 224→112 | 4 |
| 2 | 1 | 64→128 | 112→56 | 10 |
| 3 | 2 | 128→256→256 | 56→28 | 30 |
| 4 | 2 | 256→512→512 | 28→14 | 70 |
| 5 | 2 | 512→512→512 | 14→7 | 150 |

配置为`((1,64),(1,128),(2,256),(2,512),(2,512))`，共有$1+1+2+2+2=8$层卷积，再加3个全连接层，所以是VGG-11。五个块不是五层网络；遍历顶层模块看到五个块，也不代表只有五次卷积。

最后输出$(N,512,7,7)$，Flatten后25088维，分类头为25088→4096→4096→10；两个隐藏全连接均接ReLU与Dropout(0.5)。

![两层小卷积叠加后的理论感受野](assets/vgg-blocks.svg)

图为编者自绘；中心虚线框表示单层范围，外框表示两层叠加后的范围。感受野描述可能依赖区域，不是每个像素的实际贡献权重。

## 2. 感受野公式：别把核大小当成整网覆盖范围

记$r$为某层一个位置在原输入上可能覆盖的边长，$j$为相邻两个输出位置映射回原输入的间距。初始$r_0=j_0=1$。对于核$k$、步幅$s$、dilation1的一层：

$$
\begin{aligned}
r_{\mathrm{new}}&=r_{\mathrm{old}}+(k-1)j_{\mathrm{old}},\\
j_{\mathrm{new}}&=s\,j_{\mathrm{old}}.
\end{aligned}
$$

第一块：3×3卷积使$r:1\to3$，池化使$r:3\to4$、$j:1\to2$。第二块：卷积$r:4\to8$，池化$r:8\to10$、$j:2\to4$。后面块内的每个3×3卷积，都要按**当前的$j$**扩大感受野，不能始终只加2。

第五块池化后$r=150,j=32$，因此一个7×7特征图位置有150×150的理论输入范围。边界位置的部分范围落在padding上；最大池化、ReLU及具体权重会使实际影响更小或不均匀。这不是“网络真的平等使用了这150×150所有像素”。分类头读取全部7×7位置，覆盖关系也不同于单个位置。

## 3. 小核堆叠为何有用，又不是什么等价替换

在输入、隐藏、输出通道都为$C$、stride1、忽略偏置时：

$$
\begin{aligned}
P_{\text{两个3×3}}&=2\times9C^2=18C^2,\\
P_{\text{一个5×5}}&=25C^2.
\end{aligned}
$$

两个3×3层具有5×5理论感受野，参数更少，还能在中间加入一次非线性。例如$C=64$，两小核为73,728权重，一大核为102,400。但这**不是任意通道配置下都省参数**的证明：中间通道变宽会改账；两层还要保存中间激活、调用更多算子。

即使去掉非线性，边界处理也要核对，不能不加条件就宣称与一个大卷积逐点等价。加入ReLU后更不是同一个线性算子。感受野相同不等于函数相同，不等于训练难度或实测速度相同。

## 4. 独立结构前向：模板复用不等于共享权重

代码保留完整教材VGG-11通道、224输入、8个卷积和3个全连接。仅做批量1前向；**参数float32本身约491.4 MiB**，另需运行时内存。若机器不够，应如实记录未运行完整配置，而不是静默删层。

```python
import torch
from torch import nn

def vgg_block(count, in_channels, out_channels):
    layers = []
    for _ in range(count):
        layers += [nn.Conv2d(in_channels, out_channels, 3, padding=1),
                   nn.ReLU()]
        in_channels = out_channels
    layers.append(nn.MaxPool2d(2, stride=2))
    return nn.Sequential(*layers)

torch.manual_seed(25)
arch = ((1, 64), (1, 128), (2, 256), (2, 512), (2, 512))
blocks = []
in_channels = 1
for count, out_channels in arch:
    blocks.append(vgg_block(count, in_channels, out_channels))
    in_channels = out_channels
net = nn.Sequential(
    *blocks, nn.Flatten(),
    nn.Linear(512 * 7 * 7, 4096), nn.ReLU(), nn.Dropout(0.5),
    nn.Linear(4096, 4096), nn.ReLU(), nn.Dropout(0.5),
    nn.Linear(4096, 10),
)
net.eval()
x = torch.zeros(1, 1, 224, 224)
with torch.no_grad():
    # 顶层先输出五个块的结果；每个块内部还有多个卷积/ReLU。
    for layer in net:
        x = layer(x)
        print(type(layer).__name__, tuple(x.shape))
assert x.shape == (1, 10)
assert torch.isfinite(x).all()
print(sum(p.numel() for p in net.parameters()))  # 解析预期：128806154
```

`vgg_block`循环中更新`in_channels`很关键：同块第二卷积接收的是该块的输出通道数，不是块最初的输入通道数。每次创建新的`Conv2d`对象，所以这里只共享结构模板，不共享参数；参数复用含义见[LEC16](#/c/d2l-pytorch-2021/lec/lec16?v=notes)。

## 5. VGG的整洁代码为什么仍然昂贵

参数总计128,806,154，其中卷积部分9,219,328，分类头119,586,826；首个Linear就有102,764,544个参数。即使大量卷积都只有3×3，大分类头仍然占存储大头。

另一方面，高分辨率位置反复使用卷积权重，计算会很重。例如第三块第二卷积仍在56×56上执行：

$$
\begin{aligned}
\mathrm{MACs}&=56^2\times256^2\times9\\
&=1849688064.
\end{aligned}
$$

这是单样本单层约18.5亿MAC，不是整网耗时。卷积后的激活还要用于反向，空间尺寸、批量和通道都会影响内存。模板能减少代码重复，**不能减少这份运算账**。

教材训练示例把每块通道除以4，即16、32、64、128、128，但仍保留相同卷积次数和4096维分类头。这是教材明示的窄通道变体，不是完整宽度VGG-11实测。中间卷积输入输出通道同时缩为1/4时，权重与MAC约缩为1/16；第一层输入仍为1、分类头部分保持4096，因此不能说整网全部成本都恰好缩为1/16。

若把输入224改96，五次池化得到48→24→12→6→3，Flatten变成$512\times3\times3$，原先的25088输入Linear就不匹配。加自适应池化可改变接口合同，但那是明确的结构改型，不是原代码自动支持所有分辨率。实验缩小配置需逐项标明输入、通道、分类头与保留的块数。

## 6. 自测

1. VGG-11为什么不是5层，也不是11层卷积？
2. 第三块第二卷积的输入通道是多少？
3. 两个3×3核的感受野是6×6吗？
4. 为什么相同的块函数不会让五个块自动共享权重？
5. 最后一块感受野150，是否代表所有位置都依赖150×150个真实输入像素？

<details>
<summary>展开答案</summary>

1. 名称数的是8卷积＋3全连接有参数层；五块各自含1、1、2、2、2个卷积。
2. 256，因为该块第一个卷积已把128通道变成256。
3. stride1、dilation1时是5×5；第一层3，第二层在其基础上每侧再扩一格。
4. 每次函数调用/循环都创建新模块对象，权重独立；复用同一模块实例才会引入参数共享。
5. 不是。150是理论范围；边界含padding，非线性、最大值选择与权重会改变实际影响。

</details>

## 来源、分P清单与缺口

实际阅读D2L作者团队[固定教材7.2](https://github.com/d2l-ai/d2l-zh/blob/e6b18ccea71451a55fcd861d7b96fddf2587b09a/chapter_convolutional-modern/vgg.md)全文、习题与PyTorch代码：块构造、VGG-11配置、完整前向、ratio4窄通道训练变体。版本为当前中文第二版固定源码，不是2021快照。感受野递推、成本与接口排错为编者补充；未额外审读VGG论文，不新增论文必读，不转载第三方图。

2026-11-14按[官网课表](https://courses.d2l.ai/zh-v2/)核对[官方BV](https://www.bilibili.com/video/BV1Ao4y117Pd)：作者“跟李沐学AI”（mid 1567748478），标题“25 使用块的网络 VGG【动手学深度学习v2】”，发布于2021-05-23 11:20:18 UTC。

| 分P | 接口标题 | 时长 |
|---|---|---:|
| P1 | VGG | 09:04 |
| P2 | 代码 | 07:23 |
| P3 | QA | 04:16 |

合计20:43。此表不是课堂时间线。3P各请求一次公开player，均成功空字幕；未观看/下载音视频，未核实课堂演示或QA。无完整课堂源，`draft`阻塞，不建占位；`materials=not_required`。

来源、SHA-256、前向与数值验收目标见`sources/p4-lec25/manifest-fragment.json`。教材根LICENSE为Apache-2.0，不外推视频或第三方图；视频copyright=1/no_reprint=1，未取得开放转录授权。代码未由撰写者运行，未执行完整训练。
