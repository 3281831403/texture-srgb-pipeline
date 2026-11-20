# texture-srgb-pipeline

## 题面

渲染管线切到线性空间后，暗部发灰、半透明边缘还发黑：sRGB 转换使用 2.2 幂近似，暗部偏差 3%；分段阈值写成 0.04，线性段少 0.5%；反变换沿用同一套分段，亮部出现跳变；srgb8 解码后不除以 255，颜色全部超出 1；目标编码量化采用 round 半上，出现 256；混合直接在 sRGB 空间做，边缘发灰；预乘与 straight 混用，半透明边缘发黑；未知格式被静默当作 linear；批量转换共用像素缓冲，图与图之间串色；t 不钳制，外推出现负值。srgb/pipeline.py 是核心，tests/test_pipeline.py 15个红。要修的是：按 sRGB 分段曲线实现正反变换，正确解码并按 0..255 量化，在线性空间混合，规范预乘 alpha，显式校验格式，并让批量转换在任一图片非法时整体回滚。

## 运行方式

在仓库根目录执行：

```powershell
cd /d D:\gsb-20261119\texture-srgb-pipeline
python -m pytest tests -q
```

初始状态下汇总必须恰好是 `15 failed`，不能出现 collection error、import error 或 syntax error；末行通常形如 `15 failed in <time>s`。全部测试通过时才是 `15 passed`。

## 字段表

| 字段 | 取值 |
| --- | --- |
| 所属领域 | 游戏、图形与多媒体 |
| 子方向 | 图形渲染 |
| 任务类型 | Bugfix |
| 语言/框架 | Python 3, pytest |
| 环境可复现等级 | 无外部依赖 |

## 边界

`tests/test_pipeline.py` 不可修改，只修复 `srgb/pipeline.py`。实现仅使用 Python 标准库（`math`）与 pytest，离线运行，不使用随机数。颜色统一表示为 `(r, g, b)` 三元组，线性光通道范围为 0..1，数值比较容差为 1e-6。
