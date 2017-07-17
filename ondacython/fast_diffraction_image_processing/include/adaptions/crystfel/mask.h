/*
 * mask.h
 *
 *  Created on: 12.12.2015
 *      Author: Yaro
 */

// Tthis version does not exploit the fast sparse mask capabilities of the original version.
// This version uses int mask instead of uint8_t
#ifndef INCLUDE_MASK_H_
#define INCLUDE_MASK_H_

#include <detectorRawFormat.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void mergeMaskIntoData(float * data, const int * mask, const detectorRawFormat_t* detectorRawFormat);

void mergeMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const int * mask, const detectorRawFormat_t* detectorRawFormat);

void mergeInvertedMaskIntoData(float * data, const int * mask, const detectorRawFormat_t* detectorRawFormat);
void mergeInvertedMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const int * mask, const detectorRawFormat_t* detectorRawFormat);

void getMaskFromMergedMaskInData(const float * data, int * mask, const detectorRawFormat_t* detectorRawFormat);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDE_MASK_H_ */
