use image::{DynamicImage, Rgba, RgbaImage};
use imageproc::geometric_transformations::{Interpolation, rotate_about_center};

use super::utils::{
    adjust_brightness, apply_rounded_corners, cover, dominant_color, draw_titles_wrapped,
    optimized_blur, overlay_with_shadow, tint,
};
use super::{Fonts, Result};
use crate::library_poster::RenderConfig;

/// 生成右侧三层旋转卡片、左侧标题的卡片风格。
pub fn render(
    images: &[DynamicImage],
    title: &str,
    subtitle: &str,
    fonts: &Fonts,
    config: &RenderConfig,
    dimensions: (u32, u32),
) -> Result<RgbaImage> {
    let source = images.first().ok_or(super::Error::MissingImage)?;
    let (width, height) = dimensions;
    let theme = dominant_color(source);
    let mut canvas = cover(source, width, height);
    canvas = optimized_blur(
        &canvas,
        config.blur_radius.max(0.0) * height as f32 / 1080.0,
    );
    tint(
        &mut canvas,
        adjust_brightness(theme, 0.82),
        config.color_strength.clamp(0.0, 1.0),
    );

    let card_size = (height as f32 * 0.70) as u32;
    let mut main_card = cover(source, card_size, card_size);
    apply_rounded_corners(&mut main_card, card_size / 8);

    let mut middle_card = optimized_blur(&main_card, height as f32 * 0.008);
    tint(&mut middle_card, adjust_brightness(theme, 1.24), 0.52);
    let mut back_card = optimized_blur(&main_card, height as f32 * 0.015);
    tint(&mut back_card, adjust_brightness(theme, 0.72), 0.64);

    let center_x = width as f32 * 0.73;
    let center_y = height as f32 * 0.50;
    let layers = [
        (back_card, 34.0_f32, 18_i64, 24_i64, 18.0_f32, 100_u8),
        (middle_card, 17.0_f32, 15_i64, 20_i64, 15.0_f32, 126_u8),
        (main_card, 0.0_f32, 12_i64, 18_i64, 13.0_f32, 150_u8),
    ];
    for (card, angle, shadow_x, shadow_y, shadow_blur, shadow_opacity) in layers {
        let rotated = rotate_about_center(
            &card,
            angle.to_radians(),
            Interpolation::Bicubic,
            Rgba([0, 0, 0, 0]),
        );
        overlay_with_shadow(
            &mut canvas,
            &rotated,
            (center_x - rotated.width() as f32 / 2.0) as i64,
            (center_y - rotated.height() as f32 / 2.0) as i64,
            shadow_x,
            shadow_y,
            shadow_blur * height as f32 / 1080.0,
            shadow_opacity,
        );
    }

    draw_titles_wrapped(
        &mut canvas,
        title,
        subtitle,
        fonts,
        (width as f32 * 0.25) as i32,
        (height as f32 * 0.37) as i32,
        height as f32 * 0.14,
        height as f32 * 0.055,
        Rgba([255, 255, 255, 235]),
        (width as f32 * 0.40) as i32,
    );
    Ok(canvas)
}
