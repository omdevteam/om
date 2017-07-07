/*
 * streakFinder.cpp
 *
 *  Created on: 11.05.2017
 *      Author: gevorkov
 */

#include <assert.h>
#include <streakFinder.h>
#include <algorithm>
#include <numeric>
#include <cmath>
#include <cfloat>
#include "sortingByOtherValues.h"
#include "eigenSTLContainers.h"

using namespace std;
using namespace Eigen;

typedef struct {
    uint32_t* pixelsToMaskIndices;
    uint32_t numberOfPixelsToMask;
} streakPixelsShort_t;

static inline void precomputePixelToCheckDetectors(const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions,
        streakFinder_precomputedConstants_t& streakFinder_precomputedConstants);
static inline void precomputeFilterDirectionVectors(const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions,
        streakFinder_precomputedConstants_t& streakFinder_precomputedConstants);
static inline void precomputeRadialFilterContributors(const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions, const uint8_t* mask_linear,
        streakFinder_precomputedConstants_t& streakFinder_precomputedConstants);
static inline void precomputeStreakPixels(const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions, const uint8_t* mask_linear,
        streakFinder_precomputedConstants_t& streakFinder_precomputedConstants);
static inline void getAllPixelCoordinatesInRadius(uint16_t x_middle, uint16_t y_middle, uint8_t radius, vector< Point2D< int16_t > >& pixelCoordinatesInRadius);
static inline void getValidPixelCoordinates(const vector< Point2D< int16_t > >& pixelCoordinates, const detectorRawFormat_t& detectorRawFormat,
        const detectorPosition_t& detectorPosition, const uint8_t* mask_linear, vector< uint32_t >& linearValidPixelCoordinates);
static inline void getLinearValidCoordinatesInRadius(uint16_t x_middle, uint16_t y_middle, uint8_t radius,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPosition_t& detectorPosition, const uint8_t* mask_linear, vector< uint32_t >& linearValidPixelCoordinates);
static inline float computeStreakThreshold(const float* data_linear,
        const streakFinder_precomputedConstants_t& streakFinder_precomputedConstants,
        const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants, const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions);
static inline float computeRadialFilter(uint16_t x, uint16_t y, const float* data_linear, const detectorRawFormat_t& detectorRawFormat,
        const streakFinder_precomputedConstants_t& streakFinder_precomputedConstants,
        const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants);

static inline detectorPosition_t* getDetectorPositionFromSubscript(Point2D< uint16_t > subscript, const detectorPositions_t& detectorPositions,
        const detectorRawFormat_t& detectorRawFormat);

