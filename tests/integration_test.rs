use std::{env, fs, path::Path, process::Command};

#[test]
fn basic_test() {
    let test_dir = "test_sim";
    fs::remove_dir_all(&test_dir).ok();
    fs::create_dir(&test_dir).unwrap();

    let toml_string = r#"
n_env = 2
n_phe = 2
prob_env = [ [ 0.99, 0.01,], [ 0.01, 0.99,],]
prob_rep = [ [ 0.04, 0.0,], [ 0.0, 0.03,],]
prob_dec = [ [ 0.0, 0.02,], [ 0.02, 0.0,],]
n_agt_init = 256
std_dev_mut = 0.01
steps_per_save = 1024
saves_per_file = 64
"#;

    let config_path = Path::new(test_dir).join("config.toml");
    fs::write(&config_path, toml_string).expect("failed to write config.toml");

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
    run_cli(&["--sim-dir", test_dir, "create"]);

    run_cli(&["--sim-dir", test_dir, "resume", "--run-idx", "0"]);
    run_cli(&["--sim-dir", test_dir, "resume", "--run-idx", "0"]);

    run_cli(&["--sim-dir", test_dir, "resume", "--run-idx", "1"]);
    run_cli(&["--sim-dir", test_dir, "resume", "--run-idx", "1"]);

    run_cli(&["--sim-dir", test_dir, "analyze"]);

    run_cli(&["--sim-dir", test_dir, "clean"]);

    fs::remove_dir_all(&test_dir).ok();
}
