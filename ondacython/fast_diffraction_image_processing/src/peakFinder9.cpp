/*
 * peakFinder.cpp
 *
 *  Created on: 12.12.2015
 *      Author: Yaro
 */

#include <peakFinder9.h>
#include <cmath>
#include <cfloat>
#include <stdexcept>

typedef struct {
    float totalMass;
    float weightedCoordinatesSummed_x, weightedCoordinatesSummed_y;
    float biggestPixelMass;
    uint8_t pixelCount;
} peakFinder9_intermediatePeakStatistics_t;

static inline bool isPixelCandidateForPeak(const float* data_linear, const detectorRawFormat_t& detectorRawFormat,
        const peakFinder9_accuracyConstants_t& accuracyConstants, uint16_t x, uint16_t y);
static inline void computeNormalDistributionParameters(const float* data_linear, const detectorRawFormat_t& detectorRawFormat,
        const peakFinder9_accuracyConstants_t& accuracyConstants, uint16_t x, uint16_t y, float* mean, float* sigma);
static inline void analysePeak(uint16_t x, uint16_t y, float thresholdNeighbourPixel, const float* data_linear,
        const detectorRawFormat_t& detectorRawFormat, const peakFinder9_accuracyConstants_t& accuracyConstants,
        peakFinder9_intermediatePeakStatistics_t& intermediatePeakStatistics);
static inline void analyseRingAroundPixel(uint8_t radius, float thresholdNeighbourPixel, uint16_t x, uint16_t y, const float* data_linear,
        const detectorRawFormat_t& detectorRawFormat, peakFinder9_intermediatePeakStatistics_t& intermediatePeakStatistics, bool* newPixelFound);
static inline void addPixelTointermediatePeakStatistics(peakFinder9_intermediatePeakStatistics_t& intermediatePeakStatistics, uint16_t x,
        uint16_t y, float pixelValue);
static inline void savePeak(float sigmaBackground, float meanBackground, const peakFinder9_intermediatePeakStatistics_t& intermediatePeakStatistics,
        const detectorRawFormat_t& detectorRawFormat, peakList_t& peakList);

uint32_t peakFinder9(const float* data_linear, const peakFinder9_accuracyConstants_t& accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat, peakList_t& peakList)
{
    uint32_t peakCount = 0;

    if (accuracyConstants.windowRadius < 2) {
        throw std::invalid_argument("window radius must be at least 2");
    }

    for (uint32_t asic_y = 0; asic_y < detectorRawFormat.nasics_y; ++asic_y) {
        for (uint32_t asic_x = 0; asic_x < detectorRawFormat.nasics_x; ++asic_x) {
            peakCount += peakFinder9_onePanel(data_linear, asic_x, asic_y, accuracyConstants, detectorRawFormat, peakList);
        }
    }

    return peakCount;
}

