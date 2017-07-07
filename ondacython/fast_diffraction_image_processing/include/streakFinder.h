/*
 * streakFinder.h
 *
 *  Created on: 11.05.2017
 *      Author: gevorkov
 */

#ifndef INCLUDE_STREAKFINDER_H_
#define INCLUDE_STREAKFINDER_H_

#include <Point2D.h>
#include <stdint.h>
#include <vector>
#include "detectorGeometry.h"
#include "ImageRectangle.h"
#include <Eigen/Dense>
#include "eigenSTLContainers.h" 

typedef struct {
    uint8_t filterLength;
    uint8_t minFilterLength;
    float filterStep;

    float sigmaFactor;
    uint8_t streakElongationMinStepsCount;
    float streakElongationRadiusFactor;
    uint8_t streakPixelMaskRadius;
    std::vector< Point2D< uint16_t > > pixelsToCheck;
    std::vector< ImageRectangle< uint16_t > > backgroundEstimationRegions;
} streakFinder_accuracyConstants_t;

typedef struct {
    std::vector< uint32_t > pixelsToMaskIndices;
    std::vector< uint32_t > numberOfPixelsToMaskForStreakLength;
} streakPixels_t;
typedef struct {
    EigenSTL::vector_Vector2f filterDirectionVectors;
    std::vector< detectorPosition_t* > pixelToCheckDetectors;

    int32_t* radialFilterContributors; // [y][x][contributor]

    std::vector< streakPixels_t > streaksPixels;
} streakFinder_precomputedConstants_t;

void precomputeStreakFinderConstants(const streakFinder_accuracyConstants_t& streakFinder_accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions,
        const uint8_t* mask_linear,
        streakFinder_precomputedConstants_t& streakFinder_precomputedConstants);

void freePrecomputedStreakFinderConstants(streakFinder_precomputedConstants_t& streakFinder_precomputedConstants);

void streakFinder(float* data_linear, const streakFinder_accuracyConstants_t& accuracyConstants, const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions, const streakFinder_precomputedConstants_t& streakFinder_precomputedConstants);

#endif /* INCLUDE_STREAKFINDER_H_ */
