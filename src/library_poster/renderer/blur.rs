use image::imageops::blur;
use image::{DynamicImage, Rgba};

use super::utils::{cover, dominant_color, draw_titles, tint};
use super::{Fonts, Result};
use crate::library_poster::RenderConfig;

/// 生成以首张素材为全屏模糊背景、标题居中的极简风格。
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
        config.blur_radius.max(8.0) * height as f32 / 1080.0,
    );
    tint(
        &mut canvas,
        theme,
        config.color_strength.clamp(0.0, 1.0) * 0.72,
    );

    draw_titles(
        &mut canvas,
        title,
        subtitle,
        fonts,
        i32::try_from(width / 2).unwrap_or(i32::MAX),
        (height as f32 * 0.35) as i32,
        height as f32 * 0.15,
        height as f32 * 0.065,
        Rgba([255, 255, 255, 255]),
    );
    Ok(canvas)
}