void streakFinder(float* data_linear, const streakFinder_accuracyConstants_t& accuracyConstants, const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions, const streakFinder_precomputedConstants_t& streakFinder_precomputedConstants)
{
    auto& ac = accuracyConstants;
    auto& pc = streakFinder_precomputedConstants;

    vector< streakPixelsShort_t > streaksPixelsShort;
    streaksPixelsShort.reserve(streakFinder_precomputedConstants.filterDirectionVectors.size()); //does not need to be dynamic! can be preallocated and passed as parameter!

    float threshold = computeStreakThreshold(data_linear, streakFinder_precomputedConstants, accuracyConstants, detectorRawFormat,
            detectorPositions);

    for (uint16_t pixelToCheckNumber = 0; pixelToCheckNumber < ac.pixelsToCheck.size(); ++pixelToCheckNumber) {
        const detectorPosition_t& detectorPosition = *pc.pixelToCheckDetectors[pixelToCheckNumber];

        float x_streakStart = ac.pixelsToCheck[pixelToCheckNumber].getX();
        float y_streakStart = ac.pixelsToCheck[pixelToCheckNumber].getY();

        float filterValue = computeRadialFilter(x_streakStart, y_streakStart, data_linear, detectorRawFormat, streakFinder_precomputedConstants,
                accuracyConstants);

        if (filterValue > threshold) {
            uint16_t streakLength = 0;

            const Vector2f& filterDirectionVector_normalized = streakFinder_precomputedConstants.filterDirectionVectors[pixelToCheckNumber];

            Vector2f pointOnStreak = Vector2f(x_streakStart, y_streakStart) + filterDirectionVector_normalized;

            uint16_t stepsWithoutStreakPixel = 0;
            float currentRadius = (detectorPosition.virtualZeroPositionRaw - pointOnStreak).norm();
            float streakElongationStepCount = max((float) accuracyConstants.streakElongationMinStepsCount, ac.streakElongationRadiusFactor * currentRadius);
            while (stepsWithoutStreakPixel < streakElongationStepCount
                    && detectorPosition.rawCoordinates_float.contains(Point2D< float >(pointOnStreak))) {
                streakLength++;

                float filterValue = computeRadialFilter(round(pointOnStreak(0)), round(pointOnStreak(1)),
                        data_linear, detectorRawFormat, streakFinder_precomputedConstants, accuracyConstants);
                if (filterValue > threshold) {
                    stepsWithoutStreakPixel = 0;
                    currentRadius = (detectorPosition.virtualZeroPositionRaw - pointOnStreak).norm();
                    streakElongationStepCount = max((float) accuracyConstants.streakElongationMinStepsCount,
                            accuracyConstants.streakElongationRadiusFactor * currentRadius);
                } else {
                    stepsWithoutStreakPixel++;
                }

                pointOnStreak += filterDirectionVector_normalized;
            }

            uint32_t numberOfPixelsToMask = pc.streaksPixels[pixelToCheckNumber].numberOfPixelsToMaskForStreakLength[streakLength];
            const vector< uint32_t > &pixelsToMaskIndices = pc.streaksPixels[pixelToCheckNumber].pixelsToMaskIndices;
            streakPixelsShort_t tmp;
            tmp.pixelsToMaskIndices = (uint32_t*) &pixelsToMaskIndices[0];
            tmp.numberOfPixelsToMask = numberOfPixelsToMask;
            streaksPixelsShort.push_back(tmp);
        }
    }

    for (const auto& streakPixelsShort : streaksPixelsShort)
    {
        for (uint32_t* nextPixelToMaskIndex = streakPixelsShort.pixelsToMaskIndices;
                nextPixelToMaskIndex < streakPixelsShort.pixelsToMaskIndices + streakPixelsShort.numberOfPixelsToMask; nextPixelToMaskIndex++) {
            data_linear[*nextPixelToMaskIndex] = -FLT_MAX;
        }
    }
}

void precomputeStreakFinderConstants(const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions, const uint8_t* mask_linear,
        streakFinder_precomputedConstants_t& streakFinder_precomputedConstants)
{
    precomputePixelToCheckDetectors(streakFinder_accuracyConstants, detectorRawFormat, detectorPositions,
            streakFinder_precomputedConstants);

    precomputeFilterDirectionVectors(streakFinder_accuracyConstants, detectorRawFormat, detectorPositions, streakFinder_precomputedConstants);

    precomputeRadialFilterContributors(streakFinder_accuracyConstants, detectorRawFormat, detectorPositions, mask_linear,
            streakFinder_precomputedConstants);

    precomputeStreakPixels(streakFinder_accuracyConstants, detectorRawFormat, detectorPositions, mask_linear,
            streakFinder_precomputedConstants);
}

static inline void precomputePixelToCheckDetectors(const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions,
        streakFinder_precomputedConstants_t& streakFinder_precomputedConstants)
{
    auto& ac = streakFinder_accuracyConstants;
    auto& pc = streakFinder_precomputedConstants;

    pc.pixelToCheckDetectors.resize(ac.pixelsToCheck.size());

    for (uint16_t pixelToCheckNumber = 0; pixelToCheckNumber < ac.pixelsToCheck.size(); ++pixelToCheckNumber) {
        pc.pixelToCheckDetectors[pixelToCheckNumber] = getDetectorPositionFromSubscript(ac.pixelsToCheck[pixelToCheckNumber], detectorPositions,
                detectorRawFormat);
    }
}

