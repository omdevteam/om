/*
 * radialBackgroundSubtraction.cpp
 *
 *  Created on: 26.06.2016
 *      Author: Yaro
 */

#include "radialBackgroundSubtraction.h"
#include <algorithm>
#include <cmath>
#include <cfloat>
#include <limits>
#include "matlabLikeFunctions.h"
#include "sortingByOtherValues.h"

using namespace Eigen;
using namespace std;

static void gatherAvailableRadii(vector< float >& availableRadii, vector< Point2D< uint16_t > >& radiiMatrixIndices,
        const radialRankFilter_accuracyConstants_t& accuracyConstants, const uint8_t* mask_linear,
        const detectorPositions_t& detectorPositions,
        const detectorRawFormat_t& detectorRawFormat, const float* detectorGeometryRadiusMatrix_linear);
static void fillBins(vector< vector< Point2D< uint16_t > > >& binsWithIndices, vector< vector< float > >& binsWithRadii,
        vector< float > &availableRadii, vector< Point2D< uint16_t > >& radiiMatrixIndices,
        const radialRankFilter_accuracyConstants_t& accuracyConstants);
static void thinOutBins(vector< vector< float > > &binsWithRadii, vector< vector< Point2D< uint16_t > > >& binsWithIndices,
        const radialRankFilter_accuracyConstants_t& accuracyConstants, const Vector2f* detectorGeometryMatrix_linear,
        const detectorRawFormat_t& detectorRawFormat);
static void computeAngles(vector< float > &angles, const vector< Point2D< uint16_t > >& radiiMatrixIndices,
        const Vector2f* detectorGeometryMatrix_linear, const detectorRawFormat_t& detectorRawFormat);
static void computeBinsWithLinearindicesFromBinsWithMatrixIndices(vector< vector< uint32_t > >& binsWithLinearIndices,
        const vector< vector< Point2D< uint16_t > > >& binsWithIndices, const detectorRawFormat_t& detectorRawFormat);
static void computeSparsePrecomputedConstants(radialRankFilter_precomputedConstants_t& precomputedConstants,
        const vector< vector< uint32_t > >& binsWithLinearIndices);
static void computeBinRadii(radialRankFilter_precomputedConstants_t& precomputedConstants, const vector< vector< float > >& binsWithRadii);
static void computeDataCountPerBin(radialRankFilter_precomputedConstants_t& precomputedConstants, const vector< vector< float > >& binsWithRadii);
static void computeIntraBinIndices(radialRankFilter_precomputedConstants_t& precomputedConstants, const uint8_t* mask_linear,
        const vector< vector< uint32_t > >& binsWithLinearIndices, const float* detectorGeometryRadiusMatrix_linear,
        const radialRankFilter_accuracyConstants_t& accuracyConstants, const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions);
static void computeIntraBinInterpolationConstant(radialRankFilter_precomputedConstants_t& precomputedConstants, const uint8_t* mask_linear,
        const float* detectorGeometryRadiusMatrix_linear, const radialRankFilter_accuracyConstants_t& accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions);

static void gatherBinsData(vector< vector< float > >& binsWithData, const float* data_linear,
        const radialRankFilter_precomputedConstants_t& precomputedConstants);
static void computeBinValues(vector< float >& binValues, vector< vector< float > >& binsWithData,
        const radialRankFilter_precomputedConstants_t& precomputedConstants, const radialRankFilter_accuracyConstants_t& accuracyConstants);

