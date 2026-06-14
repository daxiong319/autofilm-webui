use image::imageops::overlay;
use image::{DynamicImage, Rgba};
use imageproc::geometric_transformations::{Interpolation, rotate_about_center};

use super::utils::{
    apply_rounded_corners, cover, dominant_color, draw_titles, gradient_background,
};
use super::{Fonts, Result};
use crate::library_poster::RenderConfig;

/// 生成左侧标题、右侧九宫格倾斜海报墙的拼贴风格。
pub fn render(
    images: &[DynamicImage],
    title: &str,
    subtitle: &str,
    fonts: &Fonts,
    _config: &RenderConfig,
    dimensions: (u32, u32),
) -> Result<image::RgbaImage> {
    let first = images.first().ok_or(super::Error::MissingImage)?;
    let (width, height) = dimensions;
    let theme = dominant_color(first);
    let mut canvas = gradient_background(width, height, theme);

    let card_width = (width as f32 * 0.20) as u32;
    let card_height = (card_width as f32 * 1.5) as u32;
    let column_spacing = width as f32 * 0.025;
    let row_spacing = height as f32 * 0.05;
    let grid_width = card_width as f32 * 3.0 + column_spacing * 2.0;
    let grid_height = card_height as f32 * 3.0 + row_spacing * 2.0;
    let start_x = width as f32 * 0.84 - grid_width / 2.0;
    let start_y = height as f32 * 0.50 - grid_height / 2.0;
    let angle = -18.0_f32.to_radians();

    for index in 0..9 {
        let column = index / 3;
        let row = index % 3;
        let source = &images[index % images.len()];
        let mut card = cover(source, card_width, card_height);
        apply_rounded_corners(&mut card, (card_width as f32 * 0.08) as u32);
        let rotated = rotate_about_center(&card, angle, Interpolation::Bicubic, Rgba([0, 0, 0, 0]));

        let center_x = start_x
            + column as f32 * (card_width as f32 + column_spacing)
            + card_width as f32 / 2.0;
        let center_y = start_y
            + row as f32 * (card_height as f32 + row_spacing)
            + card_height as f32 / 2.0
            + height as f32 * column as f32 * 0.03;
        overlay(
            &mut canvas,
            &rotated,
            (center_x - rotated.width() as f32 / 2.0) as i64,
            (center_y - rotated.height() as f32 / 2.0) as i64,
        );
    }

    draw_titles(
        &mut canvas,
        title,
        subtitle,
        fonts,
        (width as f32 * 0.25) as i32,
        (height as f32 * 0.35) as i32,
        height as f32 * 0.15,
        height as f32 * 0.06,
        text_color(theme),
    );
    Ok(canvas)
}

fn text_color(color: Rgba<u8>) -> Rgba<u8> {
    let luminance =
        (0.299 * color[0] as f32 + 0.587 * color[1] as f32 + 0.114 * color[2] as f32) / 255.0;
    if luminance > 0.55 {
        Rgba([20, 20, 20, 255])
    } else {
        Rgba([255, 255, 255, 255])
    }
}
