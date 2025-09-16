# mutare

`mutare` (Latin for "to change") is a simple tool to simulate and analyze a stochastic agent-based model of adaptation in uncertain environments.

---

## Overview

`mutare` simulates a stochastic agent-based model of adaptation in uncertain environments with the following characteristics:

- The **environment** is a discrete random variable with `n_env` possible states and follows a **Markov chain** with configurable transition probabilities (`prob_trans_env`).
- Each agent carries a **phenotype**, a discrete variable with `n_phe` possible states, and a **probability distribution over phenotypes**.
- At every simulation step, agents may **replicate** or **decease** according to environment and phenotype specific probabilities (`prob_rep` and `prob_dec`).
- The offspring's phenotype is sampled from the parent's distribution.
- The offspring inherits the parent's distribution, but with probability `prob_mut` this distribution suffers a slight mutation (modulated by `std_dev_mut`).
- At every simulation step, the population is capped at its initial size and reinitialized if extinction is reached.
- Each output file contains `steps_per_file` records, and the state is saved every `steps_per_save` steps if specified.

From these output files `mutare` can also compute the following observables:
- The relative change in the number of agents per step.
- The probability of extinction.
- The probability of each environment.
- The average probability distribution over phenotypes across agents.

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
cargo build --release # The release profile is much faster than the dev profile
```

### Basic Usage

Start by creating a simulation directory (e.g. `example_sim/`) and placing a config file named `config.toml` inside it.

Here is an example config file:

```toml
[model]
n_env = 2
n_phe = 2
prob_trans_env = [ [ 0.99, 0.01,], [ 0.01, 0.99,],]
prob_rep = [ [ 0.012, 0.0,], [ 0.0, 0.008,],]
prob_dec = [ [ 0.0, 0.016,], [ 0.012, 0.0,],]
prob_mut = 0.001
std_dev_mut = 0.1

[init]
n_agt = 4096
prob_phe = [ 0.5, 0.5,]

[output]
steps_per_file = 16384
steps_per_save = 1024

```

Now you can begin making simulation runs and analyzing them. Here are some examples of common commands:

```bash
mutare --sim-dir example_sim/ create # Create new simulation run
mutare --sim-dir example_sim/ resume --run-idx 0  # Resume run 0
mutare --sim-dir example_sim/ analyze # Analyze all runs
mutare --sim-dir example_sim/ clean # Clean up all runs
```

Run `mutare --help` to see more detailed help information.

---

## Advanced Usage

The repository also includes some Python utility modules in `scripts/utils/` for automating simulation workflows.

### Prerequisites

- **Python 3.12+**

### Python Setup

If you want to use these utilities you can set up the Python environment by running the following commands (after having cloned the repository):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Documentation

Documentation is available via:

```bash
cargo doc --no-deps --open # Not generating docs for dependencies saves time
```

---

## License

This project is licensed under the MIT License.

---

## Contact

For questions or collaboration, reach out to marcomc@ucm.es or open an issue on GitHub.