void precomputeRadialRankFilterConstants(radialRankFilter_precomputedConstants_t& precomputedConstants, const uint8_t* mask_linear,
        const float* detectorGeometryRadiusMatrix_linear,
        const detectorPositions_t& detectorPositions,
        const detectorRawFormat_t& detectorRawFormat, const radialRankFilter_accuracyConstants_t& accuracyConstants,
        const Eigen::Vector2f* detectorGeometryMatrix_linear)
{
    precomputedConstants.accuracyConstants = accuracyConstants;

    vector< float > availableRadii;
    vector< Point2D< uint16_t > > radiiMatrixIndices;

    gatherAvailableRadii(availableRadii, radiiMatrixIndices, accuracyConstants, mask_linear, detectorPositions, detectorRawFormat,
            detectorGeometryRadiusMatrix_linear);

    vector< vector< Point2D< uint16_t > > > binsWithIndices;
    vector< vector< float > > binsWithRadii;

    fillBins(binsWithIndices, binsWithRadii, availableRadii, radiiMatrixIndices, accuracyConstants);

    vector< vector< Point2D< uint16_t > > > binsWithIndices_thinedOut(binsWithIndices);
    vector< vector< float > > binsWithRadii_thinedOut(binsWithRadii);

    thinOutBins(binsWithRadii_thinedOut, binsWithIndices_thinedOut, accuracyConstants, detectorGeometryMatrix_linear, detectorRawFormat);

    vector< vector< uint32_t > > binsWithLinearIndices_thinedOut;

    computeBinsWithLinearindicesFromBinsWithMatrixIndices(binsWithLinearIndices_thinedOut, binsWithIndices_thinedOut, detectorRawFormat);
    computeSparsePrecomputedConstants(precomputedConstants, binsWithLinearIndices_thinedOut);

    computeBinRadii(precomputedConstants, binsWithRadii_thinedOut);
    precomputedConstants.binCount = binsWithRadii.size() + 2;

    computeDataCountPerBin(precomputedConstants, binsWithRadii_thinedOut);

    vector< vector< uint32_t > > binsWithLinearIndices;

    computeBinsWithLinearindicesFromBinsWithMatrixIndices(binsWithLinearIndices, binsWithIndices, detectorRawFormat);
    computeIntraBinIndices(precomputedConstants, mask_linear, binsWithLinearIndices, detectorGeometryRadiusMatrix_linear, accuracyConstants,
            detectorRawFormat, detectorPositions);

    computeIntraBinInterpolationConstant(precomputedConstants, mask_linear, detectorGeometryRadiusMatrix_linear, accuracyConstants, detectorRawFormat,
            detectorPositions);
}

void applyRadialRankFilterBackgroundSubtraction(float* data_linear,
        const radialRankFilter_precomputedConstants_t& precomputedConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions)
{
    const radialRankFilter_accuracyConstants_t& accuracyConstants = precomputedConstants.accuracyConstants;

    vector< vector< float > > binsWithData;
    gatherBinsData(binsWithData, data_linear, precomputedConstants);

    vector< float > binValues;
    computeBinValues(binValues, binsWithData, precomputedConstants, accuracyConstants);

    for (const auto& detektorToCorrectIndex : accuracyConstants.detektorsToCorrectSubscripts) {
        const detectorPosition_t detectorPosition = detectorPositions[detektorToCorrectIndex.getY()][detektorToCorrectIndex.getX()];

        for (uint16_t y = detectorPosition.rawCoordinates_uint16.getUpperLeftCorner().getY() + 1;
                y <= detectorPosition.rawCoordinates_uint16.getLowerRightCorner().getY() - 1; ++y) {
            for (uint16_t x = detectorPosition.rawCoordinates_uint16.getUpperLeftCorner().getX() + 1;
                    x <= detectorPosition.rawCoordinates_uint16.getLowerRightCorner().getX() - 1; ++x) {
                uint32_t linearIndex = getLinearIndexFromMatrixIndex(x, y, detectorRawFormat);
                if (data_linear[linearIndex] != FLT_MAX) {
                    data_linear[linearIndex] -= binValues[precomputedConstants.intraBinIndices[linearIndex]]
                            + precomputedConstants.intraBinInterpolationConstant[linearIndex]
                                    * (binValues[precomputedConstants.intraBinIndices[linearIndex] + 1]
                                            - binValues[precomputedConstants.intraBinIndices[linearIndex]]);
                }
            }
        }
    }
}

