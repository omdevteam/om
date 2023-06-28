#include "peakfinder8.hh"

namespace {
using std::vector;

/**
 * Holds pointers to detector data, a pixel mask and pixel radius information.
 * Also maintains a vector describing the detector panel layout in memory, as
 * well as useful numbers such as the number of asics/panels and the total
 * number of pixels in the image.
 */
struct DetectorData {
  float* data; ///< Pointer to raw data array
  char* mask;  ///< Pointer to binary mask of pixels. 1 means good pixel
  /// Pointer to the radius mapping of each corresponding data point (pixel).
  /// I.e. the calculated radius at that pixel position compared to the beam
  /// center
  float* radius;

  int fs_size;          ///< Size of a panel along the fast-scan (x) dimension.
  int ss_size;          ///< Size of a panel along the slow-scan (y) dimension.
  int pixels_per_panel; ///< Number of pixels in a single asic/panel.
  int num_panels;       ///< Number of asics/panels in the data stream.
  long num_pixels;      ///< TOTAL number of pixels in all asics/panels.
  vector<int> shape;    ///< Vector of data dimensions as represented in Python.

  DetectorData(float* data, char* mask, float* radius, const vector<int>& data_shape)
    : data{data}
    , mask{mask}
    , radius{radius}
    , shape(data_shape)
    , fs_size(data_shape.back())
    , ss_size(data_shape[data_shape.size() - 2])
    , pixels_per_panel(0)
    , num_panels(1)
    , num_pixels(0l)
  {
    for (int i = 0; i < shape.size() - 2; ++i) {
      num_panels *= shape[i];
    }
    pixels_per_panel = fs_size * ss_size;
    num_pixels = num_panels * pixels_per_panel;
  }
};
using DetData = DetectorData;

/**
 * Store user specified algorithm options on values such is minimum SNR, and
 * the maximum number of peaks to find in an image.
 */
struct HitfinderOptions {
  float ADCthresh;   ///< Threshold ADC value to be considered for peak finding
  float MinSNR;      ///< Minimum SNR of peak vs local background to count
  long MinPixCount;  ///< Minimum number of pixels in a peak
  long MaxPixCount;  ///< Maximum number of pixels in a peak
  int LocalBGRadius; ///< Radius to search in for local background calculation
  int MaxNumPeaks;   ///< Maximum number of peaks to find

  HitfinderOptions(float threshADC, float SNRmin, long MinNumPix,
                   long MaxNumPix, int BkgndRadius, int NumPeaksMax)
    : ADCthresh(threshADC)
    , MinSNR(SNRmin)
    , MinPixCount(MinNumPix)
    , MaxPixCount(MaxNumPix)
    , LocalBGRadius(BkgndRadius)
    , MaxNumPeaks(NumPeaksMax)
  {}
};
using HfOpts = HitfinderOptions;

/**
 * Store information for calculations on individual peaks. Maintains a record
 * of indices that comprise a given peak along the fs and ss dimensions, using
 * the panel indexing convention. I.e. (0,0) is top-left of each individual
 * panel. Also holds the indices of peak pixels in the 1D flattened panel. The
 * structure is reused, with the indices being overwritten each time a new peak
 * is found. Additionally, a pixel peaks mask is maintained to avoid counting
 * the same pixels in multiple peaks. This mask is NOT overwritten.
 */
struct peakfinder_intern_data {
  vector<char> pix_in_peak_map; ///< Mask of peak pixels to avoid double counting
  vector<int> infs;             ///< Panel indices along fs dimension in peak.
  vector<int> inss;             ///< Panel indices along ss dimension in peak.
  vector<int> peak_pixels;      ///< 1D indices of the peak being processed.

  peakfinder_intern_data(int data_size, int max_pix_count)
    : pix_in_peak_map(data_size)
    , infs(data_size) // Could be switched to a vector of num_pix in panel
    , inss(data_size) // Could be switched to a vector of num_pix in panel
    , peak_pixels(max_pix_count)
  {}

