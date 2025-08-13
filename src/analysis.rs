// use std::{
//     fs::File,
//     io::{BufWriter, Write},
//     path::Path,
// };

// use crate::model::State;
// use crate::stats::{OnlineStats, TimeSeriesStats};
// use anyhow::Result;

// pub trait Obs {
//     fn update(&mut self, state: &State) -> Result<()>;
//     fn write(&self, out: &mut dyn Write) -> Result<()>;
// }

// pub struct ProbEnvObs {
//     stats_vec: Vec<OnlineStats>,
// }

// impl ProbEnvObs {
//     pub fn new(state: &State) -> Self {
//         let mut stats_vec = Vec::new();
//         stats_vec.resize_with(state.mp.n_env, OnlineStats::default);
//         Self { stats_vec }
//     }
// }

// impl Obs for ProbEnvObs {
//     fn update(&mut self, state: &State) -> Result<()> {
//         let env = state.env;
//         for (i_env, stats) in self.stats_vec.iter_mut().enumerate() {
//             stats.add(if i_env == env { 1.0 } else { 0.0 });
//         }
//         Ok(())
//     }

//     fn write(&self, out: &mut dyn Write) -> Result<()> {
//         writeln!(out, "#prob_env:")?;
//         writeln!(out, "#            mean        sqrt(var)")?;
//         for stats in &self.stats_vec {
//             writeln!(
//                 out,
//                 " {:016.14} {:016.14}",
//                 stats.mean(),
//                 stats.sample_variance().sqrt()
//             )?;
//         }
//         Ok(())
//     }
// }

// pub struct AvgProbPheObs {
//     stats_vec: Vec<OnlineStats>,
// }

// impl AvgProbPheObs {
//     pub fn new(state: &State) -> Self {
//         let mut stats_vec = Vec::new();
//         stats_vec.resize_with(state.mp.n_phe, OnlineStats::default);
//         Self { stats_vec }
//     }
// }

// impl Obs for AvgProbPheObs {
//     fn update(&mut self, state: &State) -> Result<()> {
//         let n_phe = self.stats_vec.len();
//         let agt_vec = &state.agt_vec;
//         if agt_vec.is_empty() {
//             return Ok(());
//         }

//         let mut prob_phe_sum = vec![0.0; n_phe];
//         for agt in agt_vec {
//             let prob_phe = agt.prob_phe();
//             for (i_phe, &val) in prob_phe.iter().enumerate() {
//                 prob_phe_sum[i_phe] += val;
//             }
//         }

//         for i_phe in 0..n_phe {
//             self.stats_vec[i_phe].add(prob_phe_sum[i_phe] / agt_vec.len() as f64);
//         }
//         Ok(())
//     }

//     fn write(&self, out: &mut dyn Write) -> Result<()> {
//         writeln!(out, "#avg_prob_phe:")?;
//         writeln!(out, "#            mean        sqrt(var)")?;
//         for stats in &self.stats_vec {
//             writeln!(
//                 out,
//                 " {:016.14} {:016.14}",
//                 stats.mean(),
//                 stats.sample_variance().sqrt()
//             )?;
//         }
//         Ok(())
//     }
// }

// pub struct NAgtDiffObs {
//     stats: TimeSeriesStats,
// }

// impl NAgtDiffObs {
//     pub fn new() -> Self {
//         Self {
//             stats: TimeSeriesStats::default(),
//         }
//     }
// }

// impl Obs for NAgtDiffObs {
//     fn update(&mut self, state: &State) -> Result<()> {
//         self.stats.add_value(state.n_agt_diff);
//         Ok(())
//     }

//     fn write(&self, out: &mut dyn Write) -> Result<()> {
//         self.stats.process();

//         writeln!(out, "#n_agt_diff:")?;
//         writeln!(
//             out,
//             "#            mean        sqrt(var)              sem      thermalized"
//         )?;
//         write!(out, " {:016.12}", self.stats.get_mean())?;
//         write!(out, " {:016.12}", self.stats.get_var().sqrt())?;
//         write!(out, " {:016.12}", self.stats.get_sem())?;
//         writeln!(
//             out,
//             " {:>16}",
//             if self.stats.get_thermalized() {
//                 "true"
//             } else {
//                 "false"
//             }
//         )?;
//         Ok(())
//     }
// }

// pub struct Analyzer {
//     state: State,
//     obs_ptr_vec: Vec<Box<dyn Obs>>,
// }

// impl Analyzer {
//     pub fn new(cfg: &serde_yaml::Value) -> Self {
//         let state = State::new(cfg);
//         let mut obs_ptr_vec: Vec<Box<dyn Obs>> = Vec::new();
//         obs_ptr_vec.push(Box::new(ProbEnvObs::new(&state)));
//         obs_ptr_vec.push(Box::new(AvgProbPheObs::new(&state)));
//         obs_ptr_vec.push(Box::new(NAgtDiffObs::new()));

//         Self {
//             state,
//             obs_ptr_vec,
//         }
//     }

//     pub fn add_traj_file<P: AsRef<Path>>(&mut self, traj_path: P) -> Result<()> {
//         let mut traj_file = File::open(traj_path.as_ref())?;
//         for _ in 0..self.state.saves_per_file {
//             self.state.read_frame(&mut traj_file)?;

//             for obs in &mut self.obs_ptr_vec {
//                 obs.update(&self.state)?;
//             }
//         }
//         Ok(())
//     }

//     pub fn write<P: AsRef<Path>>(&self, ana_path: P) -> Result<()> {
//         let file = File::create(ana_path)?;
//         let mut writer = BufWriter::new(file);
//         for obs in &self.obs_ptr_vec {
//             obs.write(&mut writer)?;
//             writeln!(writer)?;
//         }
//         Ok(())
//     }
// }
