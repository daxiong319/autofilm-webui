mod alist;
mod alist2strm;
mod ani2alist;
mod app_info;
mod args;
mod config;
mod extensions;
mod library_poster;
mod logging;
mod media_server;
mod schedule;

use args::CliArgs;
use clap::Parser;
use config::{Config, Error as ConfigError};
use tracing::{debug, error, info, warn};
use crate::alist2strm::Alist2Strm;
use crate::ani2alist::Ani2Alist;
use crate::library_poster::LibraryPoster;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let args = CliArgs::parse();
    app_info::print_banner();

    if args.show_version {
        let version_info = serde_json::to_string_pretty(&app_info::APPLICATION_INFO)?;
        println!("{version_info}");
        return Ok(());
    }

    let tz = args.app_timezone();

    let _logging_guard = logging::init(args.log_level(), &args.log_path, tz, args.colorful_log)?;
    debug!(
        debug = args.debug,
        config_path = %args.config_path.display(),
        log_path = %args.log_path,
        timezone = ?args.timezone,
        "启动参数解析完成"
    );
    let config = match Config::load(&args.config_path) {
        Ok(config) => config,
        Err(ConfigError::CreatedExample { path }) => {
            error!(config_path = %path, "配置文件不存在，已生成示例配置文件，请编辑后重新启动程序");
            return Ok(());
        }
        Err(err) => return Err(Box::new(err) as Box<dyn std::error::Error + Send + Sync>),
    };

    info!(timezone = %tz, "使用应用时区");

    // 如果指定了 --run-once 参数，则单次执行指定任务后退出
    if let Some(task_id) = &args.run_once {
        info!(task_id = %task_id, "单次运行模式：执行指定任务后退出");
        return run_single_task(config, task_id, tz).await;
    }

    let (mut scheduler, scheduled_count) = schedule::create_scheduler(config, tz).await?;

    if scheduled_count == 0 {
        warn!("没有可调度的任务");
        return Ok(());
    }

    scheduler.start().await?;
    info!(scheduled_count, "AutoFilm 调度器启动完成");

    // 阻塞主任务，直到收到 Ctrl-C；调度器会在后台按 cron 触发任务。
    tokio::signal::ctrl_c().await?;
    info!("AutoFilm 收到退出信号，正在退出中...");
    scheduler.shutdown().await?;
    info!("AutoFilm 已成功退出");
    Ok(())
}

/// 单次执行指定任务（不启动调度器）
async fn run_single_task(
    config: Config,
    task_id: &str,
    tz: chrono_tz::Tz,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    use schedule::utils;

    let alist_clients = utils::create_alist_clients(&config.alist).await;
    let media_server_clients = utils::create_media_server_clients(&config.media_servers);

    // 尝试在 Alist2Strm 任务中查找
    for task in &config.alist2strm_tasks {
        if task.id == task_id {
            info!(task_id = %task_id, "找到 Alist2Strm 任务，开始执行");
            let Some((client, server_url)) = alist_clients.get(&task.alist) else {
                error!(task_id = %task_id, alist = %task.alist, "AList 客户端不存在");
                return Ok(());
            };
            let runner = Alist2Strm::new(task.clone(), client.clone(), server_url.clone());
            match runner.run().await {
                Err(err) => {
                    error!(task_id = %task_id, error = %err, "任务执行失败");
                    return Ok(());
                }
                Ok(summary) => {
                    info!(
                        task_id = %summary.task_id,
                        scanned_dir_count = summary.scanned_dir_count,
                        strm_created_count = summary.strm_created_count,
                        strm_updated_count = summary.strm_updated_count,
                        "Alist2Strm 任务完成"
                    );
                }
            }
            return Ok(());
        }
    }

    // 尝试在 Ani2Alist 任务中查找
    for task in &config.ani2alist_tasks {
        if task.id == task_id {
            info!(task_id = %task_id, "找到 Ani2Alist 任务，开始执行");
            let Some((client, _server_url)) = alist_clients.get(&task.alist) else {
                error!(task_id = %task_id, alist = %task.alist, "AList 客户端不存在");
                return Ok(());
            };
            let runner = Ani2Alist::new(task.clone(), client.clone(), tz);
            match runner.run().await {
                Err(err) => {
                    error!(task_id = %task_id, error = %err, "任务执行失败");
                    return Ok(());
                }
                Ok(()) => {
                    info!(task_id = %task_id, "Ani2Alist 任务完成");
                }
            }
            return Ok(());
        }
    }

    // 尝试在 LibraryPoster 任务中查找
    for task in &config.library_poster_tasks {
        if task.id == task_id {
            info!(task_id = %task_id, "找到 LibraryPoster 任务，开始执行");
            let Some(client) = media_server_clients.get(&task.server) else {
                error!(task_id = %task_id, server = %task.server, "媒体服务器客户端不存在");
                return Ok(());
            };
            let runner = match LibraryPoster::new(task.clone(), client.clone()) {
                Ok(runner) => runner,
                Err(err) => {
                    error!(task_id = %task_id, error = %err, "初始化任务失败");
                    return Ok(());
                }
            };
            match runner.run().await {
                Err(err) => {
                    error!(task_id = %task_id, error = %err, "任务执行失败");
                    return Ok(());
                }
                Ok(summary) => {
                    info!(
                        task_id = %summary.task_id,
                        library_count = summary.library_count,
                        succeeded_count = summary.succeeded_count,
                        uploaded_count = summary.uploaded_count,
                        "LibraryPoster 任务完成"
                    );
                }
            }
            return Ok(());
        }
    }

    error!(task_id = %task_id, "未找到匹配的任务 ID");
    Err(format!("任务 ID '{}' 不存在", task_id).into())
}