static void gatherBinsData(vector< vector< float > >& binsWithData, const float* data_linear,
        const radialRankFilter_precomputedConstants_t& precomputedConstants)
{
    binsWithData.resize(precomputedConstants.binCount);
    for (uint32_t i = 1; i < binsWithData.size() - 1; ++i) {
        binsWithData[i].reserve(precomputedConstants.dataCountPerBin[i]);
    }

    for (uint32_t i = 0; i < precomputedConstants.sparseLinearDataToConsiderIndices.size(); ++i) {
        binsWithData[precomputedConstants.sparseBinIndices[i]].push_back(data_linear[precomputedConstants.sparseLinearDataToConsiderIndices[i]]);
    }
}

static void computeBinValues(vector< float >& binValues, vector< vector< float > >& binsWithData,
        const radialRankFilter_precomputedConstants_t& precomputedConstants, const radialRankFilter_accuracyConstants_t& accuracyConstants)
{
    binValues.resize(binsWithData.size());
    for (uint32_t i = 1; i < binsWithData.size() - 1; ++i) {
        uint32_t intRank = max((uint32_t) (accuracyConstants.rank * binsWithData[i].size()), (uint32_t) 1) - 1;
        nth_element(binsWithData[i].begin(), binsWithData[i].begin() + intRank, binsWithData[i].end());
        binValues[i] = binsWithData[i][intRank];
    }

    binValues[0] = binValues[1]
            + (binValues[1] - binValues[2]) /
                    (precomputedConstants.binRadii[2] - precomputedConstants.binRadii[1]) *
                    (precomputedConstants.binRadii[1] - precomputedConstants.binRadii[0]);

    uint32_t lastIndex = binValues.size() - 1;
    binValues[lastIndex] = binValues[lastIndex - 1] +
            (binValues[lastIndex - 1] - binValues[lastIndex - 2]) /
                    (precomputedConstants.binRadii[lastIndex - 1] - precomputedConstants.binRadii[lastIndex - 2]) *
                    (precomputedConstants.binRadii[lastIndex] - precomputedConstants.binRadii[lastIndex - 1]);
}

static void gatherAvailableRadii(vector< float > &availableRadii, vector< Point2D< uint16_t > > &radiiMatrixIndices,
        const radialRankFilter_accuracyConstants_t& accuracyConstants, const uint8_t* mask_linear,
        const detectorPositions_t& detectorPositions,
        const detectorRawFormat_t& detectorRawFormat, const float* detectorGeometryRadiusMatrix_linear)
{
    const uint8_t (*mask)[detectorRawFormat.pix_nx] = (uint8_t (*)[detectorRawFormat.pix_nx]) mask_linear;
    const float (*detectorGeometryRadiusMatrix)[detectorRawFormat.pix_nx] =
            (float (*)[detectorRawFormat.pix_nx]) detectorGeometryRadiusMatrix_linear;

    for (uint8_t detektorToConsiderNumber = 0; detektorToConsiderNumber < accuracyConstants.detektorsToConsiderSubscripts.size(); ++detektorToConsiderNumber) {
        const Point2D< uint8_t >& detektorToConsiderIndex = accuracyConstants.detektorsToConsiderSubscripts[detektorToConsiderNumber];

        const detectorPosition_t detectorPosition = detectorPositions[detektorToConsiderIndex.getY()][detektorToConsiderIndex.getX()];

        for (uint16_t y = detectorPosition.rawCoordinates_uint16.getUpperLeftCorner().getY() + 1;
                y <= detectorPosition.rawCoordinates_uint16.getLowerRightCorner().getY() - 1; ++y) {
            for (uint16_t x = detectorPosition.rawCoordinates_uint16.getUpperLeftCorner().getX() + 1;
                    x <= detectorPosition.rawCoordinates_uint16.getLowerRightCorner().getX() - 1; ++x) {
                if (mask[y][x] == 0) {
                    availableRadii.push_back(detectorGeometryRadiusMatrix[y][x]);
                    radiiMatrixIndices.push_back(Point2D< uint16_t >(x, y));
                }
            }
        }
    }
}

