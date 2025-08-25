use std::env;
use std::fs::{self};
use std::process::Command;

#[test]
fn integration_test() {
    let test_dir = "test_sim";
    fs::remove_dir_all(&test_dir).ok();
    fs::create_dir(&test_dir).unwrap();

    Command::new("./scripts/config.py")
        .args(&[test_dir])
        .output()
        .expect("failed to generate config");

    fn run_cli(args: &[&str]) {
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

    run_cli(&["--sim-dir", test_dir, "create"]);
    run_cli(&["--sim-dir", test_dir, "resume", "--run-idx", "0"]);
    run_cli(&["--sim-dir", test_dir, "analyze"]);
    // run_cli(&["--sim-dir", test_dir, "clean"]);
}