  // Remove copy construction/assignment
  peakfinder_intern_data(const peakfinder_intern_data&) = delete;
  peakfinder_intern_data &operator=(peakfinder_intern_data&) = delete;
};

/**
 * Struct to store information on the peaks that have been found.
 * Stores the center-of-mass (COM) along the x (fast-scan) and y (slow-scan)
 * dimensions, as well as statistics on intensity and signal-to-noise.
 * Units of stored COMs are in pixel indices measured on a asic/panel basis,
 * i.e. begininning at (0,0) at the top-left of each panel of a multi-panel
 * detector. The panel number is also stored to correctly place the peak on
 * a multi-panel detector.
 */
struct peakfinder_peak_data {
  int num_found_peaks{};    ///< Total number of found peaks
  vector<int> npix;         ///< Vector for the number of pixels for each peak.
  /// Vector of center of masses of each peak in the fast - scan dimension.
  /// Units are panel-indices measured from the top-left of each asic/panel.
  vector<float> com_fs;
  vector<float> com_ss;     ///< Same as com_fs but in the slow-scan dimension
  vector<int> com_index;    ///< Peak's center-of-mass index for the 1D panel repr.
  vector<int> panel_number; ///< The number of the asic/panel the peak is on.
  vector<float> tot_i;      ///< Integrated intensity of the peak.
  vector<float> max_i;      ///< Max single pixel intensity in the peak.
  vector<float> sigma;      ///< Signal-to-noise of the peak's background.
  vector<float> snr;        ///< Signal-to-noise of the peak.

  explicit peakfinder_peak_data(int max_num_peaks)
    : npix(max_num_peaks)
    , com_fs(max_num_peaks)
    , com_ss(max_num_peaks)
    , com_index(max_num_peaks)
    , panel_number(max_num_peaks)
    , tot_i(max_num_peaks)
    , max_i(max_num_peaks)
    , sigma(max_num_peaks)
    , snr(max_num_peaks)
  {}

  // Remove copy construction/assignment
  peakfinder_peak_data(const peakfinder_peak_data&) = delete;
  peakfinder_peak_data &operator=(peakfinder_peak_data&) = delete;
};

/**
 * Class to store radial statistics which are used for background corrections.
 * Detector statistics are calculated in radial bins to provide more accurate
 * corrections for peak detection in the presence of varying background due to
 * effects from, e.g., solvent rings.
 */
class RadialStats {
public:
  vector<float> roffset; ///<
  vector<float> rthreshold; ///<
  vector<float> lthreshold; ///<
  vector<float> rsigma; ///<
  vector<int> rcount; ///<
  int n_rad_bins; ///<

  explicit RadialStats(int bins)
    : n_rad_bins{bins}
    , roffset(bins)
    , rthreshold(bins)
    , lthreshold(bins)
    , rsigma(bins)
    , rcount(bins)
  {}

  // Remove copy construction/assignment
  RadialStats(const RadialStats&) = delete;
  RadialStats &operator=(RadialStats&) = delete;


