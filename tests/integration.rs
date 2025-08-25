use std::env;
use std::fs::{self};
use std::process::Command;

#[test]
fn test_cli_create_resume_analyze_clean() {
    // Create a temporary directory
    let temp_dir = "integration_test";
    let _ = fs::remove_dir_all(&temp_dir); // clean up if exists
    fs::create_dir(&temp_dir).unwrap();

    // Write config.msgpack

    // USE PYTHON SCRIPT TO DO IT -------------------------------------------------------------------------------------

    // Helper function to run the binary and check success
    fn run_cli(args: &[&str]) {
        // `CARGO_BIN_EXE_my_crate` is automatically set by Cargo for integration tests
        let bin = env!("CARGO_BIN_EXE_mutare");
        let output = Command::new(bin)
            .args(args)
            .output()
            .expect("failed to execute command");

        assert!(
            output.status.success(),
            "Command failed:\nstdout: {}\nstderr: {}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
    }

    // Run commands just like the original
    run_cli(&["--sim-dir", temp_dir, "create"]);
    run_cli(&["--sim-dir", temp_dir, "resume", "--run-idx", "0"]);
    run_cli(&["--sim-dir", temp_dir, "analyze"]);
    run_cli(&["--sim-dir", temp_dir, "clean"]);

    // Optional cleanup
    // let _ = fs::remove_dir_all(&temp_dir);
}
