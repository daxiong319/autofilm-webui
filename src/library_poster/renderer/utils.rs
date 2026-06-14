use std::collections::HashMap;

use ab_glyph::{Font, FontArc, PxScale, ScaleFont};
use image::imageops::{FilterType, overlay};
use image::{DynamicImage, GenericImageView, Rgba, RgbaImage};
use imageproc::drawing::draw_text_mut;

use super::Fonts;

/// 将素材按“填满画布并居中裁剪”的方式缩放。
pub fn cover(image: &DynamicImage, width: u32, height: u32) -> RgbaImage {
    let (source_width, source_height) = image.dimensions();
    let scale = f64::max(
        width as f64 / source_width as f64,
        height as f64 / source_height as f64,
    );
    let resized_width = (source_width as f64 * scale).ceil() as u32;
    let resized_height = (source_height as f64 * scale).ceil() as u32;
    let resized = image
        .resize_exact(resized_width, resized_height, FilterType::Lanczos3)
        .to_rgba8();
    let left = resized_width.saturating_sub(width) / 2;
    let top = resized_height.saturating_sub(height) / 2;
    image::imageops::crop_imm(&resized, left, top, width, height).to_image()
}

/// 使用缩略图量化统计提取出现频率最高的主题色。
pub fn dominant_color(image: &DynamicImage) -> Rgba<u8> {
    let thumbnail = image.thumbnail(96, 96).to_rgb8();
    let mut colors = HashMap::<[u8; 3], usize>::new();
    for pixel in thumbnail.pixels() {
        let quantized = [pixel[0] / 32 * 32, pixel[1] / 32 * 32, pixel[2] / 32 * 32];
        *colors.entry(quantized).or_default() += 1;
    }
    let color = colors
        .into_iter()
        .max_by_key(|(_, count)| *count)
        .map(|(color, _)| color)
        .unwrap_or([96, 96, 96]);
    Rgba([color[0], color[1], color[2], 255])
}

pub fn gradient_background(width: u32, height: u32, color: Rgba<u8>) -> RgbaImage {
    RgbaImage::from_fn(width, height, |x, _| {
        let progress = x as f32 / width.max(1) as f32;
        let factor = 0.42 + progress * 0.58;
        Rgba([
            (color[0] as f32 * factor) as u8,
            (color[1] as f32 * factor) as u8,
            (color[2] as f32 * factor) as u8,
            255,
        ])
    })
}

pub fn tint(image: &mut RgbaImage, color: Rgba<u8>, strength: f32) {
    let strength = strength.clamp(0.0, 1.0);
    for pixel in image.pixels_mut() {
        for channel in 0..3 {
            pixel[channel] =
                (pixel[channel] as f32 * (1.0 - strength) + color[channel] as f32 * strength) as u8;
        }
    }
}

pub fn apply_rounded_corners(image: &mut RgbaImage, radius: u32) {
    let width = image.width();
    let height = image.height();
    let radius = radius.min(width / 2).min(height / 2);
    let radius_squared = i64::from(radius).pow(2);
    for y in 0..height {
        for x in 0..width {
            let corner = match (
                x < radius,
                x >= width - radius,
                y < radius,
                y >= height - radius,
            ) {
                (true, _, true, _) => Some((radius - x, radius - y)),
                (_, true, true, _) => Some((x - (width - radius - 1), radius - y)),
                (true, _, _, true) => Some((radius - x, y - (height - radius - 1))),
                (_, true, _, true) => Some((x - (width - radius - 1), y - (height - radius - 1))),
                _ => None,
            };
            if let Some((distance_x, distance_y)) = corner
                && i64::from(distance_x).pow(2) + i64::from(distance_y).pow(2) > radius_squared
            {
                image.get_pixel_mut(x, y)[3] = 0;
            }
        }
    }
}

pub fn paste_centered(canvas: &mut RgbaImage, image: &RgbaImage, center_x: i64, center_y: i64) {
    overlay(
        canvas,
        image,
        center_x - i64::from(image.width()) / 2,
        center_y - i64::from(image.height()) / 2,
    );
}

#[allow(clippy::too_many_arguments)]
pub fn draw_titles(
    canvas: &mut RgbaImage,
    title: &str,
    subtitle: &str,
    fonts: &Fonts,
    center_x: i32,
    title_y: i32,
    title_size: f32,
    subtitle_size: f32,
    color: Rgba<u8>,
) {
    draw_centered_text(
        canvas,
        title,
        &fonts.title,
        center_x,
        title_y,
        title_size,
        color,
        false,
    );
    if !subtitle.trim().is_empty() {
        draw_centered_text(
            canvas,
            subtitle,
            &fonts.subtitle,
            center_x,
            title_y + (title_size * 1.45) as i32,
            subtitle_size,
            color,
            true,
        );
    }
}

#[allow(clippy::too_many_arguments)]
fn draw_centered_text(
    canvas: &mut RgbaImage,
    text: &str,
    font: &FontArc,
    center_x: i32,
    y: i32,
    size: f32,
    color: Rgba<u8>,
    shadow: bool,
) {
    let scale = PxScale::from(size);
    let width = text_width(font, scale, text);
    let x = center_x - width / 2;
    if shadow {
        let offset = (size * 0.05).max(2.0) as i32;
        draw_text_mut(
            canvas,
            Rgba([0, 0, 0, 120]),
            x + offset,
            y + offset,
            scale,
            font,
            text,
        );
    }
    draw_text_mut(canvas, color, x, y, scale, font, text);
}

fn text_width(font: &FontArc, scale: PxScale, text: &str) -> i32 {
    let scaled = font.as_scaled(scale);
    text.chars()
        .map(|character| {
            let glyph = scaled.scaled_glyph(character);
            scaled.h_advance(glyph.id)
        })
        .sum::<f32>()
        .ceil() as i32
}
