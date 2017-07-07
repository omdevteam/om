/*
 * mask.cpp
 *
 *  Created on: 12.12.2015
 *      Author: Yaro
 */

#include "mask.h"
#include <cmath>
#include <cfloat>


using namespace std;

void mergeMaskIntoData(float * data, const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat)
{
    float* currentDataPixel;
    const uint8_t* currentMaskPixel;

    for (currentDataPixel = data, currentMaskPixel = mask; currentDataPixel < data + detectorRawFormat.pix_nn;
            ++currentDataPixel, ++currentMaskPixel) {
        if (*currentMaskPixel != 0) {
            *currentDataPixel = -FLT_MAX;
        }
    }
}

void mergeInvertedMaskIntoData(float * data, const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat)
{
    float* currentDataPixel;
    const uint8_t* currentMaskPixel;

    for (currentDataPixel = data, currentMaskPixel = mask; currentDataPixel < data + detectorRawFormat.pix_nn;
            ++currentDataPixel, ++currentMaskPixel) {
        if (*currentMaskPixel == 0) {
            *currentDataPixel = -FLT_MAX;
        }
    }
}

void mergeMaskIntoData(float * data, const std::vector< uint32_t >& sparseMask)
{
    for (const uint32_t & it : sparseMask)
    {
        data[it] = -FLT_MAX;
    }
}

void mergeMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat)
{
    const float *currentDataPixel;
    float *currentDataCopyPixel;
    const uint8_t* currentMaskPixel;

    for (currentDataPixel = data, currentMaskPixel = mask, currentDataCopyPixel = dataCopy;
            currentDataPixel < data + detectorRawFormat.pix_nn;
            ++currentDataPixel, ++currentMaskPixel, ++currentDataCopyPixel) {
        if (*currentMaskPixel == 0) {
            *currentDataCopyPixel = *currentDataPixel;
        } else {
            *currentDataCopyPixel = -FLT_MAX;
        }
    }
}

void mergeMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const std::vector< uint32_t >& sparseMask,
        const detectorRawFormat_t& detectorRawFormat)
{
    copy(data, data + detectorRawFormat.pix_nn, dataCopy);
    mergeMaskIntoData(dataCopy, sparseMask);
}

void mergeInvertedMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat)
{
    const float *currentDataPixel;
    float *currentDataCopyPixel;
    const uint8_t* currentMaskPixel;

    for (currentDataPixel = data, currentMaskPixel = mask, currentDataCopyPixel = dataCopy;
            currentDataPixel < data + detectorRawFormat.pix_nn;
            ++currentDataPixel, ++currentMaskPixel, ++currentDataCopyPixel) {
        if (*currentMaskPixel == 0) {
            *currentDataCopyPixel = -FLT_MAX;
        } else {
            *currentDataCopyPixel = *currentDataPixel;
        }
    }
}

void getMaskFromMergedMaskInData(const float * data, uint8_t * mask, const detectorRawFormat_t& detectorRawFormat)
{
    uint32_t pixelCount = detectorRawFormat.pix_nn;

    for (uint32_t i = 0; i < pixelCount; ++i) {
        if (isfinite(data[i])) {
            mask[i] = 0;
        } else {
            mask[i] = 1;
        }
    }
}

void createSparseMask(const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat, std::vector< uint32_t >& sparseMask)
{
    sparseMask.clear();

    for (uint32_t i = 0; i < detectorRawFormat.pix_nn; ++i) {
        if (mask[i] != 0) {
            sparseMask.push_back(i);
        }
    }
}