static inline void precomputeFilterDirectionVectors(const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions,
        streakFinder_precomputedConstants_t& streakFinder_precomputedConstants)
{
    auto& ac = streakFinder_accuracyConstants;
    auto& pc = streakFinder_precomputedConstants;

    EigenSTL::vector_Vector2f& filterDirectionVectors = pc.filterDirectionVectors;

    filterDirectionVectors.resize(streakFinder_accuracyConstants.pixelsToCheck.size());

    for (uint16_t pixelToCheckNumber = 0; pixelToCheckNumber < ac.pixelsToCheck.size(); ++pixelToCheckNumber) {
        const detectorPosition_t& detectorPosition = *pc.pixelToCheckDetectors[pixelToCheckNumber];

        Vector2f filterDirectionVector = Vector2f(ac.pixelsToCheck[pixelToCheckNumber].getX(), ac.pixelsToCheck[pixelToCheckNumber].getY())
                - detectorPosition.virtualZeroPositionRaw;

        filterDirectionVectors[pixelToCheckNumber] = filterDirectionVector.normalized();
    }
}

static inline void precomputeRadialFilterContributors(const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions, const uint8_t* mask_linear,
        streakFinder_precomputedConstants_t& streakFinder_precomputedConstants)
{
    auto& ac = streakFinder_accuracyConstants;
    auto& pc = streakFinder_precomputedConstants;

    const uint8_t (*mask)[detectorRawFormat.pix_nx] = (uint8_t (*)[detectorRawFormat.pix_nx]) mask_linear;

    int32_t* & radialFilterContributors_linear = streakFinder_precomputedConstants.radialFilterContributors;
    radialFilterContributors_linear = new int32_t[detectorRawFormat.pix_nn * (ac.filterLength + 1)];

    fill(radialFilterContributors_linear,
            radialFilterContributors_linear + detectorRawFormat.pix_nn * (ac.filterLength + 1),
            -1);

    int32_t (*radialFilterContributors)[detectorRawFormat.pix_nx][ac.filterLength + 1] =
            (int32_t (*)[detectorRawFormat.pix_nx][ac.filterLength + 1]) radialFilterContributors_linear;

    vector< int32_t > currentFilterContributors;
    currentFilterContributors.reserve(ac.filterLength);

    vector< detectorPosition_t* > detectorsToCheck(pc.pixelToCheckDetectors);
    sort(detectorsToCheck.begin(), detectorsToCheck.end());
    auto it = unique(detectorsToCheck.begin(), detectorsToCheck.end());
    detectorsToCheck.resize(distance(detectorsToCheck.begin(), it));

    for (uint16_t detectorToCheckNumber = 0; detectorToCheckNumber < detectorsToCheck.size(); ++detectorToCheckNumber) {
        const detectorPosition_t& detectorPosition = *detectorsToCheck[detectorToCheckNumber];

        for (uint16_t y = detectorPosition.rawCoordinates_uint16.getUpperLeftCorner().getY();
                y <= detectorPosition.rawCoordinates_uint16.getLowerRightCorner().getY();
                ++y) {
            for (uint16_t x = detectorPosition.rawCoordinates_uint16.getUpperLeftCorner().getX();
                    x <= detectorPosition.rawCoordinates_uint16.getLowerRightCorner().getX(); ++x) {
                Vector2f filterDirectionVector = Vector2f(x, y) - detectorPosition.virtualZeroPositionRaw;
                Vector2f filterDirectionVector_normalized = filterDirectionVector.normalized();
                Vector2f filterDirectionVector_adapted = ac.filterStep * filterDirectionVector_normalized;

//                vector<Point<uint16_t, 2>> debug;

                currentFilterContributors.clear();
                for (uint8_t i = 0; i < ac.filterLength; ++i) {
                    Vector2f nextFilterPixel_pos = Vector2f(x, y) + i * filterDirectionVector_adapted;

                    Point2D< uint16_t > nextFilterPixel_posRounded = Point2D< float >(nextFilterPixel_pos.array().round());
                    if (nextFilterPixel_posRounded > detectorPosition.rawCoordinates_uint16.getUpperLeftCorner()
                            && nextFilterPixel_posRounded < detectorPosition.rawCoordinates_uint16.getLowerRightCorner()
                            && mask[nextFilterPixel_posRounded.getY()][nextFilterPixel_posRounded.getX()] == 0) {

                        currentFilterContributors.push_back(
                                nextFilterPixel_posRounded.getY() * detectorRawFormat.pix_nx + nextFilterPixel_posRounded.getX());

//                        debug.push_back(nextFilterPixel_posRounded);
                    }
                }

                if (currentFilterContributors.size() >= ac.minFilterLength) {
                    copy(currentFilterContributors.begin(), currentFilterContributors.end(), &radialFilterContributors[y][x][0]);
                }
            }
        }
    }
}

