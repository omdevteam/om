/*
 * mask.cpp
 *
 *  Created on: 12.12.2015
 *      Author: Yaro
 */

#include <adaptions/crystfel/mask.h>
#include <cmath>
#include <cfloat>


using namespace std;

void mergeMaskIntoData(float * data, const int * mask, const detectorRawFormat_t* detectorRawFormat)
{
    float* currentDataPixel;
    const int* currentMaskPixel;

    for (currentDataPixel = data, currentMaskPixel = mask; currentDataPixel < data + detectorRawFormat->pix_nn;
            ++currentDataPixel, ++currentMaskPixel) {
        if (*currentMaskPixel != 0) {
            *currentDataPixel = -FLT_MAX;
        }
    }
}

void mergeInvertedMaskIntoData(float * data, const int * mask, const detectorRawFormat_t* detectorRawFormat)
{
    float* currentDataPixel;
    const int* currentMaskPixel;

    for (currentDataPixel = data, currentMaskPixel = mask; currentDataPixel < data + detectorRawFormat->pix_nn;
            ++currentDataPixel, ++currentMaskPixel) {
        if (*currentMaskPixel == 0) {
            *currentDataPixel = -FLT_MAX;
        }
    }
}

void mergeMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const int * mask, const detectorRawFormat_t* detectorRawFormat)
{
    const float *currentDataPixel;
    float *currentDataCopyPixel;
    const int* currentMaskPixel;

    for (currentDataPixel = data, currentMaskPixel = mask, currentDataCopyPixel = dataCopy;
            currentDataPixel < data + detectorRawFormat->pix_nn;
            ++currentDataPixel, ++currentMaskPixel, ++currentDataCopyPixel) {
        if (*currentMaskPixel == 0) {
            *currentDataCopyPixel = *currentDataPixel;
        } else {
            *currentDataCopyPixel = -FLT_MAX;
        }
    }
}

void mergeInvertedMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const int * mask, const detectorRawFormat_t* detectorRawFormat)
{
    const float *currentDataPixel;
    float *currentDataCopyPixel;
    const int* currentMaskPixel;

    for (currentDataPixel = data, currentMaskPixel = mask, currentDataCopyPixel = dataCopy;
            currentDataPixel < data + detectorRawFormat->pix_nn;
            ++currentDataPixel, ++currentMaskPixel, ++currentDataCopyPixel) {
        if (*currentMaskPixel == 0) {
            *currentDataCopyPixel = -FLT_MAX;
        } else {
            *currentDataCopyPixel = *currentDataPixel;
        }
    }
}

void getMaskFromMergedMaskInData(const float * data, int * mask, const detectorRawFormat_t* detectorRawFormat)
{
    uint32_t pixelCount = detectorRawFormat->pix_nn;

    for (uint32_t i = 0; i < pixelCount; ++i) {
        if (isfinite(data[i])) {
            mask[i] = 0;
        } else {
            mask[i] = 1;
        }
    }
}
