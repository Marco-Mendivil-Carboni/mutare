# mutare

`mutare` (Latin for "to change") is a simple tool to simulate and analyze a stochastic agent-based model of adaptation in uncertain environments.

---

## Overview

`mutare` simulates a stochastic agent-based model of adaptation in uncertain environments with the following characteristics:

- The **environment** is a discrete random variable with `n_env` possible states and follows a **Markov chain** with configurable transition probabilities (`prob_env`).
- Each agent carries a **phenotype**, a discrete variable with `n_phe` possible states, and a **probability distribution over phenotypes**.
- At every simulation step, agents may **replicate** or **decease** according to environment and phenotype specific probabilities (`prob_rep` and `prob_dec`).
- The offspring's phenotype is sampled from the parent's distribution, and its distribution is the parent's one with a slight mutation (modulated by `std_dev_mut`).
- The simulation state is saved every `steps_per_save` steps, and `saves_per_file` states are stored in each trajectory file.

From these trajectories `mutare` can compute metrics such as:
- The probability of finding the system in each environment.
- The average probability distribution over phenotypes across agents.
- The net change in the number of agents per step.

---

## Getting Started

### Prerequisites

- **Rust** (install via [rustup](https://rustup.rs/))

### Installation

You can install `mutare` via `cargo`:

```bash
cargo install mutare
```

Or build it from source:

```bash
git clone https://github.com/Marco-Mendivil-Carboni/mutare.git
cd mutare
cargo build --release # The release profile is much faster than the dev profile.
```

### Basic Usage

First you must create a simulation directory (`./my_sim_dir`) and place inside it a config file named `config.toml`. Here is an example config file:

```toml
n_env = 2
n_phe = 2
prob_env = [ [ 0.99, 0.01,], [ 0.01, 0.99,],]
prob_rep = [ [ 0.04, 0.0,], [ 0.0, 0.03,],]
prob_dec = [ [ 0.0, 0.02,], [ 0.02, 0.0,],]
n_agt_init = 1024
std_dev_mut = 0.01
steps_per_save = 4096
saves_per_file = 64
```

Then you can use this tool. Run `mutare --help` to display help information. Here are some examples of common commands:

```bash
mutare --sim-dir ./my_sim_dir create # Create a new simulation run.
mutare --sim-dir ./my_sim_dir resume --run-idx 0  # Resume run 0.
mutare --sim-dir ./my_sim_dir analyze # Analyze all runs.
mutare --sim-dir ./my_sim_dir clean # Clean up all simulation runs.
```

---

## Advanced Usage

Convenient Python scripts are provided in the `scripts/` folder that allow orchestration of multiple simulations automatically.

### Prerequisites:

- **Python 3.10+**

### Python Setup

To setup the python environment run the following commands (asuming you have cloned the repo and built the binary):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Documentation

Documentation is available via:

```bash
cargo doc --no-deps --open # Not generating the dependency docs is much faster.
```

---

## License

This project is licensed under the MIT License.

---

## Contact

For questions or collaboration, reach out to marcomc@ucm.es or open an issue on GitHub.