static inline void precomputeStreakPixels(const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat, const detectorPositions_t& detectorPositions, const uint8_t* mask_linear,
        streakFinder_precomputedConstants_t& streakFinder_precomputedConstants)
{
    auto& ac = streakFinder_accuracyConstants;
    auto& pc = streakFinder_precomputedConstants;

    vector< streakPixels_t > &streaksPixels = streakFinder_precomputedConstants.streaksPixels;
    streaksPixels.resize(ac.pixelsToCheck.size());

    vector< uint32_t > pixelsToMask, newPixelsToMask, pixelsToMask_sorted, newPixelsToMask_cleaned;
    vector< uint32_t > numberOfPixelsToMaskForStreakLength;
    pixelsToMask.reserve(detectorRawFormat.asic_nx * detectorRawFormat.asic_ny);
    newPixelsToMask.reserve(detectorRawFormat.asic_nx * detectorRawFormat.asic_ny);
    pixelsToMask_sorted.reserve(detectorRawFormat.asic_nx * detectorRawFormat.asic_ny);
    newPixelsToMask_cleaned.reserve(detectorRawFormat.asic_nx * detectorRawFormat.asic_ny);
    numberOfPixelsToMaskForStreakLength.reserve(detectorRawFormat.asic_nx + detectorRawFormat.asic_ny);

    for (uint16_t pixelToCheckNumber = 0; pixelToCheckNumber < ac.pixelsToCheck.size(); ++pixelToCheckNumber) {
        const detectorPosition_t& detectorPosition = *pc.pixelToCheckDetectors[pixelToCheckNumber];

        float x_streakStart = ac.pixelsToCheck[pixelToCheckNumber].getX();
        float y_streakStart = ac.pixelsToCheck[pixelToCheckNumber].getY();

        pixelsToMask.clear();
        numberOfPixelsToMaskForStreakLength.clear();
        pixelsToMask_sorted.clear();

        Vector2f& filterDirectionVector_normalized = pc.filterDirectionVectors[pixelToCheckNumber];

        //backtrack streak
        Vector2f currentStreakPos_backtrack(x_streakStart, y_streakStart);
        while (detectorPosition.rawCoordinates_float.contains(Point2D< float >(currentStreakPos_backtrack))
                && filterDirectionVector_normalized.dot(currentStreakPos_backtrack - detectorPosition.virtualZeroPositionRaw) > 0) {
            getLinearValidCoordinatesInRadius((uint16_t) round((float) currentStreakPos_backtrack(0)),
                    (uint16_t) round((float) currentStreakPos_backtrack(1)),
                    streakFinder_accuracyConstants.streakPixelMaskRadius, detectorRawFormat, detectorPosition, mask_linear, newPixelsToMask);

            pixelsToMask.insert(pixelsToMask.end(), newPixelsToMask.begin(), newPixelsToMask.end());

            sort(pixelsToMask.begin(), pixelsToMask.end());
            auto it = unique(pixelsToMask.begin(), pixelsToMask.end());
            pixelsToMask.resize(distance(pixelsToMask.begin(), it));

            currentStreakPos_backtrack -= filterDirectionVector_normalized;
        }
        numberOfPixelsToMaskForStreakLength.push_back(pixelsToMask.size());

        pixelsToMask_sorted.insert(pixelsToMask_sorted.end(), pixelsToMask.begin(), pixelsToMask.end());
        sort(pixelsToMask_sorted.begin(), pixelsToMask_sorted.end());

        //mask as long as streak is possible
        Point2D< float > currentStreakPos = Point2D< float >(Vector2f(x_streakStart, y_streakStart) + filterDirectionVector_normalized);
        while (detectorPosition.rawCoordinates_float.contains(currentStreakPos)) {
            getLinearValidCoordinatesInRadius(currentStreakPos.getRounded().getX(), currentStreakPos.getRounded().getY(),
                    streakFinder_accuracyConstants.streakPixelMaskRadius, detectorRawFormat, detectorPosition, mask_linear, newPixelsToMask);

            newPixelsToMask_cleaned.clear();
            sort(newPixelsToMask.begin(), newPixelsToMask.end());
            set_difference(newPixelsToMask.begin(), newPixelsToMask.end(), pixelsToMask_sorted.begin(), pixelsToMask_sorted.end(),
                    inserter(newPixelsToMask_cleaned, newPixelsToMask_cleaned.begin()));

            pixelsToMask.insert(pixelsToMask.end(), newPixelsToMask_cleaned.begin(), newPixelsToMask_cleaned.end());
            numberOfPixelsToMaskForStreakLength.push_back(pixelsToMask.size());

            pixelsToMask_sorted.insert(pixelsToMask_sorted.end(), newPixelsToMask_cleaned.begin(), newPixelsToMask_cleaned.end());
            sort(pixelsToMask_sorted.begin(), pixelsToMask_sorted.end());

            currentStreakPos += Point2D< float >(filterDirectionVector_normalized);
        }

        vector< uint32_t > &pixelsToMask_inPrecomputedArray =
                streakFinder_precomputedConstants.streaksPixels[pixelToCheckNumber].pixelsToMaskIndices;
        vector< uint32_t > &numberOfPixelsToMaskForStreakLength_inPrecomputedArray =
                streakFinder_precomputedConstants.streaksPixels[pixelToCheckNumber].numberOfPixelsToMaskForStreakLength;

        pixelsToMask_inPrecomputedArray.reserve(pixelsToMask.size());
        pixelsToMask_inPrecomputedArray.insert(pixelsToMask_inPrecomputedArray.end(), pixelsToMask.begin(), pixelsToMask.end());

        numberOfPixelsToMaskForStreakLength_inPrecomputedArray.reserve(numberOfPixelsToMaskForStreakLength.size());
        numberOfPixelsToMaskForStreakLength_inPrecomputedArray.insert(numberOfPixelsToMaskForStreakLength_inPrecomputedArray.end(),
                numberOfPixelsToMaskForStreakLength.begin(), numberOfPixelsToMaskForStreakLength.end());
    }

}

