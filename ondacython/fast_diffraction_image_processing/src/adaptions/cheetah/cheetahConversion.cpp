/*
 * cheetahConversion.cpp
 *
 *  Created on: 22.12.2015
 *      Author: Yaro
 */

#include "adaptions/cheetah/cheetahConversion.h"

using namespace Eigen;

void cheetahGetDetectorGeometryMatrix(const float* pix_x, const float* pix_y, const detectorRawFormat_t detectorRawFormat,
        Vector2f** detectorGeometryMatrix)
{
    uint32_t imageSize_x = detectorRawFormat.asic_nx * detectorRawFormat.nasics_x;
    uint32_t imageSize_y = detectorRawFormat.asic_ny * detectorRawFormat.nasics_y;

    *detectorGeometryMatrix = new Vector2f[imageSize_x * imageSize_y];
    for (uint32_t i = 0; i < imageSize_x * imageSize_y; ++i) {
        float x = pix_x[i];
        float y = pix_y[i];

        (*detectorGeometryMatrix)[i] = Vector2f(x, y);
    }
}

void cheetahDeleteDetectorGeometryMatrix(Vector2f* detectorGeometryMatrix)
{
    delete[] detectorGeometryMatrix;
}
