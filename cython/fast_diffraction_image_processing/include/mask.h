/*
 * mask.h
 *
 *  Created on: 12.12.2015
 *      Author: Yaro
 */

#ifndef INCLUDE_MASK_H_
#define INCLUDE_MASK_H_

#include <detectorRawFormat.h>
#include <stdint.h>
#include <vector>

void mergeMaskIntoData(float * data, const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat);
void mergeMaskIntoData(float * data, const std::vector< uint32_t >& sparseMask);

void mergeMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat);
void mergeMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const std::vector< uint32_t >& sparseMask,
        const detectorRawFormat_t& detectorRawFormat);

void mergeInvertedMaskIntoData(float * data, const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat);
void mergeInvertedMaskAndDataIntoDataCopy(const float * data, float * dataCopy, const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat);

void getMaskFromMergedMaskInData(const float * data, uint8_t * mask, const detectorRawFormat_t& detectorRawFormat);

void createSparseMask(const uint8_t * mask, const detectorRawFormat_t& detectorRawFormat, std::vector< uint32_t >& sparseMask);

#endif /* INCLUDE_MASK_H_ */