static inline void getAllPixelCoordinatesInRadius(uint16_t x_middle, uint16_t y_middle, uint8_t radius,
        vector< Point2D< int16_t > >& pixelCoordinatesInRadius)
{
    pixelCoordinatesInRadius.clear();
    pixelCoordinatesInRadius.reserve((2 * radius + 1) * (2 * radius + 1));

    for (int16_t x = x_middle - radius; x <= x_middle + radius; ++x) {
        for (int16_t y = y_middle - radius; y <= y_middle + radius; ++y) {
            pixelCoordinatesInRadius.push_back(Point2D< int16_t >(x, y));
        }
    }
}

static inline void getValidPixelCoordinates(const vector< Point2D< int16_t > >& pixelCoordinates, const detectorRawFormat_t& detectorRawFormat,
        const detectorPosition_t& detectorPosition, const uint8_t* mask_linear, vector< uint32_t >& linearValidPixelCoordinates)
{
    const uint8_t (*mask)[detectorRawFormat.pix_nx] = (uint8_t (*)[detectorRawFormat.pix_nx]) mask_linear;

    linearValidPixelCoordinates.clear();

    vector< Point2D< int16_t > > validPixelCoordinates_debug;

    for (const auto& pixelCoordinate : pixelCoordinates)
    {
        if (pixelCoordinate >= Point2D< int16_t >(detectorPosition.rawCoordinates_uint16.getUpperLeftCorner())
                && pixelCoordinate <= Point2D< int16_t >(detectorPosition.rawCoordinates_uint16.getLowerRightCorner())
                && mask[pixelCoordinate.getY()][pixelCoordinate.getX()] == 0) {

            validPixelCoordinates_debug.push_back(pixelCoordinate);
            linearValidPixelCoordinates.push_back(pixelCoordinate.getY() * detectorRawFormat.pix_nx + pixelCoordinate.getX());
        }
    }
}

static inline void getLinearValidCoordinatesInRadius(uint16_t x_middle, uint16_t y_middle, uint8_t radius,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPosition_t& detectorPosition, const uint8_t* mask_linear, vector< uint32_t >& linearValidPixelCoordinates)
{
    vector< Point2D< int16_t > > pixelCoordinatesInRadius;

    getAllPixelCoordinatesInRadius(x_middle, y_middle, radius, pixelCoordinatesInRadius);
    getValidPixelCoordinates(pixelCoordinatesInRadius, detectorRawFormat, detectorPosition, mask_linear, linearValidPixelCoordinates);
}

