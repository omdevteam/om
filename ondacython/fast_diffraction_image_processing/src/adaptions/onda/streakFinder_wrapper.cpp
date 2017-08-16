/*
 * streakfinder.cpp
 *
 *  Created on: Feb 5, 2016
 *      Author: vmariani
 */

#include "adaptions/cheetah/cheetahConversion.h"
#include "mask.h"
#include <string.h>
#include "ImageRectangle.h"
#include <stdint.h>
#include <algorithm>
#include "adaptions/onda/streakFinder_wrapper.h"

using namespace std;
using namespace Eigen;

streakFinder_constantArguments_t precomputeStreakFinderConstantArguments(
        streakFinder_accuracyConstants_pythonWrapper_t streakFinder_accuracyConstants,
        detectorRawFormat_t detectorRawFormat,
        detectorGeometryMatrix_pythonWrapper_t detectorGeometryMatrix_pythonWrapper,
        const uint8_t *mask)
{
    const streakFinder_accuracyConstants_pythonWrapper_t& ac = streakFinder_accuracyConstants;

    streakFinder_accuracyConstants_t *accuracyConstants_heap = new streakFinder_accuracyConstants_t;
    accuracyConstants_heap->filterLength = streakFinder_accuracyConstants.filterLength;
    accuracyConstants_heap->minFilterLength = streakFinder_accuracyConstants.minFilterLength;
    accuracyConstants_heap->filterStep = streakFinder_accuracyConstants.filterStep;
    accuracyConstants_heap->sigmaFactor = streakFinder_accuracyConstants.sigmaFactor;
    accuracyConstants_heap->streakElongationMinStepsCount = streakFinder_accuracyConstants.streakElongationMinStepsCount;
    accuracyConstants_heap->streakElongationRadiusFactor = streakFinder_accuracyConstants.streakElongationRadiusFactor;
    accuracyConstants_heap->streakPixelMaskRadius = streakFinder_accuracyConstants.streakPixelMaskRadius;

    for (uint16_t i = 0; i < ac.pixelsToCheckCount; ++i) {
        accuracyConstants_heap->pixelsToCheck.emplace_back(ac.pixelsToCheck_x[i], ac.pixelsToCheck_y[i]);
    }

    for (uint16_t i = 0; i < ac.backgroundEstimationRegionsCount; ++i) {
        accuracyConstants_heap->backgroundEstimationRegions.emplace_back(
                Point2D< uint16_t >(ac.backgroundEstimationRegions_upperLeftCorner_x[i], ac.backgroundEstimationRegions_upperLeftCorner_y[i]),
                Point2D< uint16_t >(ac.backgroundEstimationRegions_lowerRightCorner_x[i], ac.backgroundEstimationRegions_lowerRightCorner_y[i]));
    }

    detectorRawFormat_t* detectorRawFormat_heap = new detectorRawFormat_t;
    *detectorRawFormat_heap = detectorRawFormat;

    vector< EigenSTL::vector_detectorPosition_t > *detectorPositions_heap = new vector< EigenSTL::vector_detectorPosition_t >;
    Vector2f* detectorGeometryMatrix;
    cheetahGetDetectorGeometryMatrix(
            detectorGeometryMatrix_pythonWrapper.detectorGeometryMatrix_x, detectorGeometryMatrix_pythonWrapper.detectorGeometryMatrix_y,
            detectorRawFormat, &detectorGeometryMatrix);
    computeDetectorPositionsFromDetectorGeometryMatrix(*detectorPositions_heap, detectorRawFormat, detectorGeometryMatrix);
    cheetahDeleteDetectorGeometryMatrix(detectorGeometryMatrix);

    streakFinder_precomputedConstants_t *streakFinder_precomputedConstants_heap = new streakFinder_precomputedConstants_t;
    precomputeStreakFinderConstants(*accuracyConstants_heap, detectorRawFormat, *detectorPositions_heap, mask,
            *streakFinder_precomputedConstants_heap);

    streakFinder_constantArguments_t streakFinderConstantArguments;

    streakFinderConstantArguments.accuracyConstants = accuracyConstants_heap;
    streakFinderConstantArguments.detectorRawFormat = detectorRawFormat_heap;
    streakFinderConstantArguments.detectorPositions = detectorPositions_heap;
    streakFinderConstantArguments.streakFinder_precomputedConstant = streakFinder_precomputedConstants_heap;

    return streakFinderConstantArguments;
}

void freePrecomputedStreakFinderConstantArguments(streakFinder_constantArguments_t streakfinder_constant_arguments)
{
    delete streakfinder_constant_arguments.accuracyConstants;
    delete streakfinder_constant_arguments.detectorRawFormat;
    delete streakfinder_constant_arguments.detectorPositions;
    freePrecomputedStreakFinderConstants(*streakfinder_constant_arguments.streakFinder_precomputedConstant);
}

void streakFinder(float* data_linear, streakFinder_constantArguments_t streakFinderConstantArguments)
{
    const streakFinder_accuracyConstants_t* accuracyConstants = (const streakFinder_accuracyConstants_t*) streakFinderConstantArguments.accuracyConstants;
    const detectorRawFormat_t* detectorRawFormat = (const detectorRawFormat_t*) streakFinderConstantArguments.detectorRawFormat;
    const detectorPositions_t* detectorPositions = (const detectorPositions_t*) streakFinderConstantArguments.detectorPositions;
    const streakFinder_precomputedConstants_t* streakFinder_precomputedConstants =
            (const streakFinder_precomputedConstants_t*) streakFinderConstantArguments.streakFinder_precomputedConstant;

    streakFinder(data_linear, *accuracyConstants, *detectorRawFormat, *detectorPositions, *streakFinder_precomputedConstants);
}

void streakFinder_allInOne(const float* data_linear, uint8_t* streakMask, streakFinder_constantArguments_t streakFinderConstantArguments)
{
    const streakFinder_accuracyConstants_t* accuracyConstants = (const streakFinder_accuracyConstants_t*) streakFinderConstantArguments.accuracyConstants;
    const detectorRawFormat_t* detectorRawFormat = (const detectorRawFormat_t*) streakFinderConstantArguments.detectorRawFormat;
    const detectorPositions_t* detectorPositions = (const detectorPositions_t*) streakFinderConstantArguments.detectorPositions;
    const streakFinder_precomputedConstants_t* streakFinder_precomputedConstants =
            (const streakFinder_precomputedConstants_t*) streakFinderConstantArguments.streakFinder_precomputedConstant;

    vector< float > dataCopy(detectorRawFormat->pix_nn);
    copy(data_linear, data_linear + detectorRawFormat->pix_nn, dataCopy.data());

    streakFinder(dataCopy.data(), *accuracyConstants, *detectorRawFormat, *detectorPositions, *streakFinder_precomputedConstants);

    getMaskFromMergedMaskInData(data_linear, streakMask, *detectorRawFormat);
}
