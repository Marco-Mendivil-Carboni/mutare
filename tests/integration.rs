use std::{env, fs, path::PathBuf, process::Command};

#[test]
fn basic_workflow() {
    let test_dir = PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join("basic_workflow");

    fs::remove_dir_all(&test_dir).ok();
    fs::create_dir(&test_dir).expect("failed to create test directory");

    let config_path = test_dir.join("config.toml");
    let config_contents = String::new()
        + "n_env = 2\n"
        + "n_phe = 2\n"
        + "prob_env = [ [ 0.99, 0.01,], [ 0.01, 0.99,],]\n"
        + "prob_rep = [ [ 0.04, 0.0,], [ 0.0, 0.03,],]\n"
        + "prob_dec = [ [ 0.0, 0.02,], [ 0.02, 0.0,],]\n"
        + "n_agt_init = 256\n"
        + "prob_phe_init = [ 0.5, 0.5,]\n"
        + "std_dev_mut = 0.01\n"
        + "steps_per_save = 1024\n"
        + "saves_per_file = 64\n";

    fs::write(&config_path, config_contents).expect("failed to write config file");

    fn run_bin(args: &[&str]) {
        let bin = PathBuf::from(env!("CARGO_BIN_EXE_mutare"));

        let output = Command::new(bin)
            .args(args)
            .output()
            .expect("failed to execute command");

        let stdout_str =
            std::str::from_utf8(&output.stdout).expect("failed to convert stdout to string");
        let stderr_str =
            std::str::from_utf8(&output.stderr).expect("failed to convert stderr to string");

        assert!(
            output.status.success(),
            "failed to run binary with {args:?}\nstdout:\n{stdout_str}\nstderr:\n{stderr_str}\n"
        );
    }

    let test_dir_str = test_dir
        .to_str()
        .expect("failed to convert test directory to string");

    run_bin(&["--sim-dir", test_dir_str, "create"]);
    run_bin(&["--sim-dir", test_dir_str, "create"]);

    run_bin(&["--sim-dir", test_dir_str, "resume", "--run-idx", "0"]);
    run_bin(&["--sim-dir", test_dir_str, "resume", "--run-idx", "0"]);

    run_bin(&["--sim-dir", test_dir_str, "resume", "--run-idx", "1"]);
    run_bin(&["--sim-dir", test_dir_str, "resume", "--run-idx", "1"]);

    run_bin(&["--sim-dir", test_dir_str, "analyze"]);

    run_bin(&["--sim-dir", test_dir_str, "clean"]);

    fs::remove_dir_all(&test_dir).ok();
}
