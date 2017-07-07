/*
 * detectorGeometry.h
 *
 *  Created on: 12.12.2015
 *      Author: Yaro
 */

#ifndef INCLUDE_DETECTORGEOMETRY_H_
#define INCLUDE_DETECTORGEOMETRY_H_

#include <detectorRawFormat.h>
#include <Point2D.h>
#include <stdint.h>
#include <vector>
#include "ImageRectangle.h"
#include <Eigen/Dense>
#include <Eigen/StdVector>

typedef struct {
    // entries from geometry file
    uint16_t min_fs;
    uint16_t min_ss;
    uint16_t max_fs;
    uint16_t max_ss;

    Eigen::Vector2f fs;  //fast scan vector (normalized)
    Eigen::Vector2f ss;  //slow scan vector (normalized)
    Eigen::Vector2f corner;

    //not in the geometry file, has to be computed (or set) explicitly.
    ImageRectangle< uint16_t > rawCoordinates_uint16;
    ImageRectangle< float > rawCoordinates_float;

    Eigen::Vector2f virtualZeroPositionRaw;   //Position of the beam center in the raw image (only valid for one detector)

public:
    EIGEN_MAKE_ALIGNED_OPERATOR_NEW
        ;
} detectorPosition_t;

typedef std::vector< std::vector< detectorPosition_t, Eigen::aligned_allocator< detectorPosition_t > > > detectorPositions_t;   //[x][y]

void computeDetectorPositionsFromDetectorGeometryMatrix(
        detectorPositions_t& detectorPositions, const detectorRawFormat_t detectorRawFormat, const Eigen::Vector2f* detectorGeometryMatrix_linear);

void updateVirtualZeroPosition(detectorPosition_t& detectorPositions);

inline uint32_t getLinearIndexFromMatrixIndex(const Point2D< uint16_t >& matrixIndex, const detectorRawFormat_t& detectorRawFormat)
{
    return matrixIndex.getY() * detectorRawFormat.pix_nx + matrixIndex.getX();
}

inline uint32_t getLinearIndexFromMatrixIndex(uint16_t x, uint16_t y, const detectorRawFormat_t& detectorRawFormat)
{
    return y * detectorRawFormat.pix_nx + x;
}

#endif /* INCLUDE_DETECTORGEOMETRY_H_ */
