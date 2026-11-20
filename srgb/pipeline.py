"""sRGB 纹理转换管线（初始桩实现）。

统一契约：
- 颜色统一为 ``(r, g, b)`` 三元组，线性光通道范围 0..1。
- sRGB 编解码使用 IEC 61966-2-1 分段函数，禁止用 2.2 幂近似。
- 所有浮点结果按 1e-6 容差验收。
"""


class ColorPipelineError(ValueError):
    """颜色管线中的格式、位深或像素数据错误。"""


def srgb_to_linear(c: float) -> float:
    """将单个 sRGB 编码通道转换为线性光通道。

    参数:
        c: sRGB 编码值，范围 0..1。

    返回:
        线性光值，范围 0..1。

    契约:
        - 使用 sRGB 分段函数，阈值 0.04045（含）：
          ``c <= 0.04045`` 时返回 ``c / 12.92``；否则返回
          ``((c + 0.055) / 1.055) ** 2.4``。
        - 不得使用 ``c ** 2.2`` 之类的纯幂近似。
        - 输入按 0..1 处理，结果精度容差 1e-6。
    """
    raise NotImplementedError


def linear_to_srgb(c: float) -> float:
    """将单个线性光通道编码为 sRGB 通道。

    参数:
        c: 线性光值，范围 0..1。

    返回:
        sRGB 编码值，范围 0..1。

    契约:
        - 使用反向分段函数，线性光阈值 0.0031308（含）：
          ``c <= 0.0031308`` 时返回 ``12.92 * c``；否则返回
          ``1.055 * c ** (1 / 2.4) - 0.055``。
        - 不得复用正向的 0.04045 阈值，否则区段边界会出现跳变。
        - 结果精度容差 1e-6。
    """
    raise NotImplementedError


def decode_texture(pixels, format: str) -> list:
    """把纹理像素解码为线性 RGB 三元组列表。

    参数:
        pixels: 像素三元组序列。``srgb8`` 与 ``linear8`` 的通道是
            0..255 的整数，``float`` 的通道是 0..1 的线性浮点数。
        format: 仅支持 ``"srgb8"``、``"linear8"``、``"float"``。

    返回:
        ``list[tuple[float, float, float]]``，每个通道为 0..1 的线性光值。

    契约:
        - ``srgb8`` 必须先除以 255 再走 sRGB 分段解码。
        - ``linear8`` 除以 255；``float`` 直接作为线性值使用。
        - 未知格式必须抛 ``ColorPipelineError``，不得静默按 linear 处理。
        - 数值精度容差 1e-6。
    """
    raise NotImplementedError


def encode_target(pixels, format: str) -> list:
    """把线性 RGB 三元组编码为目标纹理格式。

    参数:
        pixels: 线性 RGB 三元组序列，通道范围 0..1。
        format: 仅支持 ``"srgb8"``、``"linear8"``、``"float"``。

    返回:
        ``list[tuple]``。8 bit 格式的通道是 0..255 的整数；``float``
        格式的通道是线性浮点数。

    契约:
        - 8 bit 编码先钳制到 0..1；``srgb8`` 先做线性到 sRGB 的分段编码，
          ``linear8`` 直接使用线性值。
        - 乘以 255 后四舍五入，并再次钳制到 0..255；1.0 只能编码成 255，
          绝不能出现 256。
        - 未知格式必须抛 ``ColorPipelineError``。
        - 数值精度容差 1e-6。
    """
    raise NotImplementedError


def blend_linear(a, b, t: float) -> list:
    """在线性光空间逐通道插值两个 RGB 三元组。

    参数:
        a: 起点线性 RGB 三元组，通道范围 0..1。
        b: 终点线性 RGB 三元组，通道范围 0..1。
        t: 混合系数。

    返回:
        ``(1 - t) * a + t * b`` 的线性 RGB 三元组。

    契约:
        - ``t`` 使用前必须钳制到 [0, 1]：小于 0 取 0，大于 1 取 1，
          不得外推出负值或超过终点的值。
        - 混合必须发生在线性光空间，不得在 sRGB 编码空间直接插值。
        - 数值精度容差 1e-6。
    """
    raise NotImplementedError


def premultiply(pixels, alpha) -> list:
    """对 straight-alpha 像素执行预乘 alpha。

    参数:
        pixels: straight-alpha 的 RGB 三元组序列，通道范围 0..1。
        alpha: 单个 alpha 标量，或与 ``pixels`` 等长的逐像素 alpha 序列；
            每个 alpha 的范围为 0..1。

    返回:
        ``(r * a, g * a, b * a)`` 形式的 premultiplied RGB 三元组列表。

    契约:
        - 输入按 straight alpha 解释，输出为 premultiplied alpha。
        - 每个像素只能乘一次自己的 alpha，不得把 straight 与
          premultiplied 两种表示混用，也不得对 alpha=1 的像素做额外缩放。
        - alpha 长度不符或越界时抛 ``ColorPipelineError``。
        - 数值精度容差 1e-6。
    """
    raise NotImplementedError


def validate_format(format: str) -> list[str]:
    """检查纹理格式名并返回问题列表。

    参数:
        format: 待检查的格式名。

    返回:
        问题描述字符串列表；空列表表示格式合法。

    契约:
        - 合法格式只有 ``"srgb8"``、``"linear8"`` 和 ``"float"``。
        - 未知格式必须返回非空列表，问题文本包含 ``unknown format``。
        - ``srgb``/``linear`` 的位深不是 8，或位深写法非法时，问题文本
          包含 ``bit depth``；不得静默放行。
        - 该函数返回问题而不抛异常；数值容差 1e-6。
    """
    raise NotImplementedError


def convert_batch(images, src_format: str, dst_format: str) -> dict:
    """批量转换纹理并保证整批原子性。

    参数:
        images: 图像列表，每个图像是像素三元组列表。
        src_format: 源格式，取值同 ``decode_texture``。
        dst_format: 目标格式，取值同 ``encode_target``。

    返回:
        ``{"format": dst_format, "images": [...]}``，其中 ``images`` 的
        顺序、长度与输入一致，每个图像都是独立的新像素缓冲。

    契约:
        - 先校验格式和全部图像，再统一产出结果；任一图像非法时必须抛
          ``ColorPipelineError``，不得返回部分结果，也不得改动输入。
        - 输出图像及其像素不得与输入或其他图像共享可变缓冲。
        - 每张图独立解码、编码；数值精度容差 1e-6。
    """
    raise NotImplementedError
