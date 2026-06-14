use image::imageops::blur;
use image::{DynamicImage, Rgba};

use super::utils::{
    apply_rounded_corners, cover, dominant_color, draw_titles, paste_centered, tint,
};
use super::{Fonts, Result};
use crate::library_poster::RenderConfig;

/// 生成右侧悬浮圆角主图、左侧标题的卡片风格。
pub fn render(
    images: &[DynamicImage],
    title: &str,
    subtitle: &str,
    fonts: &Fonts,
    config: &RenderConfig,
    dimensions: (u32, u32),
) -> Result<image::RgbaImage> {
    let source = images.first().ok_or(super::Error::MissingImage)?;
    let (width, height) = dimensions;
    let theme = dominant_color(source);
    let mut canvas = cover(source, width, height);
    canvas = blur(
        &canvas,
        config.blur_radius.max(0.0) * height as f32 / 1080.0,
    );
    tint(
        &mut canvas,
        theme,
        config.color_strength.clamp(0.0, 1.0) * 0.65,
    );

    let card_width = (width as f32 * 0.33) as u32;
    let card_height = (height as f32 * 0.72) as u32;
    let mut card = cover(source, card_width, card_height);
    apply_rounded_corners(&mut card, (height as f32 * 0.035) as u32);
    paste_centered(
        &mut canvas,
        &card,
        (width as f32 * 0.72) as i64,
        i64::from(height) / 2,
    );

    draw_titles(
        &mut canvas,
        title,
        subtitle,
        fonts,
        (width as f32 * 0.25) as i32,
        (height as f32 * 0.37) as i32,
        height as f32 * 0.14,
        height as f32 * 0.055,
        Rgba([255, 255, 255, 255]),
    );
    Ok(canvas)
}
