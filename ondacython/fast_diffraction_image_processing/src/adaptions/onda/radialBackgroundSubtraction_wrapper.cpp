/*
 * radialBackgroundSubtraction_wrapper.cpp
 *
 *  Created on: 04.08.2016
 *      Author: gevorkov
 */

#include <adaptions/cheetah/cheetahConversion.h>
#include <adaptions/onda/radialBackgroundSubtraction_wrapper.h>
#include <detectorGeometry.h>

#include <Eigen/Dense>
#include "eigenSTLContainers.h"
#include <cstdint>
#include <vector>

using namespace std;
using namespace Eigen;

radialRankFilter_constantArguments_t precomputeRadialRankFilterConstantArguments(const uint8_t* mask, const float* detectorGeometryRadiusMatrix,
        const detectorRawFormat_t& detectorRawFormat, const radialRankFilter_accuracyConstants_pythonWrapper_t& accuracyConstants_pythonWrapper,
        detectorGeometryMatrix_pythonWrapper_t detectorGeometryMatrix_pythonWrapper)
{
    const radialRankFilter_accuracyConstants_pythonWrapper_t& ac = accuracyConstants_pythonWrapper;

    radialRankFilter_accuracyConstants_t accuracyConstants;

    accuracyConstants.minValuesPerBin = ac.minValuesPerBin;
    accuracyConstants.minBinWidth = ac.minBinWidth;
    accuracyConstants.maxConsideredValuesPerBin = ac.maxConsideredValuesPerBin;
    accuracyConstants.rank = ac.rank;

    for (uint16_t i = 0; i < ac.detectorsToConsiderCount; ++i) {
        accuracyConstants.detektorsToConsiderSubscripts.emplace_back(ac.detectorsToConsiderSubscripts_x[i], ac.detectorsToConsiderSubscripts_y[i]);
    }

    for (uint16_t i = 0; i < ac.detectorsToCorrectCount; ++i) {
        accuracyConstants.detektorsToCorrectSubscripts.emplace_back(ac.detectorsToCorrectSubscripts_x[i], ac.detectorsToCorrectSubscripts_y[i]);
    }

    detectorRawFormat_t* detectorRawFormat_heap = new detectorRawFormat_t;
    *detectorRawFormat_heap = detectorRawFormat;

    vector< EigenSTL::vector_detectorPosition_t > *detectorPositions_heap = new vector< EigenSTL::vector_detectorPosition_t >;
    Vector2f* detectorGeometryMatrix;
    cheetahGetDetectorGeometryMatrix(detectorGeometryMatrix_pythonWrapper.detectorGeometryMatrix_x,
            detectorGeometryMatrix_pythonWrapper.detectorGeometryMatrix_y,
            detectorRawFormat, &detectorGeometryMatrix);
    computeDetectorPositionsFromDetectorGeometryMatrix(*detectorPositions_heap, detectorRawFormat, detectorGeometryMatrix);

    radialRankFilter_precomputedConstants_t* precomputedConstants_heap = new radialRankFilter_precomputedConstants_t;

    precomputeRadialRankFilterConstants(*precomputedConstants_heap, mask, detectorGeometryRadiusMatrix, *detectorPositions_heap, detectorRawFormat,
            accuracyConstants, detectorGeometryMatrix);

    cheetahDeleteDetectorGeometryMatrix(detectorGeometryMatrix);

    radialRankFilter_constantArguments_t radialRankFilter_constantArguments;
    radialRankFilter_constantArguments.precomputedConstants = precomputedConstants_heap;
    radialRankFilter_constantArguments.detectorRawFormat = detectorRawFormat_heap;
    radialRankFilter_constantArguments.detectorPositions = detectorPositions_heap;

    return radialRankFilter_constantArguments;
}

void freePrecomputeRadialRankFilterConstants(radialRankFilter_constantArguments_t radialRankFilter_constantArguments)
{
    delete (radialRankFilter_precomputedConstants_t*) radialRankFilter_constantArguments.precomputedConstants;
    delete (detectorRawFormat_t*) radialRankFilter_constantArguments.detectorRawFormat;
    delete (vector< vector< detectorPosition_t > >*) radialRankFilter_constantArguments.detectorPositions;
}

void applyRadialRankFilter(float* data, radialRankFilter_constantArguments_t radialRankFilter_constantArguments)
{
    const radialRankFilter_precomputedConstants_t* precomputedConstants = radialRankFilter_constantArguments.precomputedConstants;
    const detectorRawFormat_t* detectorRawFormat = radialRankFilter_constantArguments.detectorRawFormat;
    const detectorPositions_t* detectorPositions = radialRankFilter_constantArguments.detectorPositions;

    applyRadialRankFilterBackgroundSubtraction(data, *precomputedConstants, *detectorRawFormat, *detectorPositions);
}
