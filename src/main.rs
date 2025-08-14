mod analysis;
mod config;
mod engine;
mod model;
mod stats;

use crate::config::Config;
use crate::engine::Engine;
use crate::stats::OnlineStats;
use anyhow::{Context, Result};
use clap::Parser;
use ron::ser::{PrettyConfig, to_string_pretty};
use std::{
    env, fs,
    path::{Path, PathBuf},
    time::Instant,
};

#[derive(Parser, Debug)]
#[command(author, version, about)]
struct Args {
    sim_dir: PathBuf,

    sim_idx: Option<usize>,

    #[arg(short, long)]
    analyze: bool,
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

    let args_0 = Args::parse();
    println!("{:?}", args_0);

    let args: Vec<_> = env::args().collect();

    let name = &args[0];

    log::info!("program name = {name}");

    let mut stats = OnlineStats::new();
    stats.add(1.0);
    stats.add(2.0);
    log::info!("{} {}", stats.mean(), stats.var());

    match count_entries(&args[1], "^Cargo.*$") {
        Ok(count) => log::info!("count = {count}"),
        Err(err) => log::error!("{:#}", err),
    }

    let cfg_str = fs::read_to_string("config.ron")?;
    let cfg = Config::new(&cfg_str)
        .context("failed to create config")
        .unwrap_or_else(|err| {
            log::error!("{:?}", err);
            std::process::exit(1);
        });

    log::info!("cfg = {:#?}", cfg);

    let cfg_str = to_string_pretty(&cfg, PrettyConfig::default())?;
    fs::write("config.ron", cfg_str)?;

    let mut sim_eng = Engine::generate_initial_condition(cfg)?;
    let start = Instant::now();
    sim_eng.run_simulation("frame.bin")?;
    let duration = start.elapsed();
    log::info!("Time elapsed: {:?}", duration);

    Ok(())
}
