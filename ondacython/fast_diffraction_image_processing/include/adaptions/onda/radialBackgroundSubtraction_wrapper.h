/*
 * radialBackgroundSubtraction_wrapper.h
 *
 *  Created on: 04.08.2016
 *      Author: gevorkov
 */

#ifndef RADIALBACKGROUNDSUBTRACTION_WRAPPER_H_
#define RADIALBACKGROUNDSUBTRACTION_WRAPPER_H_

#include "radialBackgroundSubtraction.h"
#include "pythonWrapperTypes.h"
#include <detectorRawFormat.h>
#include <ctype.h>

typedef struct {
    radialRankFilter_precomputedConstants_t* precomputedConstants;
    detectorRawFormat_t* detectorRawFormat;
    detectorPositions_t* detectorPositions;
} radialRankFilter_constantArguments_t;

typedef struct {
    uint32_t minValuesPerBin;
    uint32_t minBinWidth;

    uint32_t maxConsideredValuesPerBin;    //0 for infinite

    //Point (x,y) in the way the detector is positioned in the rawImage (top left detector is (0,0), it's right neighbor is (1,0) )
    uint8_t* detectorsToConsiderSubscripts_x;
    uint8_t* detectorsToConsiderSubscripts_y;
    uint16_t detectorsToConsiderCount;

    //must be a subset of detektorsToConsiderIndices
    uint8_t* detectorsToCorrectSubscripts_x;
    uint8_t* detectorsToCorrectSubscripts_y;
    uint16_t detectorsToCorrectCount;

    float rank; //between 0 and 1
} radialRankFilter_accuracyConstants_pythonWrapper_t;

radialRankFilter_constantArguments_t precomputeRadialRankFilterConstantArguments(const uint8_t* mask, const float* detectorGeometryRadiusMatrix,
        const detectorRawFormat_t& detectorRawFormat, const radialRankFilter_accuracyConstants_pythonWrapper_t& accuracyConstants_pythonWrapper,
        detectorGeometryMatrix_pythonWrapper_t detectorGeometryMatrix_pythonWrapper);

void applyRadialRankFilter(float* data, radialRankFilter_constantArguments_t radialRankFilter_constantArguments);

void freePrecomputeRadialRankFilterConstants(radialRankFilter_constantArguments_t radialRankFilter_constantArguments);

#endif /* RADIALBACKGROUNDSUBTRACTION_WRAPPER_H_ */
