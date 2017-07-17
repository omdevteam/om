/*
 * detectorGeometry.cpp
 *
 *  Created on: 12.12.2015
 *      Author: Yaro
 */

#include "detectorGeometry.h"
//#include <math.h>
#include <cmath>

using namespace std;
using namespace Eigen;

void updateVirtualZeroPosition(detectorPosition_t& detectorPosition);

void computeDetectorPositionsFromDetectorGeometryMatrix(detectorPositions_t& detectorPositions, const detectorRawFormat_t detectorRawFormat,
        const Vector2f* detectorGeometryMatrix_linear)
{
    detectorPositions.resize(detectorRawFormat.nasics_x);
    for (auto& element : detectorPositions)
    {
        element.resize(detectorRawFormat.nasics_y);
    }

    const Vector2f (*detectorGeometryMatrix)[detectorRawFormat.pix_nx] =
            (const Vector2f (*)[detectorRawFormat.pix_nx]) detectorGeometryMatrix_linear;

    for (uint16_t asic_y = 0; asic_y < detectorRawFormat.nasics_y; ++asic_y) {
        for (uint16_t asic_x = 0; asic_x < detectorRawFormat.nasics_x; ++asic_x) {
            uint16_t min_fs = asic_x * detectorRawFormat.asic_nx;
            uint16_t min_ss = asic_y * detectorRawFormat.asic_ny;
            uint16_t max_fs = (asic_x + 1) * detectorRawFormat.asic_nx - 1;
            uint16_t max_ss = (asic_y + 1) * detectorRawFormat.asic_ny - 1;

            Vector2f fs = detectorGeometryMatrix[min_ss][min_fs + 1] - detectorGeometryMatrix[min_ss][min_fs];
            Vector2f ss = detectorGeometryMatrix[min_ss + 1][min_fs] - detectorGeometryMatrix[min_ss][min_fs];
            Vector2f corner = detectorGeometryMatrix[min_ss][min_fs] - 0.5 * fs - 0.5 * ss;

            detectorPositions[asic_y][asic_x].min_fs = min_fs;
            detectorPositions[asic_y][asic_x].min_ss = min_ss;
            detectorPositions[asic_y][asic_x].max_fs = max_fs;
            detectorPositions[asic_y][asic_x].max_ss = max_ss;
            detectorPositions[asic_y][asic_x].fs = fs;
            detectorPositions[asic_y][asic_x].ss = ss;
            detectorPositions[asic_y][asic_x].corner = corner;

            detectorPositions[asic_y][asic_x].rawCoordinates_uint16 = ImageRectangle< uint16_t >(Point2D< uint16_t >(min_fs, min_ss),
                    Point2D< uint16_t >(max_fs, max_ss));
            detectorPositions[asic_y][asic_x].rawCoordinates_float = ImageRectangle< float >(Point2D< float >(min_fs, min_ss),
                    Point2D< float >(max_fs, max_ss));

            updateVirtualZeroPosition(detectorPositions[asic_y][asic_x]);
        }
    }
}

void updateVirtualZeroPosition(detectorPosition_t& detectorPosition)
{
    float numerator = detectorPosition.fs.dot(detectorPosition.corner * (-1));
    float denominator = detectorPosition.fs.norm() * detectorPosition.corner.norm();
    float angleSsVectorToZero = acosf(numerator / denominator);

//    rotationMatrix = [ cos(angleSsVectorToZero) -sin(angleSsVectorToZero); sin(angleSsVectorToZero) cos(angleSsVectorToZero) ];
//    virtualZeroPosition = upperLeftCornerRaw + rotationMatrix*[distanceUpperLeftCornerAlignedToZero ; 0];

    detectorPosition.virtualZeroPositionRaw = Map< const Vector2f >(detectorPosition.rawCoordinates_float.getUpperLeftCorner().getData())
            + Vector2f(cos(angleSsVectorToZero), sin(angleSsVectorToZero)) * detectorPosition.corner.norm();
}

