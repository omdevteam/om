/*
 * peakFinder9_Adapted.c
 *
 *  Created on: 10.03.2017
 *      Author: Yaro
 */


#include <adaptions/crystfel/peakFinder9.h>

uint32_t peakFinder9_onePanel_noSlab(const float* data_linear, const peakFinder9_accuracyConstants_t* accuracyConstants,
        const detectorRawFormat_t* detectorRawFormat, peakList_t* peakList)
{
    return peakFinder9_onePanel(data_linear, 0, 0, *accuracyConstants,
            *detectorRawFormat, *peakList);
}