static void fillBins(vector< vector< Point2D< uint16_t > > >& binsWithIndices, vector< vector< float > >& binsWithRadii,
        vector< float >& availableRadii, vector< Point2D< uint16_t > >& radiiMatrixIndices,
        const radialRankFilter_accuracyConstants_t& accuracyConstants)
{
    sortTwoVectorsByFirstVector(availableRadii, radiiMatrixIndices);

    binsWithIndices.clear();
    binsWithIndices.resize(1);
    binsWithRadii.clear();
    binsWithRadii.resize(1);

    for (uint32_t i = 0; i < availableRadii.size(); ++i) {
        if (binsWithIndices.back().size() < accuracyConstants.minValuesPerBin ||
                binsWithRadii.back().back() - binsWithRadii.back().front() < accuracyConstants.minBinWidth) {
            binsWithIndices.back().push_back(radiiMatrixIndices[i]);
            binsWithRadii.back().push_back(availableRadii[i]);
        } else {
            binsWithIndices.push_back(vector< Point2D< uint16_t > >(1, radiiMatrixIndices[i]));
            binsWithRadii.push_back(vector< float >(1, availableRadii[i]));
        }
    }
}

static void thinOutBins(vector< vector< float > >& binsWithRadii, vector< vector< Point2D< uint16_t > > >& binsWithIndices,
        const radialRankFilter_accuracyConstants_t& accuracyConstants, const Vector2f* detectorGeometryMatrix_linear,
        const detectorRawFormat_t& detectorRawFormat)
{
    if (accuracyConstants.maxConsideredValuesPerBin == 0) {
        return;
    }

    for (uint32_t i = 0; i < binsWithRadii.size(); ++i) {
        vector< float > &currentRadii = binsWithRadii[i];
        vector< Point2D< uint16_t > > &currentIndices = binsWithIndices[i];

        vector< float > angles;
        computeAngles(angles, currentIndices, detectorGeometryMatrix_linear, detectorRawFormat);
        sortThreeVectorsByFirstVector(angles, currentRadii, currentIndices);

        uint32_t N = currentRadii.size();

        if (N > accuracyConstants.maxConsideredValuesPerBin) {
            vector< float > floatLinspace;
            linspace(0, N, accuracyConstants.maxConsideredValuesPerBin + 1).swap(floatLinspace);

            vector< uint32_t > vectorIndicesToConsider(floatLinspace.begin(), floatLinspace.end() - 1);

            vector< float > tempRadii(vectorIndicesToConsider.size());
            vector< Point2D< uint16_t > > tempIndices(vectorIndicesToConsider.size());

            for (uint32_t i = 0; i < vectorIndicesToConsider.size(); ++i) {
                tempRadii[i] = currentRadii[vectorIndicesToConsider[i]];
                tempIndices[i] = currentIndices[vectorIndicesToConsider[i]];
            }
            tempRadii.swap(currentRadii);
            tempIndices.swap(currentIndices);
        }
    }
}

static void computeAngles(vector< float >& angles, const vector< Point2D< uint16_t > >& radiiMatrixIndices,
        const Vector2f* detectorGeometryMatrix_linear, const detectorRawFormat_t& detectorRawFormat)
{
    const Vector2f (*detectorGeometryMatrix)[detectorRawFormat.pix_nx] =
            (const Eigen::Vector2f (*)[detectorRawFormat.pix_nx]) detectorGeometryMatrix_linear;

    angles.resize(radiiMatrixIndices.size());

    for (uint32_t i = 0; i < radiiMatrixIndices.size(); ++i) {
        Point2D< uint16_t > matrixIndex = radiiMatrixIndices[i];
        const Vector2f position = detectorGeometryMatrix[matrixIndex.getY()][matrixIndex.getX()];
        float angle = atan2(position.y(), position.x());
        angles[i] = angle;
    }
}