#define MAX_REGIONS_COUNT 500
static inline float computeStreakThreshold(const float* data_linear,
        const streakFinder_precomputedConstants_t& streakFinder_precomputedConstants,
        const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants, const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions)
{

    const size_t regionsCount = streakFinder_accuracyConstants.backgroundEstimationRegions.size();
    assert(regionsCount <= MAX_REGIONS_COUNT);

    float means[MAX_REGIONS_COUNT];
    float sigmas[MAX_REGIONS_COUNT];
    uint8_t validRegionsEstimated = 0;

    for (const auto & backgroundEstimationRegion : streakFinder_accuracyConstants.backgroundEstimationRegions)
    {
        uint32_t validValuesCount = 0;
        double sum = 0, sumOfSquares = 0;

//            vector< float > debug;

        for (uint16_t y = backgroundEstimationRegion.getUpperLeftCorner().getY(); y <= backgroundEstimationRegion.getLowerRightCorner().getY(); ++y) {
            for (uint16_t x = backgroundEstimationRegion.getUpperLeftCorner().getX(); x <= backgroundEstimationRegion.getLowerRightCorner().getX(); ++x) {

                float filterValue = computeRadialFilter(x, y, data_linear, detectorRawFormat, streakFinder_precomputedConstants,
                        streakFinder_accuracyConstants);

//                    debug.push_back(filterValue);

                if (filterValue != -FLT_MAX) {
                    sumOfSquares += filterValue * filterValue;
                    sum += filterValue;
                    validValuesCount++;
                }
            }
        }

        if (validValuesCount > 0) {
            float currentMean = (float) sum / validValuesCount;
            means[validRegionsEstimated] = currentMean;
            sigmas[validRegionsEstimated] = sqrt(((float) sumOfSquares - currentMean * currentMean * validValuesCount) / (float) (validValuesCount - 1));
            validRegionsEstimated++;
        }
    }

    uint8_t indices[regionsCount];
    iota(indices, indices + validRegionsEstimated, 0);
    nth_element(indices, indices + 1, indices + validRegionsEstimated, [&](size_t a, size_t b) {return sigmas[a] < sigmas[b];}); //compute index of second-largest element

    float threshold = means[indices[1]] + streakFinder_accuracyConstants.sigmaFactor * sigmas[indices[1]];
    return threshold;
}

static inline float computeRadialFilter(uint16_t x, uint16_t y, const float* data_linear, const detectorRawFormat_t& detectorRawFormat,
        const streakFinder_precomputedConstants_t& streakFinder_precomputedConstants,
        const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants)
{

    int32_t (*radialFilterContributors)[detectorRawFormat.pix_nx][streakFinder_accuracyConstants.filterLength + 1] =
            (int32_t (*)[detectorRawFormat.pix_nx][streakFinder_accuracyConstants.filterLength + 1]) streakFinder_precomputedConstants.radialFilterContributors;

    float filterContributors[streakFinder_accuracyConstants.filterLength]; //using #define instead of pix_nx gives a tiny performance boost
    float* nextFilterContributor = filterContributors;

    int32_t* nextContributorIndex = &radialFilterContributors[y][x][0];
    if (*nextContributorIndex < 0) {
        return -FLT_MAX;
    }

    while (*nextContributorIndex >= 0) {
        *nextFilterContributor = data_linear[*nextContributorIndex];
        nextFilterContributor++;
        nextContributorIndex++;
    }

    float* median = filterContributors + (nextFilterContributor - filterContributors) / 2;
    nth_element(filterContributors, median, nextFilterContributor);
    float filterValue = accumulate(filterContributors, median, *median) / (median - filterContributors + 1);

    return filterValue;
}

void freePrecomputedStreakFinderConstants(streakFinder_precomputedConstants_t& streakFinder_precomputedConstants)
{
    delete[] streakFinder_precomputedConstants.radialFilterContributors;
}

static inline detectorPosition_t* getDetectorPositionFromSubscript(Point2D< uint16_t > subscript, const detectorPositions_t& detectorPositions,
        const detectorRawFormat_t& detectorRawFormat)
{
    return (detectorPosition_t*) &detectorPositions[subscript.getX() / detectorRawFormat.asic_nx][subscript.getY() / detectorRawFormat.asic_ny];
}
