"""texture-srgb-pipeline 的 15 条验收测试。"""

import pytest

from srgb.pipeline import (
    ColorPipelineError,
    blend_linear,
    convert_batch,
    decode_texture,
    encode_target,
    linear_to_srgb,
    premultiply,
    srgb_to_linear,
    validate_format,
)


# 缺陷 1：用 2.2 幂近似代替 sRGB 分段函数。
def test_srgb_to_linear_uses_piecewise_curve_not_2_2_power():
    assert srgb_to_linear(0.02) == pytest.approx(
        0.0015479876160990713, abs=1e-6
    )
    assert srgb_to_linear(0.5) == pytest.approx(
        0.21404114048223255, abs=1e-6
    )


# 缺陷 2：阈值写成 0.04，0.04..0.04045 的线性段被误走非线性分支。
def test_srgb_to_linear_threshold_is_0_04045():
    assert srgb_to_linear(0.0404) == pytest.approx(
        0.0404 / 12.92, rel=1e-6, abs=1e-12
    )
    assert srgb_to_linear(0.04045) == pytest.approx(
        0.04045 / 12.92, abs=1e-6
    )


# 缺陷 3：反变换复用正向阈值，亮部/边界跳变。
def test_linear_to_srgb_uses_inverse_piecewise_curve():
    assert linear_to_srgb(0.003) == pytest.approx(0.03876, abs=1e-6)
    assert linear_to_srgb(0.04) == pytest.approx(
        0.22091636254849623, abs=1e-6
    )
    assert linear_to_srgb(0.5) == pytest.approx(
        0.7353569830524495, abs=1e-6
    )
    assert linear_to_srgb(0.9) == pytest.approx(
        0.9546871718858662, abs=1e-6
    )


# 缺陷 4：srgb8 解码不除以 255。
def test_srgb8_decode_divides_by_255_then_decodes():
    decoded = decode_texture([(255, 128, 0)], "srgb8")

    assert len(decoded) == 1
    assert decoded[0] == pytest.approx(
        (1.0, 0.21586050011389926, 0.0), abs=1e-6
    )


# 缺陷 5：8 bit 量化出现 256。
def test_encode_srgb8_stays_in_0_255_and_never_emits_256():
    encoded = encode_target(
        [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (0.5, 0.5, 0.5)],
        "srgb8",
    )

    assert encoded == [(0, 0, 0), (255, 255, 255), (188, 188, 188)]
    assert all(
        isinstance(channel, int) and 0 <= channel <= 255
        for pixel in encoded
        for channel in pixel
    )


# 缺陷 6：在 sRGB 空间而不是线性空间混合。
def test_blend_linear_interpolates_in_linear_space():
    midpoint = blend_linear((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), 0.5)
    quarter = blend_linear((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.25)

    assert midpoint == pytest.approx((0.5, 0.5, 0.5), abs=1e-6)
    assert quarter == pytest.approx((0.75, 0.0, 0.25), abs=1e-6)


# 缺陷 7：预乘与 straight 混用。
def test_premultiply_applies_each_alpha_exactly_once():
    pixels = [(1.0, 0.5, 0.25), (0.2, 0.4, 0.8), (0.5, 0.5, 0.5)]
    alpha = [0.5, 1.0, 0.0]

    result = premultiply(pixels, alpha)
    expected = [(0.5, 0.25, 0.125), (0.2, 0.4, 0.8), (0.0, 0.0, 0.0)]

    assert len(result) == len(expected)
    for actual, wanted in zip(result, expected):
        assert actual == pytest.approx(wanted, abs=1e-6)


# 缺陷 8：未知格式被静默当成 linear。
def test_validate_format_reports_unknown_and_bad_depth():
    assert validate_format("srgb8") == []
    assert validate_format("linear8") == []
    assert validate_format("float") == []

    unknown = validate_format("rec709")
    assert unknown
    assert any("unknown" in issue.lower() for issue in unknown)

    bad_depth = validate_format("srgb16")
    assert bad_depth
    assert any("bit depth" in issue.lower() for issue in bad_depth)


# 缺陷 9：批量转换共用像素缓冲，图与图之间串色。
def test_convert_batch_keeps_output_images_independent():
    images = [[(255, 0, 0)], [(0, 255, 0)]]

    result = convert_batch(images, "srgb8", "linear8")
    converted = result["images"]

    assert converted == [[(255, 0, 0)], [(0, 255, 0)]]
    assert converted[0] is not converted[1]
    converted[0][0] = (0, 0, 0)
    assert converted[1] == [(0, 255, 0)]
    assert images[0] == [(255, 0, 0)]


# 缺陷 10：t 不钳制，外推出负值。
def test_blend_linear_clamps_t_to_unit_interval():
    a = (0.2, 0.4, 0.6)
    b = (0.8, 0.9, 1.0)

    assert blend_linear(a, b, -0.5) == pytest.approx(a, abs=1e-6)
    assert blend_linear(a, b, 1.5) == pytest.approx(b, abs=1e-6)


# 组合 1：0 与 1 的往返不变。
def test_zero_and_one_round_trip_within_tolerance():
    for value in (0.0, 1.0):
        assert linear_to_srgb(srgb_to_linear(value)) == pytest.approx(
            value, abs=1e-6
        )
        assert srgb_to_linear(linear_to_srgb(value)) == pytest.approx(
            value, abs=1e-6
        )


# 组合 2：t=0 返回 a。
def test_blend_linear_t_zero_returns_a():
    a = (0.1, 0.2, 0.3)
    b = (0.9, 0.8, 0.7)

    assert blend_linear(a, b, 0.0) == pytest.approx(a, abs=1e-6)


# 组合 3：t=1 返回 b。
def test_blend_linear_t_one_returns_b():
    a = (0.1, 0.2, 0.3)
    b = (0.9, 0.8, 0.7)

    assert blend_linear(a, b, 1.0) == pytest.approx(b, abs=1e-6)


# 组合 4：未知格式抛出 ColorPipelineError。
def test_unknown_format_raises_color_pipeline_error():
    with pytest.raises(ColorPipelineError):
        decode_texture([(0, 0, 0)], "rec709")


# 组合 5：批量全部成功时顺序不变。
def test_convert_batch_preserves_order_when_all_succeed():
    images = [
        [(255, 0, 0)],
        [(0, 255, 0)],
        [(0, 0, 255)],
    ]

    result = convert_batch(images, "srgb8", "linear8")

    assert result["format"] == "linear8"
    assert result["images"] == [
        [(255, 0, 0)],
        [(0, 255, 0)],
        [(0, 0, 255)],
    ]
