pub use average::Moments4 as OnlineStats;
// use ndarray::Array1;

// pub struct TimeSeriesStats {
//     time_series: Vec<f64>,
//     i_therm: usize,
// }

// impl TimeSeriesStats {
//     pub fn new() -> Self {
//         Self {
//             time_series: Vec::new(),
//             online_stats: OnlineStats::new(),
//         }
//     }

//     pub fn add(&mut self, new_val: f64) {
//         self.time_series.push(new_val);
//     }

//     pub fn mean(&self) -> f64 {
//         self.online_stats.mean()
//     }

//     pub fn sample_variance(&self) -> f64 {
//         self.online_stats.sample_variance()
//     }

//     pub fn sem(&self) -> f64 {
//         if self.time_series.len() < 2 {
//             return f64::NAN;
//         }

//         let mut blk = &self.time_series;
//         let mut sem_2: f64;
//         let mut uppr_lim = f64::NAN;

//         loop {
//             let arr = Array1::from(blk.clone());
//             let var = arr.var(1.0);
//             let n_vals = blk.len();
//             sem_2 = var / (n_vals as f64);

//             if uppr_lim.is_nan() || sem_2 > uppr_lim {
//                 uppr_lim = sem_2 * (1.0 + (2.0 / (n_vals as f64 - 1.0)).sqrt());
//             } else {
//                 break;
//             }

//             if n_vals < 4 {
//                 break;
//             }

//             let mut aux_blk = Vec::with_capacity(n_vals / 2);
//             for pair in blk.chunks(2) {
//                 if pair.len() == 2 {
//                     aux_blk.push((pair[0] + pair[1]) / 2.0);
//                 }
//             }
//             blk = &aux_blk;
//         }

//         sem_2.sqrt()
//     }

//     pub fn thermalized(&self) -> bool {
//         let mut min_mse = f64::INFINITY;
//         let mut i_therm = self.time_series.len() / 2;

//         for div in [2usize, 4, 8, 16, 32, 64] {
//             let candidate = self.time_series.len() / div;
//             if candidate >= self.time_series.len() {
//                 break;
//             }

//             let aux = &self.time_series[candidate..];
//             if aux.len() < 2 {
//                 break;
//             }

//             let arr = Array1::from(aux.to_vec());
//             let var = arr.var(1.0);
//             let n_vals = aux.len();
//             let mse = var * (n_vals as f64 - 1.0) / ((n_vals * n_vals) as f64);

//             if mse < min_mse {
//                 min_mse = mse;
//                 i_therm = candidate;
//             }
//         }

//         let thermalized = i_therm != self.time_series.len() / 2;
//         thermalized
//     }
// }