//returns number of peaks found
uint32_t peakFinder9_onePanel(const float* data_linear, uint32_t asic_x, uint32_t asic_y, const peakFinder9_accuracyConstants_t& accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat, peakList_t& peakList)
{
    uint16_t x_asicStart = asic_x * detectorRawFormat.asic_nx;
    uint16_t y_asicStart = asic_y * detectorRawFormat.asic_ny;

    const float (*data)[detectorRawFormat.pix_nx] = (const float (*)[detectorRawFormat.pix_nx]) data_linear; //using #define instead of pix_nx gives a tiny performance boost

    uint16_t windowRadius = accuracyConstants.windowRadius;
    uint32_t peakCount = 0;

#if PEAK_FINDER_9__DOUBLE_BACKGROUND_ESTIMATION_WINDOW
    for (uint16_t y = y_asicStart + (windowRadius + 1); y < y_asicStart + detectorRawFormat.asic_ny - (windowRadius + 1); ++y) {
        for (uint16_t x = x_asicStart + (windowRadius + 1); x < x_asicStart + detectorRawFormat.asic_nx - (windowRadius + 1); ++x) {
#else
    for (uint16_t y = y_asicStart + windowRadius; y < y_asicStart + detectorRawFormat.asic_ny - windowRadius; ++y) {
        for (uint16_t x = x_asicStart + windowRadius; x < x_asicStart + detectorRawFormat.asic_nx - windowRadius; ++x) {
#endif
            if (isPixelCandidateForPeak(data_linear, detectorRawFormat, accuracyConstants, x, y)) {
                float meanBackground, sigmaBackground;
                computeNormalDistributionParameters(data_linear, detectorRawFormat, accuracyConstants, x, y, &meanBackground, &sigmaBackground);

                float thresholdSinglePixel = meanBackground + accuracyConstants.sigmaFactorBiggestPixel * sigmaBackground;
                if (data[y][x] > thresholdSinglePixel) {
                    float thresholdNeighbourPixel = meanBackground + accuracyConstants.sigmaFactorPeakPixel * sigmaBackground;
                    peakFinder9_intermediatePeakStatistics_t intermediatePeakStatistics;
                    analysePeak(x, y, thresholdNeighbourPixel, data_linear, detectorRawFormat, accuracyConstants, intermediatePeakStatistics);

                    float thresholdWholePeak = meanBackground + accuracyConstants.sigmaFactorWholePeak * sigmaBackground;
                    if (intermediatePeakStatistics.totalMass > thresholdWholePeak) {
                        savePeak(sigmaBackground, meanBackground, intermediatePeakStatistics, detectorRawFormat, peakList);
                        peakCount++;
                    }
                }
            }
        }
    }

    return peakCount;
}

//writing this function directly into peakFinder9_oneDetector saves some milliseconds
static inline bool isPixelCandidateForPeak(const float* data_linear, const detectorRawFormat_t& detectorRawFormat,
        const peakFinder9_accuracyConstants_t& accuracyConstants, uint16_t x, uint16_t y)
{

    const float (*data)[detectorRawFormat.pix_nx] = (float (*)[detectorRawFormat.pix_nx]) data_linear;

    if (data[y][x] == -FLT_MAX) {
        return false;
    }

    uint16_t windowRadius = accuracyConstants.windowRadius;

    float adjustedPixel = data[y][x] - accuracyConstants.minimumPeakOversizeOverNeighbours;

    if (adjustedPixel > data[y][x - windowRadius] &&
            adjustedPixel > data[y][x + windowRadius] &&
            adjustedPixel > data[y - 1][x - windowRadius] &&
            adjustedPixel > data[y - 1][x + windowRadius] &&
            adjustedPixel > data[y - windowRadius][x - 1] &&
            adjustedPixel > data[y - windowRadius][x] &&
            adjustedPixel > data[y - windowRadius][x + 1] &&
            adjustedPixel > data[y + 1][x - windowRadius] &&
            adjustedPixel > data[y + 1][x + windowRadius] &&
            adjustedPixel > data[y + windowRadius][x - 1] &&
            adjustedPixel > data[y + windowRadius][x] &&
            adjustedPixel > data[y + windowRadius][x + 1] &&
            data[y][x] > data[y - 1][x - 1] &&
            data[y][x] > data[y - 1][x] &&
            data[y][x] > data[y - 1][x + 1] &&
            data[y][x] > data[y][x - 1] &&
            data[y][x] > data[y][x + 1] &&
            data[y][x] > data[y + 1][x - 1] &&
            data[y][x] > data[y + 1][x] &&
            data[y][x] > data[y + 1][x + 1]) {
        return true;
    } else {
        return false;
    }
}

//theoretically best true true, but need to test!
#define COMPUTE_ON_THE_FLY              false
#define ONE_PASS_COMPUTATION_METHOD      true

static inline void computeNormalDistributionParameters(const float* data_linear, const detectorRawFormat_t& detectorRawFormat,
        const peakFinder9_accuracyConstants_t& accuracyConstants, uint16_t x, uint16_t y, float* mean, float* sigma)
{

    const float (*data)[detectorRawFormat.pix_nx] = (float (*)[detectorRawFormat.pix_nx]) data_linear;
    uint16_t windowRadius = accuracyConstants.windowRadius;

#if COMPUTE_ON_THE_FLY && !ONE_PASS_COMPUTATION_METHOD
#warning "Computing on the fly makes no sense for naive computation method!"
#endif

#if COMPUTE_ON_THE_FLY && ONE_PASS_COMPUTATION_METHOD
//compute on the fly (only for changed computation method)
    double sum = 0;
    double sumOfSquares = 0;
    uint8_t validPixelCount = 0;

//compute mean and sigma from border
//upper border
    for (const float* currentPixel = &data[y - windowRadius][x - 2]; currentPixel <= &data[y - windowRadius][x + 2]; ++currentPixel) {
        if (*currentPixel != -FLT_MAX) {
            float pixelValue = *currentPixel;
            sumOfSquares += pixelValue * pixelValue;
            sum += pixelValue;
            validPixelCount++;
        }
    }

//left and right border
    for (int_fast8_t i = -2; i <= 2; ++i) {
        if (data[y + i][x - windowRadius] != -FLT_MAX) {
            float pixelValue = data[y + i][x - windowRadius];
            sumOfSquares += pixelValue * pixelValue;
            sum += pixelValue;
            validPixelCount++;
        }

        if (data[y + i][x + windowRadius] != -FLT_MAX) {
            float pixelValue = data[y + i][x + windowRadius];
            sumOfSquares += pixelValue * pixelValue;
            sum += pixelValue;
            validPixelCount++;
        }
    }

//lower border
    for (const float* currentPixel = &data[y + windowRadius][x - 2]; currentPixel <= &data[y + windowRadius][x + 2]; ++currentPixel) {
        if (*currentPixel != -FLT_MAX) {
            float pixelValue = *currentPixel;
            sumOfSquares += pixelValue * pixelValue;
            sum += pixelValue;
            validPixelCount++;
        }
    }

#ifdef PEAK_FINDER_9__DOUBLE_BACKGROUND_ESTIMATION_WINDOW
    //compute mean and sigma from border and border+1 (thus needs one more pixel at asic border!)
    //upper border
    for (const float* currentPixel = &data[y - (windowRadius + 1)][x - 2]; currentPixel <= &data[y - (windowRadius + 1)][x + 2]; ++currentPixel) {
        if (*currentPixel != -FLT_MAX) {
            float pixelValue = *currentPixel;
            sumOfSquares += pixelValue * pixelValue;
            sum += pixelValue;
            validPixelCount++;
        }
    }

    //left and right border
    for (int_fast8_t i = -2; i <= 2; ++i) {
        if (data[y + i][x - (windowRadius + 1)] != -FLT_MAX) {
            float pixelValue = data[y + i][x - (windowRadius + 1)];
            sumOfSquares += pixelValue * pixelValue;
            sum += pixelValue;
            validPixelCount++;
        }

        if (data[y + i][x + (windowRadius + 1)] != -FLT_MAX) {
            float pixelValue = data[y + i][x + (windowRadius + 1)];
            sumOfSquares += pixelValue * pixelValue;
            sum += pixelValue;
            validPixelCount++;
        }
    }

    //lower border
    for (const float* currentPixel = &data[y + (windowRadius + 1)][x - 2]; currentPixel <= &data[y + (windowRadius + 1)][x + 2]; ++currentPixel) {
        if (*currentPixel != -FLT_MAX) {
            float pixelValue = *currentPixel;
            sumOfSquares += pixelValue * pixelValue;
            sum += pixelValue;
            validPixelCount++;
        }
    }
#endif

    if (validPixelCount < 2) {
        *mean = FLT_MAX;
        *sigma = FLT_MAX;
    } else {
        *mean = (float) sum / validPixelCount;
        float computedSigma = sqrt((float) sumOfSquares / (validPixelCount - 1) - (*mean) * (*mean) * validPixelCount / (float) (validPixelCount - 1));
        *sigma = fmax(computedSigma, accuracyConstants.minimumSigma);
    }
#else
//first save everything, then compute
    float background[20 * 2];
    uint8_t validPixelCount = 0;

//compute mean and sigma from border
//upper border
    for (const float* currentPixel = &data[y - windowRadius][x - 2]; currentPixel <= &data[y - windowRadius][x + 2]; ++currentPixel) {
        if (*currentPixel != -FLT_MAX) {
            background[validPixelCount++] = *currentPixel;
        }
    }

//left and right border
    for (int_fast8_t i = -2; i <= 2; ++i) {
        if (data[y + i][x - windowRadius] != -FLT_MAX) {
            background[validPixelCount++] = data[y + i][x - windowRadius];
        }

        if (data[y + i][x + windowRadius] != -FLT_MAX) {
            background[validPixelCount++] = data[y + i][x + windowRadius];
        }
    }

//lower border
    for (const float* currentPixel = &data[y + windowRadius][x - 2]; currentPixel <= &data[y + windowRadius][x + 2]; ++currentPixel) {
        if (*currentPixel != -FLT_MAX) {
            background[validPixelCount++] = *currentPixel;
        }
    }

#ifdef PEAK_FINDER_9__DOUBLE_BACKGROUND_ESTIMATION_WINDOW
    //compute mean and sigma from border and border+1 (thus needs one more pixel at asic border!)
    //upper border
    for (const float* currentPixel = &data[y - (windowRadius + 1)][x - 2]; currentPixel <= &data[y - (windowRadius + 1)][x + 2]; ++currentPixel) {
        if (*currentPixel != -FLT_MAX) {
            background[validPixelCount++] = *currentPixel;
        }
    }

    //left and right border
    for (int_fast8_t i = -2; i <= 2; ++i) {
        if (data[y + i][x - (windowRadius + 1)] != -FLT_MAX) {
            background[validPixelCount++] = data[y + i][x - (windowRadius + 1)];
        }

        if (data[y + i][x + (windowRadius + 1)] != -FLT_MAX) {
            background[validPixelCount++] = data[y + i][x + (windowRadius + 1)];
        }
    }

    //lower border
    for (const float* currentPixel = &data[y + (windowRadius + 1)][x - 2]; currentPixel <= &data[y + (windowRadius + 1)][x + 2]; ++currentPixel) {
        if (*currentPixel != -FLT_MAX) {
            background[validPixelCount++] = *currentPixel;
        }
    }
#endif

#endif

    if (validPixelCount < 4) {
        *mean = FLT_MAX;
        *sigma = FLT_MAX;
    } else {
#if ONE_PASS_COMPUTATION_METHOD
#if !COMPUTE_ON_THE_FLY
        double sum = 0;  //can be float, since it can easily be stored in 24bit!
        double sumOfSquares = 0;
        for (uint8_t i = 0; i < validPixelCount; ++i) {
            sum += background[i];
            sumOfSquares += background[i] * background[i];
        }
#endif
        *mean = (float) sum / validPixelCount;
        float computedSigma = sqrt(((float) sumOfSquares - (*mean) * (*mean) * validPixelCount) / (float) (validPixelCount - 1));
        *sigma = std::max(computedSigma, accuracyConstants.minimumSigma);
#else
        //naive computation method
        double sum = 0;
        for (uint8_t i = 0; i < validPixelCount; ++i) {
            sum += background[i];
        }
        *mean = sum / validPixelCount;

        double squaredDeviationSum = 0;
        for (uint8_t i = 0; i < validPixelCount; ++i) {
            double deviation = *mean - background[i];
            squaredDeviationSum += deviation * deviation;
        }
        *sigma = std::max(sqrtf((float) squaredDeviationSum / (validPixelCount - 1)), accuracyConstants.minimumSigma);
#endif
    }
}

static inline void analysePeak(uint16_t x, uint16_t y, float thresholdNeighbourPixel, const float* data_linear,
        const detectorRawFormat_t& detectorRawFormat, const peakFinder9_accuracyConstants_t& accuracyConstants,
        peakFinder9_intermediatePeakStatistics_t& intermediatePeakStatistics)
{

    const float (*data)[detectorRawFormat.pix_nx] = (float (*)[detectorRawFormat.pix_nx]) data_linear;

    intermediatePeakStatistics.totalMass = data[y][x];
    intermediatePeakStatistics.weightedCoordinatesSummed_x = data[y][x] * x;
    intermediatePeakStatistics.weightedCoordinatesSummed_y = data[y][x] * y;
    intermediatePeakStatistics.biggestPixelMass = data[y][x];
    intermediatePeakStatistics.pixelCount = 1;

    bool newPixelFound = true;
    for (uint8_t radius = 1; newPixelFound && radius < accuracyConstants.windowRadius; ++radius) {
        analyseRingAroundPixel(radius, thresholdNeighbourPixel, x, y, data_linear, detectorRawFormat, intermediatePeakStatistics, &newPixelFound);
    }

}

static inline void analyseRingAroundPixel(uint8_t radius, float thresholdNeighbourPixel, uint16_t x, uint16_t y, const float* data_linear,
        const detectorRawFormat_t& detectorRawFormat, peakFinder9_intermediatePeakStatistics_t& intermediatePeakStatistics, bool* newPixelFound)
{

    const float (*data)[detectorRawFormat.pix_nx] = (float (*)[detectorRawFormat.pix_nx]) data_linear;

    *newPixelFound = false;
    uint8_t pixelsCount_old = intermediatePeakStatistics.pixelCount;

//upper border
    uint16_t currentY = y - radius;
    for (int_fast8_t i = -radius; i <= radius; ++i) {
        uint16_t currentX = x + i;
        float currentPixelValue = data[currentY][currentX];
        if (currentPixelValue > thresholdNeighbourPixel) {
            addPixelTointermediatePeakStatistics(intermediatePeakStatistics, currentX, currentY, currentPixelValue);
        }
    }

//left and right border
    for (int_fast8_t i = -(radius - 1); i <= (radius - 1); ++i) {
        uint16_t currentX = x - radius;
        uint16_t currentY = y + i;
        float currentPixelValue = data[currentY][currentX];
        if (currentPixelValue > thresholdNeighbourPixel) {
            addPixelTointermediatePeakStatistics(intermediatePeakStatistics, currentX, currentY, currentPixelValue);
        }

        currentX = x + radius;
        currentY = y + i;
        currentPixelValue = data[currentY][currentX];
        if (currentPixelValue > thresholdNeighbourPixel) {
            addPixelTointermediatePeakStatistics(intermediatePeakStatistics, currentX, currentY, currentPixelValue);
        }
    }

//lower border
    currentY = y + radius;
    for (int_fast8_t i = -radius; i <= radius; ++i) {
        uint16_t currentX = x + i;
        float currentPixelValue = data[currentY][currentX];
        if (currentPixelValue > thresholdNeighbourPixel) {
            addPixelTointermediatePeakStatistics(intermediatePeakStatistics, currentX, currentY, currentPixelValue);
        }
    }

    if (pixelsCount_old != intermediatePeakStatistics.pixelCount) {
        *newPixelFound = true;
    }
}

static inline void addPixelTointermediatePeakStatistics(peakFinder9_intermediatePeakStatistics_t& intermediatePeakStatistics, uint16_t x,
        uint16_t y, float pixelValue)
{
    intermediatePeakStatistics.totalMass += pixelValue;
    intermediatePeakStatistics.weightedCoordinatesSummed_x += pixelValue * x;
    intermediatePeakStatistics.weightedCoordinatesSummed_y += pixelValue * y;
    ++intermediatePeakStatistics.pixelCount;
}

static inline void savePeak(float sigmaBackground, float meanBackground, const peakFinder9_intermediatePeakStatistics_t& intermediatePeakStatistics,
        const detectorRawFormat_t& detectorRawFormat, peakList_t& peakList)
{

    float x = intermediatePeakStatistics.weightedCoordinatesSummed_x / intermediatePeakStatistics.totalMass;
    float y = intermediatePeakStatistics.weightedCoordinatesSummed_y / intermediatePeakStatistics.totalMass;
    float peakMass = intermediatePeakStatistics.totalMass - intermediatePeakStatistics.pixelCount * meanBackground;

    if (peakList.peakCount < peakList.maxPeakCount) {
        uint32_t peakCountOld = peakList.peakCount;

        peakList.pixelCount[peakCountOld] = intermediatePeakStatistics.pixelCount;
        peakList.centerOfMass_rawX[peakCountOld] = x;
        peakList.centerOfMass_rawY[peakCountOld] = y;
        peakList.totalIntensity[peakCountOld] = peakMass;
        peakList.maxIntensity[peakCountOld] = intermediatePeakStatistics.biggestPixelMass;
        peakList.sigmaBackground[peakCountOld] = sigmaBackground;
        peakList.snr[peakCountOld] = peakMass / sigmaBackground;

        ++peakList.peakCount;
    }
}