  void compute_bins_and_stats(const DetData& img_data, HfOpts& options,
                              int iterations);

private:
  void fill_radial_bins(const float* data, long num_pix,
                        const float* pix_radius, const char* mask);
};

void RadialStats::fill_radial_bins(const float* data, long num_pix,
                                   const float* pix_radius, const char* mask)
{
  for (int pidx = 0; pidx < num_pix; ++pidx) {
    if (mask[pidx]) {
      int curr_r = static_cast<int>(rint(pix_radius[pidx]));
      float value = data[pidx];

      if (value < rthreshold[curr_r]
          && value > lthreshold[curr_r])
      {
        roffset[curr_r] += value;
        rsigma[curr_r] += (value * value);
        rcount[curr_r] += 1;
      }
    }
  }
}

int compute_num_radial_bins(int num_pix, const float* pix_radius) {
  float max_r = 1e-9;

  for (int pidx = 0; pidx < num_pix; pidx++) {
    if (pix_radius[pidx] > max_r) {
      max_r = pix_radius[pidx];
    }
  }

  return static_cast<int>(ceil(max_r)) + 1;
}

/**
 * Compute radial bins and statistics.
 *
 * @param img_data Contains image data and detector shape parameters.
 * @param options Contains user supplied threshold and SNR options.
 * @param iterations Number of times to run algo. to reduce effect from peaks.
 */
void RadialStats::compute_bins_and_stats(const DetData& img_data, HfOpts& options,
                                          int iterations = 5)
{
  for (int iter = 0; iter < iterations; iter++) {
    if (iter > 0) {
      // Function called on newly 0-initialized members -> save the first
      // iteration of 0-filling
      std::fill(roffset.begin(), roffset.end(), 0);
      std::fill(rsigma.begin(), rsigma.end(), 0);
      std::fill(rcount.begin(), rcount.end(), 0);
    }

    fill_radial_bins(img_data.data, img_data.num_pixels, img_data.radius, img_data.mask);

    for (int ri = 0; ri < n_rad_bins; ++ri) {
      if (rcount[ri] == 0) {
        roffset[ri] = 0;
        rsigma[ri] = 0;
        rthreshold[ri] = FLT_MAX;
        lthreshold[ri] = FLT_MIN;
      } else {
        float ri_offset = roffset[ri]/rcount[ri];
        float ri_sigma = rsigma[ri]/rcount[ri] - (ri_offset * ri_offset);

        if (ri_sigma >= 0) {
          ri_sigma = sqrt(ri_sigma);
        }

        roffset[ri] = ri_offset;
        rsigma[ri] = ri_sigma;
        rthreshold[ri] = roffset[ri] + options.MinSNR * rsigma[ri];
        lthreshold[ri] = roffset[ri] - options.MinSNR * rsigma[ri];

        if (rthreshold[ri] < options.ADCthresh) {
          rthreshold[ri] = options.ADCthresh;
        }
      }
    }
  }
}

/**
 * Returns the starting index for the requested panel, given the data shape.
 * Panels are assumed to be contiguous in memory and ordered numerically, and
 * are numbered starting from 0.
 * See the complementary function `calc_panel_indices` for more information.
 *
 * @param panel_num Which panel to find the starting point of.
 * @param data_shape Holds the size of the data dimensions and related values.
 * @return start_idx The starting index of the panel in contiguous data.
 */
int calc_panel_start_index(int panel_num, const DetData& img_data)
{
  int start_idx = img_data.pixels_per_panel * panel_num;
  return start_idx;
}

/**
 * Returns the indices for the requested panel in the shape of the original
 * Python array. The final two dimensions of the object are assumed to be the
 * slow-scan and fast-scan dimensions of the individual panels, while the other
 * dimensions relate to ordering/organization of the panels. Only the panel
 * indices are returned.
 * E.g. for an ndarray of dimensionality (2, 4, 8, 156, 156) and a panel number
 * of 9 the indices (0, 1, 1) will be returned. Panels are numbered from 0.
 *
 * @param panel_num Which panel to find the starting point of.
 * @param data_shape Holds the size of the of the data dimensions and related values
 * @return indices The panel indices for the requested panel number
 */
vector<std::size_t> calc_panel_indices(int panel_num, const DetData& img_data)
{
  vector<std::size_t> indices((img_data.shape.size() - 2));
  int len = indices.size();

  for (auto i = 0; i < len; ++i) {
    // Hold the "base" of the current panel index
    // I.e. the number of panels you add by incrementing this index by one
    int base_index{1};
    for (auto j = i+1; j < len; ++j) {
      base_index *= img_data.shape[j];
    }
    indices[i] = panel_num / base_index; // Integer division
    panel_num %= base_index; // Store the remainder in panel_num
  }

  return indices;
}

/**
 * Determine if a specific pixel is not within the bounds of a detector
 * panel.
 * @param fs_idx Index of the pixel in the fast-scan dimension of the panel.
 * @param ss_idx Index of the pixel in the slow-scan dimension of the panel.
 * @param fs_offset Offset value in fs dimension, e.g. if searching in ring.
 * @param ss_offset Offset value in ss dimension, e.g. if searching in ring.
 * @return result Boolean indicating if point/pixel is outside of panel.
 */
bool not_in_panel(int fs_idx, int ss_idx, int fs_offset, int ss_offset,
                  const DetData& img_data)
{
  bool out_left = (fs_idx + fs_offset < 0);
  bool out_right = (fs_idx + fs_offset >= img_data.fs_size);
  bool out_top = (ss_idx + ss_offset < 0);
  bool out_bottom = (ss_idx + ss_offset >= img_data.ss_size);
  return out_left || out_right || out_top || out_bottom;
}

/**
 * Holds information on the local background statistics in a ring around a
 * potential peak. The intensity, offset and snr are used to recenter and
 * reintegrate the peak.
 */
struct LocalPeakBkgnd {
  float max_intensity;
  float offset;
  float sigma;
};

/**
 * Calculate the local background statistics and signal-to-noise ratio in a
 * ring around a found peak. Pixels which could potentially be a part of
 * another peak are excluded from the calculation.
 *
 * @param com_fs_int Center of mass in the fast-scan axis of the panel.
 * @param com_ss_int Center of mass in the slow-scan axis of the panel.
 * @param com_idx Index of the center of mass in the 1D panel.
 * @param panel_num Number of the panel. With `com_idx` determines index in the data.
 * @param img_data Struct of Python data containing raw data, mask and radii map.
 * @param data_shape Information on the layout of the detector data.
 * @param rstats Radial binning information used for background calculations.
 * @param pfinter Internal peak-finding data, holding peak pixel indices.
 * @param options Algorithm options like the maximum number of peaks to find.
 * @return bkgnd Struct containing local background statistics.
 */
LocalPeakBkgnd search_in_ring(int com_fs_int, int com_ss_int, int com_idx,
                              int panel_num, const DetData& img_data,
                              RadialStats& rstats,
                              peakfinder_intern_data& pfinter, const HfOpts& options)
{
  const int ring_width = options.LocalBGRadius * 2;

  int np_sigma {};
  int np_counted {};
  float sum_i{};
  float sum_i_squared{};

  float background_max_i{};

  for (int ssj = -ring_width; ssj < ring_width; ++ssj) {
    for (int fsi = -ring_width; fsi < ring_width; ++fsi) {
      // Check that we're within the panel
      if (not_in_panel(com_fs_int, com_ss_int, fsi, ssj, img_data)) {
        continue;
      }

      float radius = sqrt(fsi*fsi + ssj*ssj);
      if (radius > ring_width) {
        continue;
      }

      int curr_fs = com_fs_int + fsi;
      int curr_ss = com_ss_int + ssj;

      int panel_offset = calc_panel_start_index(panel_num, img_data);
      int pidx = panel_offset + curr_fs + (curr_ss * img_data.fs_size);

      int curr_radius = static_cast<int>(rint(img_data.radius[pidx]));
      int curr_threshold = rstats.rthreshold[curr_radius];

      int curr_intensity = img_data.data[pidx];

      if (curr_intensity < curr_threshold
          && pfinter.pix_in_peak_map[pidx] == 0
          && img_data.mask[pidx])
      {
        np_sigma++;
        sum_i += curr_intensity;
        sum_i_squared += (curr_intensity * curr_intensity);

        if (curr_intensity > background_max_i) {
          background_max_i = curr_intensity;
        }
      }
      ++np_counted;
    }
  }

  float local_offset{};
  float local_sigma{};
  if (np_sigma) {
    local_offset = sum_i/np_sigma;
    local_sigma = sum_i_squared/np_sigma - (local_offset*local_offset);
    if (local_sigma >= 0) {
      local_sigma = sqrt(local_sigma);
    } else {
      local_sigma = 0.01;
    }
  } else {
    int local_radius = static_cast<int>(rint(img_data.radius[static_cast<int>(rint(com_idx))]));
    local_offset = rstats.roffset[local_radius];
    local_sigma = 0.01;
  }

  LocalPeakBkgnd bkgnd{background_max_i, local_offset, local_sigma};
  return bkgnd;
}

/**
 * Holds the intensity sums along the fast-scan (fs), slow-scan (ss) dimensions
 * as well as the total integrated intensity of a found peak. Used when
 * calculating the center-of-mass (COM) of the peak.
 */
struct com_sums {
  float fs{};
  float ss{};
  float intensity{};
};

/**
 * Determine pixels surrounding a peak pixel which are a part of the same peak.
 * Function is called repeatedly until no new peak pixels are found, or the
 * maximum number of pixels per peak (caller-defined) has been reached.
 *
 * @param peak_pix Index, [0, max_num_pix], of the peak pixel to search around.
 * @param panel_num Asic/panel number that is currently being analyzed.
 * @param img_data Struct of Python data containing raw data, mask and radii map.
 * @param rstats Radial binning information used for background calculations.
 * @param pfinter Internal peak-finding data, holding peak pixel indices.
 * @param options Algorithm options like the maximum number of peaks to find.
 * @param sums Peak intensity sums along fs/ss dimensions for COM calculation.
 */
int peak_search(int peak_pix, int panel_num, const DetData& img_data,
                RadialStats& rstats, peakfinder_intern_data& pfinter,
                const HfOpts& options, com_sums& sums)
{
  int num_pix_in_peak {}; // Return num_pix_in_peak
  const vector<int> search_fs {0, -1, 0, 1, -1, 1, -1, 0, 1};
  const vector<int> search_ss {0, -1, -1, -1, 0, 0, 1, 1, 1};

  int peak_fs = pfinter.infs[peak_pix];
  int peak_ss = pfinter.inss[peak_pix];

  for (int k = 0, search_n = 9; k < search_n; ++k) {
    int offset_fs = search_fs[k];
    int offset_ss = search_ss[k];

    // Calculate fs/ss indices for the current pixel
    int curr_fs = peak_fs + offset_fs;
    int curr_ss = peak_fs + offset_ss;

    // Move on if out of panel bounds
    if (not_in_panel(curr_fs, curr_ss, 0, 0, img_data)) {
      continue;
    }

    // Convert to a pixel index in the 1D data stream
    int panel_offset = calc_panel_start_index(panel_num, img_data);
    int pidx = panel_offset + curr_fs + (curr_ss * img_data.fs_size);

    int curr_radius = static_cast<int>(rint(img_data.radius[pidx]));
    int curr_threshold = rstats.rthreshold[pidx];

    // Check if above thresholds
    if (img_data.data[pidx] > curr_threshold
        && pfinter.pix_in_peak_map[pidx] == 0
        && img_data.mask[pidx])
    {
      int curr_intensity = img_data.data[pidx] - rstats.roffset[curr_radius];

      sums.intensity += curr_intensity;
      sums.fs += curr_intensity * static_cast<float>(curr_fs);
      sums.ss += curr_intensity * static_cast<float>(curr_ss);

      pfinter.inss[num_pix_in_peak] = curr_ss; // In panel indices
      pfinter.infs[num_pix_in_peak] = curr_fs; // In panel indices
      pfinter.pix_in_peak_map[pidx] = 1; // In 1D indices
      if (num_pix_in_peak < options.MaxPixCount) {
        // `pidx` would be in the 1D data stream indices -> for peak pix mask
        // Adjust by `panel_offset` for panel indices -> make easier for later
        pfinter.peak_pixels[num_pix_in_peak] = pidx - panel_offset;
      }
      ++num_pix_in_peak;
    }
  }
  return num_pix_in_peak;
}

/**
 * Find peaks on an individual panel/asic of a multi-panel detector.
 *

 * @param panel_number Number of the panel to process.
 * @param img_data Struct of Python data containing raw data, mask and radii map.
 * @param data_shape Information on the layout of the detector data.
 * @param rstats Radial binning information used for background calculations.
 * @param pfinter Internal peak-finding data, holding peak pixel indices.
 * @param pkdata Center-of-mass and info on peaks for the whole detector.
 * @param options Algorithm options like the maximum number of peaks to find.
 * @return peak_count The number of peaks found in the processed panel.
 */
int process_panel(int panel_number, const DetData& img_data,
                  RadialStats& rstats, peakfinder_intern_data& pfinter,
                  peakfinder_peak_data& pkdata, const HfOpts& options)
{
  int fs_size {img_data.fs_size};
  int ss_size {img_data.ss_size};

  int start_idx = calc_panel_start_index(panel_number, img_data);
  int peak_count{};

  for (int pix_ss = 1; pix_ss < ss_size - 1; ++pix_ss) {
    for (int pix_fs = 1; pix_fs < fs_size - 1; ++pix_fs) {
      int idx = start_idx + pix_ss*fs_size + pix_fs;

      int curr_rad = static_cast<int>(rint(img_data.radius[idx]));
      int curr_thresh = rstats.rthreshold[idx];

      /// Intensities and sums used for center of mass calculations
      com_sums sums{0.0, 0.0, 0.0};

      if (img_data.data[idx] > curr_thresh
          && pfinter.pix_in_peak_map[idx] == 0
          && img_data.mask[idx] != 0)
      {
        pfinter.infs[0] = pix_fs; // In panel indices
        pfinter.inss[0] = pix_ss; // In panel indices
        pfinter.peak_pixels[0] = idx - start_idx; // In panel indices
        int num_pix_in_peak {};
        int lt_num_pix_in_peak {};

        do {
          lt_num_pix_in_peak = num_pix_in_peak;

          for (int peak_pix = 0; peak_pix <= num_pix_in_peak; ++peak_pix) {
            num_pix_in_peak += peak_search(peak_pix, panel_number, img_data,
                                           rstats, pfinter, options,
                                           sums);
          }
        } while (lt_num_pix_in_peak != num_pix_in_peak);

        if (num_pix_in_peak < options.MinPixCount
            || num_pix_in_peak > options.MaxPixCount) {
          continue;
        }

        if (fabs(sums.intensity) < 1e-10) continue;

        // Calculate center mass from the initial search
        float peak_com_fs = sums.fs / fabs(sums.intensity); // Panel indices
        float peak_com_ss = sums.ss / fabs(sums.intensity); // Panel indices

        // Shouldn't need the conversions anymore, since working in panel indices
        int peak_com_fs_int = static_cast<int>(rint(peak_com_fs));
        int peak_com_ss_int = static_cast<int>(rint(peak_com_ss));

        int com_idx = peak_com_fs_int + peak_com_ss_int * fs_size; // Panel indices

        // Returns statistics on background intensity, offset and deviation
        // in the ring around the peak
        LocalPeakBkgnd bkgnd = search_in_ring(peak_com_fs_int, peak_com_ss_int,
                                              com_idx, panel_number, img_data,
                                              rstats, pfinter, options);

        /// Using the background statistics, reintegrate (and center) the peak
        /**********************************************************************/
        /// Integrated raw intensity of the peak
        float peak_raw_intensity{};
        /// Integrated background-adjusted intensity of the peak
        float peak_adjusted_intensity{};
        /// Maximum raw pixel intensity in the peak
        float max_intensity_raw{};
        /// Maximum adjusted pixel intensity in the peak
        float max_intensity_adjusted{};

        // Reset sums used for center-of-mass calculations
        sums.fs = 0;
        sums.ss = 0;

        for (int peak_idx = 0; // Pixel within peak
             peak_idx < num_pix_in_peak && peak_idx < options.MaxPixCount;
             ++peak_idx)
        {
          int curr_idx = pfinter.peak_pixels[peak_idx]; // Value in panel indices
          float raw_intensity = img_data.data[curr_idx + start_idx];
          float adjusted_intensity = raw_intensity - bkgnd.offset;

          peak_raw_intensity += raw_intensity;
          peak_adjusted_intensity += adjusted_intensity;

          // Already in panel indices (from peak_search)
          int curr_fs = curr_idx % fs_size;
          int curr_ss = curr_idx / fs_size;
          sums.fs += raw_intensity * static_cast<float>(curr_fs);
          sums.ss += raw_intensity * static_cast<float>(curr_ss);

          if (raw_intensity > max_intensity_raw) {
            max_intensity_raw = raw_intensity;
          }

          if (adjusted_intensity > max_intensity_adjusted) {
            max_intensity_adjusted = adjusted_intensity;
          }
        }

        // Some peaks are found with zero intensity - best to skip
        if (fabs(peak_raw_intensity) < 1e-10) {
          continue;
        }

        peak_com_fs = sums.fs / fabs(peak_raw_intensity);
        peak_com_ss = sums.ss / fabs(peak_raw_intensity);

        float peak_snr{};

        if (fabs(bkgnd.sigma) > 1e-10) {
          peak_snr = peak_adjusted_intensity / bkgnd.sigma;
        } else {
          peak_snr = 0;
        }

        // Is the maximum peak intensity enough above the local background?
        if (max_intensity_adjusted < bkgnd.max_intensity - bkgnd.offset) {
          continue;
        }

        // Is the center of mass on the panel.
        // We're using panel indices - so needs to be within (0, fs/ss)
        if (peak_com_fs <= 0 || peak_com_fs >= fs_size
            || peak_com_ss <= 0 || peak_com_ss >= ss_size)
        {
          continue;
        }

        // Final checks to see if peak meets critera - if so add to pkdata
        if (num_pix_in_peak >= options.MinPixCount
            && num_pix_in_peak <= options.MaxPixCount)
        {
          // Add peak pixels to mask to avoid double counting
          for (int peak_idx = 0;
               peak_idx < num_pix_in_peak && peak_idx < options.MaxPixCount;
               ++peak_idx)
          {
            // Need to convert back to 1D data indices
            int equivalent_1d_idx = pfinter.peak_pixels[peak_idx] + start_idx;
            pfinter.pix_in_peak_map[equivalent_1d_idx] = 2;
          }

          int peak_com_idx = static_cast<int>(peak_com_fs)
                             + static_cast<int>(peak_com_ss) * fs_size;
          pkdata.npix[peak_count] = num_pix_in_peak;
          pkdata.com_fs[peak_count] = peak_com_fs; // Float version - do we want int?
          pkdata.com_ss[peak_count] = peak_com_ss; // Same as ^ - should be like com_idx?
          pkdata.com_index[peak_count] = peak_com_idx;
          pkdata.panel_number[peak_count] = panel_number;
          pkdata.tot_i[peak_count] = peak_adjusted_intensity;
          pkdata.max_i[peak_count] = max_intensity_adjusted;
          pkdata.sigma[peak_count] = bkgnd.sigma;
          pkdata.snr[peak_count] = peak_snr;
        }
        ++peak_count;

        // Break out of all loops if peak_count greater than the max # of peaks
        // Written this way, it will add 1 peak to the data for the pathological
        // case where 0 or a negative number of peaks is input to the algorithm
        if (peak_count >= options.MaxNumPeaks)
        {
            break;
        }
      }
    }
    // Also break out of outer loop
    if (peak_count >= options.MaxNumPeaks) {
      break;
    }
  }

  // Return the number of peaks
  return peak_count;
}

/**
 * Run the peakfinding algorithm on a panel-by-panel basis.
 *
 * @param img_data Struct of Python data containing raw data, mask and radii map.
 * @param rstats Radial binning information used for background calculations.
 * @param pkdata Center-of-mass and info on peaks for the whole detector.
 * @param options Algorithm options like the maximum number of peaks to find.
 * @return num_found_peaks The number of peaks found.
 */
int peakfinder8_base(const DetData& img_data, RadialStats& rstats,
                     peakfinder_peak_data& pkdata, HfOpts& options) {
  int num_found_peaks = 0;
  peakfinder_intern_data pfinter(img_data.num_pixels, options.MaxNumPeaks);

  for (int panel = 0; panel < img_data.num_panels; ++panel) {
    num_found_peaks += process_panel(panel, img_data, rstats, pfinter,
                                     pkdata, options);
    // If you've already found enough peaks, break early
    if (num_found_peaks >= options.MaxNumPeaks) {
      break;
    }
  }
  return num_found_peaks;
}
} // Anonymous namespace

