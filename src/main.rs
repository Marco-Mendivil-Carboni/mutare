mod analysis;
mod config;
mod engine;
mod manager;
mod model;
mod stats;

use crate::manager::Manager;
use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use std::path::PathBuf;

/// Command-line interface for managing, producing and analyzing simulations.
#[derive(Debug, Parser)]
#[command(version, about)]
struct CLI {
    /// Path to the simulation directory.
    #[arg(long)]
    sim_dir: PathBuf,

    /// Command to specify the desired action.
    #[command(subcommand)]
    command: Command,
}

/// Available commands for the simulation CLI.
#[derive(Debug, Subcommand)]
enum Command {
    /// Create a new simulation run.
    Create,

    /// Resume an existing simulation run.
    Resume {
        /// Index of the run to resume.
        #[arg(long)]
        run_idx: usize,
    },

    /// Analyze all simulation runs.
    Analyze,

    /// Clean up all simulation runs.
    Clean,
}

/// Entry point of the application.
fn main() {
    // Initialize logging with millisecond timestamps and INFO level by default.
    env_logger::Builder::new()
        .format_timestamp_millis()
        .filter_level(log::LevelFilter::Info)
        .parse_default_env()
        .init();

    // Run the CLI and exit with error code 1 if any error occurs.
    if let Err(error) = run_cli() {
        log::error!("{error:#?}");
        std::process::exit(1);
    }
}

/// Parse CLI arguments and execute the requested command.
fn run_cli() -> Result<()> {
    // Parse command-line arguments.
    let args = CLI::parse();
    log::info!("{args:#?}");

    // Construct a manager for the specified simulation directory.
    let mgr = Manager::new(args.sim_dir).context("failed to construct mgr")?;

    // Execute the requested command.
    match args.command {
        Command::Create => mgr.create_run()?,
        Command::Resume { run_idx } => mgr.resume_run(run_idx)?,
        Command::Analyze => mgr.analyze_sim()?,
        Command::Clean => mgr.clean_sim()?,
    }

    Ok(())
}