static void computeBinsWithLinearindicesFromBinsWithMatrixIndices(vector< vector< uint32_t > >& binsWithLinearIndices,
        const vector< vector< Point2D< uint16_t > > >& binsWithIndices, const detectorRawFormat_t& detectorRawFormat)
{
    binsWithLinearIndices.resize(binsWithIndices.size());
    for (uint32_t i = 0; i < binsWithIndices.size(); ++i) {
        binsWithLinearIndices[i].resize(binsWithIndices[i].size());
        for (uint32_t j = 0; j < binsWithIndices[i].size(); ++j) {
            const Point2D< uint16_t > matrixIndex = binsWithIndices[i][j];
            binsWithLinearIndices[i][j] = getLinearIndexFromMatrixIndex(matrixIndex, detectorRawFormat);
        }
    }
}

static void computeSparsePrecomputedConstants(radialRankFilter_precomputedConstants_t& precomputedConstants,
        const vector< vector< uint32_t > >& binsWithLinearIndices)
{
    precomputedConstants.sparseBinIndices.clear();
    precomputedConstants.sparseLinearDataToConsiderIndices.clear();

    for (uint16_t i = 0; i < binsWithLinearIndices.size(); ++i) {
        for (uint32_t j = 0; j < binsWithLinearIndices[i].size(); ++j) {
            precomputedConstants.sparseLinearDataToConsiderIndices.push_back(binsWithLinearIndices[i][j]);
            precomputedConstants.sparseBinIndices.push_back(i + 1);   //+1 because a first and last bin are added for interpolation
        }
    }

    sortTwoVectorsByFirstVector(precomputedConstants.sparseLinearDataToConsiderIndices, precomputedConstants.sparseBinIndices);
}

static void computeBinRadii(radialRankFilter_precomputedConstants_t& precomputedConstants, const vector< vector< float > >& binsWithRadii)
{
    precomputedConstants.binRadii.resize(binsWithRadii.size() + 2); //+2 because a first and last bin are added for interpolation
    float minRadius = numeric_limits< float >::max();
    float maxRadius = 0;
    for (uint32_t i = 0; i < binsWithRadii.size(); ++i) {
        double sum = 0;
        for (uint32_t j = 0; j < binsWithRadii[i].size(); ++j) {
            sum += binsWithRadii[i][j];

            if (binsWithRadii[i][j] < minRadius) {
                minRadius = binsWithRadii[i][j];
            }
            if (binsWithRadii[i][j] > maxRadius) {
                maxRadius = binsWithRadii[i][j];
            }
        }
        precomputedConstants.binRadii[i + 1] = (float) (sum / binsWithRadii[i].size());
    }
    precomputedConstants.binRadii[0] = minRadius;
    precomputedConstants.binRadii.back() = maxRadius;
}

static void computeDataCountPerBin(radialRankFilter_precomputedConstants_t& precomputedConstants, const vector< vector< float > >& binsWithRadii)
{
    precomputedConstants.dataCountPerBin.resize(precomputedConstants.binCount);
    for (uint32_t i = 0; i < binsWithRadii.size(); ++i) {
        precomputedConstants.dataCountPerBin[i + 1] = binsWithRadii[i].size();
    }
    precomputedConstants.dataCountPerBin[0] = 0;
    precomputedConstants.dataCountPerBin.back() = 0;
}

