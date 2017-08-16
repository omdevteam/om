from libc.stdint cimport uint32_t, uint16_t, uint8_t

cdef extern from "detectorRawFormat.h":
    ctypedef struct detectorRawFormat_t:
        uint16_t asic_nx
        uint16_t asic_ny
        uint8_t nasics_x
        uint8_t nasics_y

        uint16_t pix_nx
        uint16_t pix_ny
        uint32_t pix_nn

cdef extern from "adaptions/onda/pythonWrapperTypes.h":
    ctypedef struct detectorGeometryMatrix_pythonWrapper_t:
        float* detectorGeometryMatrix_x
        float* detectorGeometryMatrix_y

cdef extern from "adaptions/onda/radialBackgroundSubtraction_wrapper.h":
    ctypedef struct radialRankFilter_constantArguments_t:
        pass

    ctypedef struct radialRankFilter_accuracyConstants_pythonWrapper_t:
        uint32_t minValuesPerBin
        uint32_t minBinWidth

        uint32_t maxConsideredValuesPerBin

        uint8_t* detectorsToConsiderSubscripts_x
        uint8_t* detectorsToConsiderSubscripts_y
        uint16_t detectorsToConsiderCount

        uint8_t* detectorsToCorrectSubscripts_x
        uint8_t* detectorsToCorrectSubscripts_y
        uint16_t detectorsToCorrectCount

        float rank


    radialRankFilter_constantArguments_t precomputeRadialRankFilterConstantArguments(const uint8_t* mask, const float* detectorGeometryRadiusMatrix,
            const detectorRawFormat_t& detectorRawFormat, const radialRankFilter_accuracyConstants_pythonWrapper_t& accuracyConstants_pythonWrapper,
            detectorGeometryMatrix_pythonWrapper_t detectorGeometryMatrix_pythonWrapper)

    void applyRadialRankFilter(float* data, radialRankFilter_constantArguments_t radialRankFilter_constantArguments)

    void freePrecomputeRadialRankFilterConstants(radialRankFilter_constantArguments_t radialRankFilter_constantArguments)

cdef extern from "adaptions/onda/streakFinder_wrapper.h":
    ctypedef struct streakFinder_constantArguments_t:
        pass

    ctypedef struct streakFinder_accuracyConstants_pythonWrapper_t:
        uint8_t filterLength;
        uint8_t minFilterLength;
        float filterStep;

        float sigmaFactor;
        uint8_t streakElongationMinStepsCount;
        float streakElongationRadiusFactor;
        uint8_t streakPixelMaskRadius;

        uint16_t* pixelsToCheck_x;
        uint16_t* pixelsToCheck_y;
        uint16_t pixelsToCheckCount;

        uint16_t* backgroundEstimationRegions_upperLeftCorner_x;
        uint16_t* backgroundEstimationRegions_upperLeftCorner_y;
        uint16_t* backgroundEstimationRegions_lowerRightCorner_x;
        uint16_t* backgroundEstimationRegions_lowerRightCorner_y;
        uint16_t backgroundEstimationRegionsCount;


    streakFinder_constantArguments_t precomputeStreakFinderConstantArguments(
            streakFinder_accuracyConstants_pythonWrapper_t streakFinder_accuracyConstants,
            detectorRawFormat_t detectorRawFormat,
            detectorGeometryMatrix_pythonWrapper_t detectorGeometryMatrix_python,
            const uint8_t *mask);

    void freePrecomputedStreakFinderConstantArguments(streakFinder_constantArguments_t streakfinder_constant_arguments);

    void streakFinder(float* data_linear, streakFinder_constantArguments_t streakFinderConstantArguments);

cdef extern from "mask.h":
    void mergeMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat)
    void mergeMaskIntoData(float * data, const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat)

    void getMaskFromMergedMaskInData(const float * data, uint8_t * mask, const detectorRawFormat_t& detectorRawFormat)

cdef extern from "peakList.h":
    ctypedef struct peakList_t:
        int memoryAllocated
        long peakCount
        long maxPeakCount

        float *maxIntensity       # Maximum intensity in peak
        float *totalIntensity     # Integrated intensity in peak
        float *sigmaBackground    # Standard deviation of the background
        float *snr                # Signal-to-noise ratio of peak
        float *pixelCount         # Number of pixels in peak
        float *centerOfMass_rawX  # peak center of mass x (in raw layout)
        float *centerOfMass_rawY  # peak center of mass y (in raw layout)

    int allocatePeakList(peakList_t* peakList, int maxPeakCount);
    void freePeakList(peakList_t peakList);

cdef extern from "peakFinder9.h":
    ctypedef struct peakFinder9_accuracyConstants_t:
        float sigmaFactorBiggestPixel              # small factor leads to a slow algorithm
        float sigmaFactorPeakPixel                 # should be smaller or equal to sigmaFactorBiggestPixel
        float sigmaFactorWholePeak                 # should be bigger or equal to sigmaFactorBiggestPixel
        float minimumSigma                         # to not find false peaks in very dark noise free regions
        float minimumPeakOversizeOverNeighbours    # for faster processing
        uint8_t windowRadius    # radius of the peak search window (incl. border). Must be >= 2

    uint32_t peakFinder9(const float* data_linear, const peakFinder9_accuracyConstants_t& accuracyConstants,
            const detectorRawFormat_t& detectorRawFormat, peakList_t& peakList);

    uint32_t peakFinder9_onePanel(const float* data_linear, uint32_t asic_x, uint32_t asic_y, const peakFinder9_accuracyConstants_t& accuracyConstants,
            const detectorRawFormat_t& detectorRawFormat, peakList_t& peakList);

