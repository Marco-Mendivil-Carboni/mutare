# TODO

## Analysis improvement

- [ ] Add a Time dependent Stat type:
```rust
/// Time dependent statistic
#[derive(Serialize, Deserialize)]
pub struct TimeStat {
    /// Time of evaluation.
    pub tau: f64,

    /// Value of the statistic.
    pub val: f64,
}
```
- [ ] Use it to analyze the average strategy as a function of tau:
```rust
    /// Time dependent average phenotypic strategy.
    pub avg_strat_phe_tau: Vec<TimeStat>,

    ...

        let tau: Vec<f64> = Vec::new();
        tau.push(1.0 / extinct_rate);
        while *tau.last().context("")? > 2.0 {
            tau.push(tau.last().context("")? / 2.0);
        }
        let avg_strat_phe_at_tau = Vec::with_capacity(tau.len());
        let time_from_extinct = 0.0;
        let last_n_extinct = 0.0;
        for obs in self.all_observables{
            // if obs.n_extinct > last_n_extinct{
            //     time_from_extinct = obs.time-time
            // }
            // time_from_extinct = ...

        }
```
