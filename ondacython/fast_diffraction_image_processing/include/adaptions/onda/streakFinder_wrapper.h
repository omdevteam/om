/*
 * streakfinder.h
 *
 *  Created on: Feb 1, 2016
 *      Author: vmariani
 */

#ifndef INCLUDE_STREAKFINDER_WRAPPER_H_
#define INCLUDE_STREAKFINDER_WRAPPER_H_

#include <streakFinder.h>
#include <vector>
#include <stddef.h>
#include "streakFinder.h"
#include "detectorGeometry.h"
#include "pythonWrapperTypes.h"

typedef struct {
    streakFinder_accuracyConstants_t* accuracyConstants;
    detectorRawFormat_t* detectorRawFormat;
    detectorPositions_t* detectorPositions;
    streakFinder_precomputedConstants_t* streakFinder_precomputedConstant;
} streakFinder_constantArguments_t;

typedef struct {
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
} streakFinder_accuracyConstants_pythonWrapper_t;

void streakFinder(float* data_linear, streakFinder_constantArguments_t streakFinderConstantArguments);

//makes copy of the data, returns streak mask.
//DO NOT use this together with other functions of this library, it will be slow!
void streakFinder_allInOne(const float* data_linear, uint8_t* streakMask, streakFinder_constantArguments_t streakFinderConstantArguments);

streakFinder_constantArguments_t precomputeStreakFinderConstantArguments(
        streakFinder_accuracyConstants_pythonWrapper_t streakFinder_accuracyConstants,
        detectorRawFormat_t detectorRawFormat,
        detectorGeometryMatrix_pythonWrapper_t detectorGeometryMatrix_pythonWrapper,
        const uint8_t *mask);

void freePrecomputedStreakFinderConstantArguments(streakFinder_constantArguments_t streakfinder_constant_arguments);

#endif /* INCLUDE_STREAKFINDER_WRAPPER_H_ */

