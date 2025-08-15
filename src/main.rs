mod analysis;
mod config;
mod engine;
mod model;
mod stats;

use crate::analysis::Analyzer;
use crate::config::Config;
use crate::engine::Engine;
use anyhow::{Context, Result};
use clap::Parser;
use std::{
    fs,
    path::{Path, PathBuf},
    time::Instant,
};

#[derive(Debug, Parser)]
#[command(version, about)]
struct Args {
    sim_dir: PathBuf,
    sim_idx: Option<usize>,
    // #[arg(short, long)]
    // analyze: bool,
}

fn count_entries<P: AsRef<Path>>(dir: P, regex: &str) -> Result<usize> {
    let dir = dir.as_ref();
    let regex = regex::Regex::new(regex)?;
    let count = fs::read_dir(dir)
        .with_context(|| format!("failed to read {:?}", dir))?
        .filter_map(Result::ok)
        .filter(|entry| {
            entry
                .file_name()
                .to_str()
                .is_some_and(|name| regex.is_match(name))
        })
        .count();
    Ok(count)
}

fn main() -> Result<()> {
    env_logger::Builder::new()
        .format_timestamp_millis()
        .filter_level(log::LevelFilter::Info)
        .parse_default_env()
        .init();

    let args = Args::parse();
    println!("{:?}", args);

    // match count_entries(&args[1], "^Cargo.*$") {
    //     Ok(count) => log::info!("count = {count}"),
    //     Err(err) => log::error!("{:#}", err),
    // }

    let cfg = Config::from_file("config.json")
        .context("failed to create config")
        .unwrap_or_else(|err| {
            log::error!("{:?}", err);
            std::process::exit(1);
        });

    log::info!("cfg = {:#?}", cfg);

    let cfg_str = serde_json::to_string_pretty(&cfg)?;
    fs::write("config.json", cfg_str)?;

    let mut engine = Engine::generate_initial_condition(cfg.clone())?;
    let start = Instant::now();
    engine.run_simulation("frame.bin")?;
    let duration = start.elapsed();
    log::info!("elapsed time = {:?}", duration);

    let mut analyzer = Analyzer::new(cfg.clone());
    analyzer.add_file("frame.bin")?;
    analyzer.save_results("analysis.bin")?;

    Ok(())
}
