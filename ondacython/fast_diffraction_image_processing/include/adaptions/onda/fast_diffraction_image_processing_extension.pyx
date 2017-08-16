import numpy as np
cimport fast_diffraction_image_processing_cpp_extension as cpp
from libc.stdint cimport uint32_t, uint16_t, uint8_t

cdef class FastDiffractionImageProcessing:
    cdef cpp.detectorRawFormat_t _detector_raw_format

    cdef cpp.radialRankFilter_constantArguments_t _radial_rank_filter__constant_arguments
    cdef bint _radial_rank_filter__constant_arguments__allocated

    cdef cpp.streakFinder_constantArguments_t _streak_finder__constant_arguments
    cdef bint _streak_finder__constant_arguments__allocated

    cdef float[:,::1] _x_map, _y_map
    cdef cpp.detectorGeometryMatrix_pythonWrapper_t _detector_geometry_matrix

    cdef uint8_t[:,::1] _global_mask
    cdef uint8_t[:,::1] _peak_finding_mask
    cdef float[:,::1] _data

    cdef cpp.peakList_t _peak_list
    cdef bint _peak_list__allocated

    def __cinit__(self,
        uint16_t asic_nx, uint16_t asic_ny, uint8_t nasics_x, uint8_t nasics_y,
        float[:,::1] x_map,
        float[:,::1] y_map,
        uint8_t[:,::1] global_mask,
        uint8_t[:,::1] peak_finding_mask
        ):
        self._set_detector_raw_format(asic_nx, asic_ny, nasics_x, nasics_y)
        self._set_detector_geometry_matrix(x_map, y_map)
        self.set_global_mask(global_mask)
        self.set_peak_finding_mask(peak_finding_mask)
        self._data = np.zeros(shape=(global_mask.shape[0], global_mask.shape[1]) , dtype='float32', order='C') #shape=mask.shape[0:2] does not work

        self._radial_rank_filter__constant_arguments__allocated = False
        self._streak_finder__constant_arguments__allocated = False

    def _set_detector_raw_format(self, uint16_t asic_nx, uint16_t asic_ny, uint8_t nasics_x, uint8_t nasics_y):
        self._detector_raw_format.asic_nx = asic_nx
        self._detector_raw_format.asic_ny = asic_ny
        self._detector_raw_format.nasics_x = nasics_x
        self._detector_raw_format.nasics_y = nasics_y
        self._detector_raw_format.pix_nx = asic_nx*nasics_x
        self._detector_raw_format.pix_ny = asic_ny*nasics_y
        self._detector_raw_format.pix_nn = asic_nx*nasics_x * asic_ny*nasics_y

    def _set_detector_geometry_matrix(self,
                                      float[:,::1] x_map,
                                      float[:,::1] y_map
                                      ):
        self._x_map = x_map.copy()
        self._y_map = y_map.copy()

        self._detector_geometry_matrix.detectorGeometryMatrix_x = &self._x_map[0,0]
        self._detector_geometry_matrix.detectorGeometryMatrix_y = &self._y_map[0,0]

    def set_data(self, float[:,::1] data):
        cpp.mergeMaskAndDataIntoDataCopy(&data[0,0], &self._data[0,0], &self._global_mask[0,0], self._detector_raw_format)

    def precompute_streak_finder(self,
                                 uint8_t filter_length,
                                 uint8_t min_filter_length,
                                 float filter_step,
                                 float sigma_factor,
                                 uint8_t streak_elongation_min_steps_count,
                                 float streak_elongation_radius_factor,
                                 uint8_t streak_pixel_mask_radius,
                                 uint16_t[::1] pixels_to_check_x,
                                 uint16_t[::1] pixels_to_check_y,
                                 uint16_t[::1] background_estimation_regions__upper_left_corner_x,
                                 uint16_t[::1] background_estimation_regions__upper_left_corner_y,
                                 uint16_t[::1] background_estimation_regions__lower_right_corner_x,
                                 uint16_t[::1] background_estimation_regions__lower_right_corner_y,
                                 ):
        print('start precomputing streakFinder')

        if(self._streak_finder__constant_arguments__allocated):
            cpp.freePrecomputedStreakFinderConstantArguments(self._streak_finder__constant_arguments)

        cdef cpp.streakFinder_accuracyConstants_pythonWrapper_t ac
        ac.filterLength = filter_length
        ac.minFilterLength = min_filter_length
        ac.filterStep = filter_step

        ac.sigmaFactor = sigma_factor
        ac.streakElongationMinStepsCount = streak_elongation_min_steps_count
        ac.streakElongationRadiusFactor = streak_elongation_radius_factor
        ac.streakPixelMaskRadius = streak_pixel_mask_radius

        ac.pixelsToCheck_x = &pixels_to_check_x[0]
        ac.pixelsToCheck_y = &pixels_to_check_y[0]
        ac.pixelsToCheckCount = pixels_to_check_y.size

        ac.backgroundEstimationRegions_upperLeftCorner_x = &background_estimation_regions__upper_left_corner_x[0]
        ac.backgroundEstimationRegions_upperLeftCorner_y = &background_estimation_regions__upper_left_corner_y[0]
        ac.backgroundEstimationRegions_lowerRightCorner_x = &background_estimation_regions__lower_right_corner_x[0]
        ac.backgroundEstimationRegions_lowerRightCorner_y = &background_estimation_regions__lower_right_corner_y[0]
        ac.backgroundEstimationRegionsCount = background_estimation_regions__upper_left_corner_x.size

        self._streak_finder__constant_arguments = cpp.precomputeStreakFinderConstantArguments(
            ac,
            self._detector_raw_format,
            self._detector_geometry_matrix,
            &self._global_mask[0,0])

        self._streak_finder__constant_arguments__allocated = True

        print('finished precomputing streakFinder')

    def precompute_background_subtraction(self,
        float[:,::1] r_map,
        uint32_t min_values_per_bin,
        uint32_t min_bin_width,
        uint32_t max_considered_values_per_bin,
        uint8_t[::1] detectors_to_consider_subscripts_x,
        uint8_t[::1] detectors_to_consider_subscripts_y,
        uint8_t[::1] detectors_to_correct_subscripts_x,
        uint8_t[::1] detectors_to_correct_subscripts_y,
        float rank
        ):
        print('start precomputing background subtraction')

        if(self._radial_rank_filter__constant_arguments__allocated):
            cpp.freePrecomputeRadialRankFilterConstants(self._radial_rank_filter__constant_arguments)

        cdef cpp.radialRankFilter_accuracyConstants_pythonWrapper_t ac
        ac.minValuesPerBin = min_values_per_bin
        ac.minBinWidth = min_bin_width
        ac.maxConsideredValuesPerBin = max_considered_values_per_bin
        ac.detectorsToConsiderSubscripts_x = &detectors_to_consider_subscripts_x[0]
        ac.detectorsToConsiderSubscripts_y = &detectors_to_consider_subscripts_y[0]
        ac.detectorsToConsiderCount = detectors_to_consider_subscripts_x.size
        ac.detectorsToCorrectSubscripts_x = &detectors_to_correct_subscripts_x[0]
        ac.detectorsToCorrectSubscripts_y = &detectors_to_correct_subscripts_y[0]
        ac.detectorsToCorrectCount = detectors_to_correct_subscripts_x.size
        ac.rank = rank

        self._radial_rank_filter__constant_arguments = cpp.precomputeRadialRankFilterConstantArguments(
            &self._global_mask[0,0], &r_map[0,0], self._detector_raw_format, ac, self._detector_geometry_matrix)

        self._radial_rank_filter__constant_arguments__allocated = True
        print('finished precomputing background subtraction\n\n')

    def precompute_peak_finder9(self, uint32_t max_peak_count):
        if(self._peak_list__allocated):
            cpp.freePeakList(self._peak_list)

        cdef int memoryAllocationErrorFlag
        memoryAllocationErrorFlag = cpp.allocatePeakList(&self._peak_list, max_peak_count)

        self._peak_list__allocated = True

        if(memoryAllocationErrorFlag):
            raise MemoryError()

    def apply_peak_finder9(self,
        float sigma_factor_biggest_pixel,              # small factor leads to a slow algorithm
        float sigma_factor_peak_pixel,                 # should be smaller or equal to sigmaFactorBiggestPixel
        float sigma_factor_whole_peak,                 # should be bigger or equal to sigmaFactorBiggestPixel
        float minimum_sigma,                         # to not find false peaks in very dark noise free regions
        float minimum_peak_oversize_over_neighbours,    # for faster processing
        uint8_t window_radius
        ):

        cpp.mergeMaskIntoData(&self._data[0,0], &self._peak_finding_mask[0,0], self._detector_raw_format)

        cdef cpp.peakFinder9_accuracyConstants_t ac
        ac.sigmaFactorBiggestPixel = sigma_factor_biggest_pixel
        ac.sigmaFactorPeakPixel = sigma_factor_peak_pixel
        ac.sigmaFactorWholePeak = sigma_factor_whole_peak
        ac.minimumSigma = minimum_sigma
        ac.minimumPeakOversizeOverNeighbours = minimum_peak_oversize_over_neighbours
        ac.windowRadius = window_radius

        self._peak_list.peakCount = 0
        cdef uint32_t peakCount = cpp.peakFinder9(&self._data[0,0], ac, self._detector_raw_format, self._peak_list)

        max_intensity = np.zeros(peakCount, dtype=float)      # Maximum intensity in peak
        total_intensity = np.zeros(peakCount, dtype=float)    # Integrated intensity in peak
        sigma_background = np.zeros(peakCount, dtype=float)   # Standard deviation of the background
        snr = np.zeros(peakCount, dtype=float)               # Signal-to-noise ratio of peak
        pixel_count = np.zeros(peakCount, dtype=float)        # Number of pixels in peak
        center_of_mass__raw_x = np.zeros(peakCount, dtype=float) # peak center of mass x (in raw layout)
        center_of_mass__raw_y = np.zeros(peakCount, dtype=float) # peak center of mass y (in raw layout)

        for i in range(0, peakCount):
            max_intensity[i] = self._peak_list.maxIntensity[i]
            total_intensity[i] = self._peak_list.totalIntensity[i]
            sigma_background[i] = self._peak_list.sigmaBackground[i]
            snr[i] = self._peak_list.snr[i]
            pixel_count[i] = self._peak_list.pixelCount[i]
            center_of_mass__raw_x[i] = self._peak_list.centerOfMass_rawX[i]
            center_of_mass__raw_y[i] = self._peak_list.centerOfMass_rawY[i]

        return (max_intensity, total_intensity, sigma_background, snr, pixel_count, center_of_mass__raw_x, center_of_mass__raw_y)

    def get_data(self):
        return np.asarray(self._data)

    def set_global_mask(self, uint8_t[:,::1] mask):
        self._global_mask = mask.copy()
        # create sparse mask if mask is sparse

    def set_peak_finding_mask(self, uint8_t[:,::1] mask):
        self._peak_finding_mask = mask.copy()
        # create sparse mask if mask is sparse. Need only to take diff to _global_mask

    def get_computed_mask(self):
        cdef uint8_t[:,::1] mask = np.zeros(shape=(self._global_mask.shape[0], self._global_mask.shape[1]) , dtype='uint8', order='C') #shape=_global_mask.shape[0:2] does not work
        cpp.getMaskFromMergedMaskInData(&self._data[0,0], &mask[0,0], self._detector_raw_format)
        return np.asarray(mask)

    def apply_streak_finder(self):
        cpp.streakFinder(&self._data[0,0], self._streak_finder__constant_arguments)

    def apply_radial_rank_filter(self):
        cpp.applyRadialRankFilter(&self._data[0,0], self._radial_rank_filter__constant_arguments)

    def __dealloc__(self):
        if(self._radial_rank_filter__constant_arguments__allocated):
            cpp.freePrecomputeRadialRankFilterConstants(self._radial_rank_filter__constant_arguments)

        if(self._streak_finder__constant_arguments__allocated):
            cpp.freePrecomputedStreakFinderConstantArguments(self._streak_finder__constant_arguments)

        if(self._peak_list__allocated):
            cpp.freePeakList(self._peak_list)
