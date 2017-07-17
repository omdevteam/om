/*
 * radialBackgroundSubtraction.h
 *
 *  Created on: 26.06.2016
 *      Author: Yaro
 */

#ifndef RADIALBACKGROUNDSUBTRACTION_H_
#define RADIALBACKGROUNDSUBTRACTION_H_

#include <Point2D.h>
#include <stdint.h>
#include <vector>
#include "detectorGeometry.h"
#include <Eigen/Dense>
#include <Eigen/StdVector>

typedef struct {
    uint32_t minValuesPerBin;
    uint32_t minBinWidth;

    uint32_t maxConsideredValuesPerBin;    //0 for infinite

    std::vector< Point2D< uint8_t > > detektorsToConsiderSubscripts; //Point (x,y) in the way the detector is positioned in the rawImage (top left detector is (0,0), it's right neighbor is (1,0) )
    std::vector< Point2D< uint8_t > > detektorsToCorrectSubscripts; //must be a subset of detektorsToConsiderIndices

    float rank; //between 0 and 1
} radialRankFilter_accuracyConstants_t;

typedef struct {
    std::vector< uint32_t > sparseLinearDataToConsiderIndices;
    std::vector< uint16_t > sparseBinIndices;

    uint16_t binCount;
    std::vector< uint32_t > dataCountPerBin;

    std::vector< uint16_t > intraBinIndices;

    std::vector< float > binRadii;

    std::vector< float > intraBinInterpolationConstant;

    radialRankFilter_accuracyConstants_t accuracyConstants;
} radialRankFilter_precomputedConstants_t;

void precomputeRadialRankFilterConstants(radialRankFilter_precomputedConstants_t& precomputedConstants, const uint8_t* mask_linear,
        const float* detectorGeometryRadiusMatrix_linear, const detectorPositions_t& detectorPositions, const detectorRawFormat_t& detectorRawFormat,
        const radialRankFilter_accuracyConstants_t& accuracyConstants, const Eigen::Vector2f* detectorGeometryMatrix_linear);

void applyRadialRankFilterBackgroundSubtraction(float* data_linear,
        const radialRankFilter_precomputedConstants_t& precomputedConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions);

#endif /* RADIALBACKGROUNDSUBTRACTION_H_ */
