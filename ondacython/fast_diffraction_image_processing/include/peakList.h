/*
 * peakList.h
 *
 *  Created on: 13.12.2015
 *      Author: Yaro
 */

#ifndef INCLUDE_PEAK_LIST_H_
#define INCLUDE_PEAK_LIST_H_

typedef struct {
    int memoryAllocated;
    long peakCount;
    long maxPeakCount;

    float *maxIntensity;        // Maximum intensity in peak
    float *totalIntensity;      // Integrated intensity in peak
    float *sigmaBackground;     // Standard deviation of the background
    float *snr;                 // Signal-to-noise ratio of peak
    float *pixelCount;          // Number of pixels in peak
    float *centerOfMass_rawX;   // peak center of mass x (in raw layout)
    float *centerOfMass_rawY;   // peak center of mass y (in raw layout)
} peakList_t;

#ifdef __cplusplus
extern "C" {
#endif

int allocatePeakList(peakList_t* peakList, int maxPeakCount);
void freePeakList(peakList_t peakList);

#ifdef __cplusplus
}
#endif

#endif /* INCLUDE_PEAK_LIST_H_ */
