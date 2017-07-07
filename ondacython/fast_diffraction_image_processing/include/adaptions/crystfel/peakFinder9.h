/*
 * peakFinder9_crystfelAdapted.h
 *
 *  Created on: 10.03.2017
 *      Author: Yaro
 */

#ifndef PEAKFINDER9_H_
#define PEAKFINDER9_H_

#include <stdint.h>
#include <peakFinder9.h>

#ifdef __cplusplus
extern "C" {
#endif

uint32_t peakFinder9_onePanel_noSlab(const float* data_linear, const peakFinder9_accuracyConstants_t* accuracyConstants,
        const detectorRawFormat_t* detectorRawFormat, peakList_t* peakList);

#ifdef __cplusplus
}
#endif

#endif /* PEAKFINDER9_H_ */