static void computeIntraBinIndices(radialRankFilter_precomputedConstants_t& precomputedConstants, const uint8_t* mask_linear,
        const vector< vector< uint32_t > >& binsWithLinearIndices, const float* detectorGeometryRadiusMatrix_linear,
        const radialRankFilter_accuracyConstants_t& accuracyConstants, const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions)
{
    vector< uint16_t > binIndices(detectorRawFormat.pix_nn);
    for (uint16_t i = 0; i < binsWithLinearIndices.size(); ++i) {
        for (uint32_t j = 0; j < binsWithLinearIndices[i].size(); ++j) {
            binIndices[binsWithLinearIndices[i][j]] = i + 1; //+1 because a first and last bin are added for interpolation
        }
    }

    sortTwoVectorsByFirstVector(precomputedConstants.sparseLinearDataToConsiderIndices, precomputedConstants.sparseBinIndices);

    precomputedConstants.intraBinIndices.resize(detectorRawFormat.pix_nn);

    for (uint8_t detektorToCrrectNumber = 0; detektorToCrrectNumber < accuracyConstants.detektorsToCorrectSubscripts.size(); ++detektorToCrrectNumber) {
        const Point2D< uint8_t >& detektorToCrrectIndex = accuracyConstants.detektorsToCorrectSubscripts[detektorToCrrectNumber];

        const detectorPosition_t detectorPosition = detectorPositions[detektorToCrrectIndex.getY()][detektorToCrrectIndex.getX()];

        for (uint16_t y = detectorPosition.rawCoordinates_uint16.getUpperLeftCorner().getY() + 1;
                y <= detectorPosition.rawCoordinates_uint16.getLowerRightCorner().getY() - 1; ++y) {
            for (uint16_t x = detectorPosition.rawCoordinates_uint16.getUpperLeftCorner().getX() + 1;
                    x <= detectorPosition.rawCoordinates_uint16.getLowerRightCorner().getX() - 1; ++x) {
                uint32_t linearIndex = getLinearIndexFromMatrixIndex(x, y, detectorRawFormat);
                if (mask_linear[linearIndex] == 0) {
                    if (detectorGeometryRadiusMatrix_linear[linearIndex] < precomputedConstants.binRadii[binIndices[linearIndex]]) {
                        precomputedConstants.intraBinIndices[linearIndex] = binIndices[linearIndex] - 1;
                    } else {
                        precomputedConstants.intraBinIndices[linearIndex] = binIndices[linearIndex];
                    }
                }
            }
        }
    }
}

static void computeIntraBinInterpolationConstant(radialRankFilter_precomputedConstants_t& precomputedConstants, const uint8_t* mask_linear,
        const float* detectorGeometryRadiusMatrix_linear, const radialRankFilter_accuracyConstants_t& accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat,
        const detectorPositions_t& detectorPositions)
{
    precomputedConstants.intraBinInterpolationConstant.resize(detectorRawFormat.pix_nn);

    for (uint8_t detektorToCrrectNumber = 0; detektorToCrrectNumber < accuracyConstants.detektorsToCorrectSubscripts.size(); ++detektorToCrrectNumber) {
        const Point2D< uint8_t >& detektorToCrrectIndex = accuracyConstants.detektorsToCorrectSubscripts[detektorToCrrectNumber];

        const detectorPosition_t detectorPosition = detectorPositions[detektorToCrrectIndex.getY()][detektorToCrrectIndex.getX()];

        for (uint16_t y = detectorPosition.rawCoordinates_uint16.getUpperLeftCorner().getY() + 1;
                y <= detectorPosition.rawCoordinates_uint16.getLowerRightCorner().getY() - 1; ++y) {
            for (uint16_t x = detectorPosition.rawCoordinates_uint16.getUpperLeftCorner().getX() + 1;
                    x <= detectorPosition.rawCoordinates_uint16.getLowerRightCorner().getX() - 1; ++x) {
                uint32_t linearIndex = getLinearIndexFromMatrixIndex(x, y, detectorRawFormat);
                if (mask_linear[linearIndex] == 0) {
                    precomputedConstants.intraBinInterpolationConstant[linearIndex] = (detectorGeometryRadiusMatrix_linear[linearIndex]
                            - precomputedConstants.binRadii[precomputedConstants.intraBinIndices[linearIndex]])
                            / (precomputedConstants.binRadii[precomputedConstants.intraBinIndices[linearIndex] + 1]
                                    - precomputedConstants.binRadii[precomputedConstants.intraBinIndices[linearIndex]]);
                }
            }
        }
    }
}
