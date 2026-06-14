use image::imageops::blur;
use image::{DynamicImage, Rgba};

use super::utils::{cover, dominant_color, draw_titles, tint};
use super::{Fonts, Result};
use crate::library_poster::RenderConfig;

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
        config.color_strength.clamp(0.0, 1.0) * 0.75,
    );

    let foreground = cover(source, width, height);
    for y in 0..height {
        let progress = y as f32 / height.max(1) as f32;
        let boundary = width as f32 * (0.58 - progress * 0.13);
        for x in boundary.max(0.0) as u32..width {
            canvas.put_pixel(x, y, *foreground.get_pixel(x, y));
        }
    }

    draw_titles(
        &mut canvas,
        title,
        subtitle,
        fonts,
        (width as f32 * 0.25) as i32,
        (height as f32 * 0.36) as i32,
        height as f32 * 0.14,
        height as f32 * 0.055,
        Rgba([255, 255, 255, 255]),
    );
    Ok(canvas)
}
