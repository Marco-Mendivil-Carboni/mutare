# mutare

`mutare` (Latin for "to change") is a simple tool to simulate and analyze a stochastic agent-based model of adaptation in uncertain environments.

---

## Overview

`mutare` simulates a stochastic agent-based model of adaptation in uncertain environments with the following characteristics:

- The **environment** is a discrete variable with `n_env` possible values and follows a **Markov chain** defined by the transition rates `rates_trans`.
- Each agent carries a **phenotype**, a discrete variable with `n_phe` possible values, and a **phenotypic strategy**, a distribution over phenotypes.
- Agents may **duplicate** or **die** according to environment and phenotype specific rates (`rates_birth` and `rates_death`).
- The offspring's phenotype is sampled from the parent's phenotypic strategy.
- The offspring inherits the parent's phenotypic strategy, but with probability `prob_mut` it suffers a random mutation and changes completely.
- At every simulation step, the population is capped at its initial size (`n_agents`) and reinitialized if extinction is reached.
- Initially, if `strat_phe` is set, all agents will share that same strategy; otherwise, they will each have a random strategy.

During the simulation, every `steps_per_save` steps, the following observables are computed and saved:
- Current simulation time
- Time until the next event
- Instantaneous population growth rate
- Number of extinctions so far
- Average phenotypic strategy
- Standard deviation of the phenotypic strategy

Every `steps_per_file` steps, the simulation is stopped and a new output file is written to disk.

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
rates_trans = [ [ -1.0, 1.0,], [ 1.0, -1.0,],]
rates_birth = [ [ 1.2, 0.0,], [ 0.0, 0.9,],]
rates_death = [ [ 0.0, 1.6,], [ 1.0, 0.0,],]
prob_mut = 0.002

[init]
n_agents = 240
strat_phe = [ 0.5, 0.5,]

[output]
steps_per_file = 65536
steps_per_save = 256

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

