use image::{DynamicImage, GenericImageView, Rgba, RgbaImage};

use super::utils::{adjust_brightness, dominant_color, draw_titles_wrapped, optimized_blur, tint};
use super::{Fonts, Result};
use crate::library_poster::RenderConfig;

/// 生成斜线分隔背景与靠右主图的分割风格。
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
    let mut canvas = super::utils::cover(source, width, height);
    canvas = optimized_blur(
        &canvas,
        config.blur_radius.max(0.0) * height as f32 / 1080.0,
    );
    tint(
        &mut canvas,
        adjust_brightness(theme, 0.78),
        config.color_strength.clamp(0.0, 1.0),
    );

    let foreground = align_image_right(source, width, height);
    let shadow_width = (width as f32 * 0.018).max(3.0);
    for y in 0..height {
        let progress = y as f32 / height.max(1) as f32;
        let boundary = width as f32 * (0.55 - progress * 0.15);
        let shadow_start = (boundary - shadow_width).max(0.0) as u32;
        let foreground_start = boundary.max(0.0) as u32;

        for x in shadow_start..foreground_start.min(width) {
            let strength = (x as f32 - shadow_start as f32) / shadow_width;
            let pixel = canvas.get_pixel_mut(x, y);
            for channel in 0..3 {
                pixel[channel] = (pixel[channel] as f32 * (0.82 - strength * 0.18)) as u8;
            }
        }
        for x in foreground_start..width {
            canvas.put_pixel(x, y, *foreground.get_pixel(x, y));
        }
    }

    draw_titles_wrapped(
        &mut canvas,
        title,
        subtitle,
        fonts,
        (width as f32 * 0.25) as i32,
        (height as f32 * 0.36) as i32,
        height as f32 * 0.15,
        height as f32 * 0.06,
        Rgba([255, 255, 255, 235]),
        (width as f32 * 0.40) as i32,
    );
    Ok(canvas)
}

/// 将素材缩放到画布高度，并以右侧展示区域为中心裁剪。
fn align_image_right(source: &DynamicImage, width: u32, height: u32) -> RgbaImage {
    let target_width = (width as f32 * 0.68) as u32;
    let (source_width, source_height) = source.dimensions();
    let scale = f64::max(
        target_width as f64 / source_width as f64,
        height as f64 / source_height as f64,
    );
    let resized_width = (source_width as f64 * scale).ceil() as u32;
    let resized_height = (source_height as f64 * scale).ceil() as u32;
    let resized = source
        .resize_exact(
            resized_width,
            resized_height,
            image::imageops::FilterType::Lanczos3,
        )
        .to_rgba8();
    let crop_left = resized_width.saturating_sub(target_width) / 2;
    let crop_top = resized_height.saturating_sub(height) / 2;
    let cropped =
        image::imageops::crop_imm(&resized, crop_left, crop_top, target_width, height).to_image();
    let mut foreground = RgbaImage::from_pixel(width, height, Rgba([0, 0, 0, 255]));
    image::imageops::overlay(
        &mut foreground,
        &cropped,
        i64::from(width.saturating_sub(target_width)),
        0,
    );
    foreground
}

#[cfg(test)]
mod tests {
    use image::{DynamicImage, Rgb, RgbImage};

    use super::*;

    #[test]
    fn right_aligned_image_fills_target_area() {
        let source = DynamicImage::ImageRgb8(RgbImage::from_pixel(400, 900, Rgb([40, 120, 220])));

        let foreground = align_image_right(&source, 640, 360);

        assert_eq!(foreground.dimensions(), (640, 360));
        assert_eq!(foreground.get_pixel(639, 180), &Rgba([40, 120, 220, 255]));
    }
}
