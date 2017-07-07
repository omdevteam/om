/*
 * peakList.cpp
 *
 *  Created on: 13.12.2015
 *      Author: Yaro
 */

#include <peakList.h>
#include <stdlib.h>
#include <cstddef>

/*
 *  Create arrays for remembering Bragg peak data
 */
int allocatePeakList(peakList_t *peakList, int maxPeakCount)
{
    peakList->peakCount = 0;
    peakList->maxPeakCount = maxPeakCount;

    peakList->maxIntensity = (float *) calloc(maxPeakCount, sizeof(float));
    peakList->totalIntensity = (float *) calloc(maxPeakCount, sizeof(float));
    peakList->sigmaBackground = (float *) calloc(maxPeakCount, sizeof(float));
    peakList->snr = (float *) calloc(maxPeakCount, sizeof(float));
    peakList->pixelCount = (float *) calloc(maxPeakCount, sizeof(float));
    peakList->centerOfMass_rawX = (float *) calloc(maxPeakCount, sizeof(float));
    peakList->centerOfMass_rawY = (float *) calloc(maxPeakCount, sizeof(float));

    if (peakList->maxIntensity == NULL ||
            peakList->totalIntensity == NULL ||
            peakList->sigmaBackground == NULL ||
            peakList->snr == NULL ||
            peakList->pixelCount == NULL ||
            peakList->centerOfMass_rawX == NULL ||
            peakList->centerOfMass_rawY == NULL
    ) {
        if (peakList->maxIntensity != NULL) {
            free(peakList->maxIntensity);
        }
        if (peakList->totalIntensity != NULL) {
            free(peakList->totalIntensity);
        }
        if (peakList->sigmaBackground != NULL) {
            free(peakList->sigmaBackground);
        }
        if (peakList->snr != NULL) {
            free(peakList->snr);
        }
        if (peakList->pixelCount != NULL) {
            free(peakList->pixelCount);
        }
        if (peakList->centerOfMass_rawX != NULL) {
            free(peakList->centerOfMass_rawX);
        }
        if (peakList->centerOfMass_rawY != NULL) {
            free(peakList->centerOfMass_rawY);
        }
        return 1;
    } else {
        peakList->memoryAllocated = 1;
        return 0;
    }
}

/*
 *  Clean up Bragg peak arrays
 */
void freePeakList(peakList_t peakList)
{
    if (peakList.memoryAllocated == 1) {
        free(peakList.maxIntensity);
        free(peakList.totalIntensity);
        free(peakList.sigmaBackground);
        free(peakList.snr);
        free(peakList.pixelCount);
        free(peakList.centerOfMass_rawX);
        free(peakList.centerOfMass_rawY);
        peakList.memoryAllocated = 0;
    }
}