void allocatePeakList(tPeakList* peak, long NpeaksMax)
{
  peak->nPeaks = 0;
  peak->nPeaks_max = NpeaksMax;

  peak->peak_maxintensity = new float[NpeaksMax]{};
  peak->peak_totalintensity = new float[NpeaksMax]{};
  peak->peak_sigma = new float[NpeaksMax]{};
  peak->peak_snr = new float[NpeaksMax]{};
  peak->peak_npix = new float[NpeaksMax]{};
  peak->peak_com_x = new float[NpeaksMax]{};
  peak->peak_com_y = new float[NpeaksMax]{};
  peak->peak_com_index = new long[NpeaksMax]{};
  peak->peak_panel_number = new int[NpeaksMax]{};
  peak->memoryAllocated = 1;
}


void freePeakList(tPeakList peak)
{
  delete [] peak.peak_maxintensity;
  delete [] peak.peak_totalintensity;
  delete [] peak.peak_sigma;
  delete [] peak.peak_snr;
  delete [] peak.peak_npix;
  delete [] peak.peak_com_x;
  delete [] peak.peak_com_y;
  delete [] peak.peak_com_index;
  delete [] peak.peak_panel_number;
  peak.memoryAllocated = 0;
}

int peakfinder8(tPeakList* peaklist, float* data, char* mask, float* pix_radius,
                const vector<int>& data_shape, float ADCthresh,
                float hitfinderMinSNR, long hitfinderMinPixCount,
                long hitfinderMaxPixCount, long hitfinderLocalBGRadius)
{
  int max_num_peaks = peaklist->nPeaks_max;

  // Bundle the data, detector shape, mask, and radii mapping in single struct
  DetData img_data(data, mask, pix_radius, data_shape);

  int num_rad_bins = compute_num_radial_bins(img_data.num_pixels, pix_radius);
  RadialStats rstats(num_rad_bins);

  peakfinder_peak_data pkdata(max_num_peaks);

  HfOpts opts(ADCthresh, hitfinderMinSNR, hitfinderMinPixCount,
              hitfinderMaxPixCount, hitfinderLocalBGRadius, max_num_peaks);

  rstats.compute_bins_and_stats(img_data, opts);

  int num_found_peaks = peakfinder8_base(img_data, rstats, pkdata, opts);

  // Return something if there is an error?
  // How should we do the exception handling?

  int peaks_to_add = num_found_peaks;

  if ( num_found_peaks > max_num_peaks ) {
    peaks_to_add = max_num_peaks;
  }

  for (int pki = 0 ; pki<peaks_to_add ; pki++ ) {
    peaklist->peak_maxintensity[pki] = pkdata.max_i[pki];
    peaklist->peak_totalintensity[pki] = pkdata.tot_i[pki];
    peaklist->peak_sigma[pki] = pkdata.sigma[pki];
    peaklist->peak_snr[pki] = pkdata.snr[pki];
    peaklist->peak_npix[pki] = pkdata.npix[pki];
    peaklist->peak_com_x[pki] = pkdata.com_fs[pki];
    peaklist->peak_com_y[pki] = pkdata.com_ss[pki];
    peaklist->peak_com_index[pki] = pkdata.com_index[pki];
    peaklist->peak_panel_number[pki] = pkdata.panel_number[pki];
  }

  peaklist->nPeaks = peaks_to_add;
  return 0;
}
