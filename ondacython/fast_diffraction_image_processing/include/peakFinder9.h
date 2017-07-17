/*
 * peakFinder.h
 *
 *  Created on: 12.12.2015
 *      Author: Yaro
 */

#ifndef INCLUDE_PEAKFINDER_H_
#define INCLUDE_PEAKFINDER_H_

#include <detectorRawFormat.h>
#include <peakList.h>
#include <stdint.h>

typedef struct {
    float sigmaFactorBiggestPixel;               // small factor leads to a slow algorithm
    float sigmaFactorPeakPixel;                 // should be smaller or equal to sigmaFactorBiggestPixel
    float sigmaFactorWholePeak;                 // should be bigger or equal to sigmaFactorBiggestPixel
    float minimumSigma;                         // to not find false peaks in very dark noise free regions
    float minimumPeakOversizeOverNeighbours;    //for faster processing
    uint8_t windowRadius;    //radius of the peak search window (incl. border). Must be >= 2
} peakFinder9_accuracyConstants_t;

#ifdef __cplusplus

#define PEAK_FINDER_9__DOUBLE_BACKGROUND_ESTIMATION_WINDOW false

uint32_t peakFinder9(const float* data_linear, const peakFinder9_accuracyConstants_t& accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat, peakList_t& peakList);

uint32_t peakFinder9_onePanel(const float* data_linear, uint32_t asic_x, uint32_t asic_y, const peakFinder9_accuracyConstants_t& accuracyConstants,
        const detectorRawFormat_t& detectorRawFormat, peakList_t& peakList);

#endif

#endif /* INCLUDE_PEAKFINDER_H_ */
